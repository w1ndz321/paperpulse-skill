#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

fitz = None
pymupdf4llm = None

try:  # Keep --help and pure helpers usable before optional dependencies are installed.
    try:
        import fitz as _fitz  # type: ignore
    except ImportError:  # pragma: no cover
        import pymupdf as _fitz  # type: ignore
    fitz = _fitz
except ImportError:  # pragma: no cover
    pass

try:
    import pymupdf4llm as _pymupdf4llm  # type: ignore
    pymupdf4llm = _pymupdf4llm
except ImportError:  # pragma: no cover
    pass


CAPTION_RE = re.compile(
    r"^(Figure|Fig\.?|Table|Tab\.?)\s+"
    r"([A-Za-z]?\d+(?:\.\d+)?|[IVXLCDM]+)(?:\s*[:.\-\u2013\u2014|])?\s+",
    re.I,
)
REFERENCE_RE = re.compile(
    r"(?im)^\s{0,3}(?:#{1,6}\s*)?(?:\*\*)?(?:\d+(?:\.\d+)*\.?\s*)?"
    r"(?:references|bibliography|\u53c2\u8003\u6587\u732e)(?:\*\*)?\s*$"
)
REFERENCE_PAGE_RE = re.compile(r"^(references|bibliography|\u53c2\u8003\u6587\u732e)$", re.I)
ARXIV_ID_RE = re.compile(r"(?:arXiv:\s*)?(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)
TITLE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "via",
    "with",
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "paper-report"


def require_pdf_dependencies() -> None:
    missing = []
    if fitz is None:
        missing.append("pymupdf")
    if pymupdf4llm is None:
        missing.append("pymupdf4llm")
    if missing:
        packages = " ".join(missing)
        raise RuntimeError(
            f"Missing PDF dependencies: {', '.join(missing)}. "
            f"Install them with: python -m pip install {packages}"
        )


def clean_markdown_line(line: str) -> str:
    line = re.sub(r"^#{1,6}\s*", "", line).strip()
    line = re.sub(r"^\s*[-–—]\s*", "", line)
    line = re.sub(r"[*_`]", "", line)
    return compact(line)


def paper_title_from_markdown(text: str) -> str:
    for raw in text.splitlines()[:80]:
        line = clean_markdown_line(raw)
        lowered = line.lower()
        if not line or len(line) < 8:
            continue
        if "intentionally omitted" in lowered or "start of picture text" in lowered:
            continue
        if lowered.startswith(("published as", "preprint", "abstract", "arxiv:")):
            continue
        if re.fullmatch(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", line):
            continue
        if "@" in line or "github.com" in lowered or "ace-agent.github.io" in lowered:
            continue
        if re.fullmatch(r"\d+", line) or re.match(r"^\d+\s+[A-Z]", line):
            continue
        if line.count(",") >= 4:
            continue
        return line
    return ""


def title_keyword_slug(title: str) -> str:
    title = re.sub(r"\s+", " ", title.replace("CON TEXTS", "CONTEXTS")).strip()
    if not title:
        return ""
    parts = re.split(r"\s*[:：]\s*", title, maxsplit=1)

    def keywords(value: str) -> list[str]:
        words = re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?", value)
        return [word.lower() for word in words if word.lower() not in TITLE_STOPWORDS]

    selected = keywords(parts[0])
    if len(selected) < 3 and len(parts) > 1:
        selected.extend(keywords(parts[1]))
    if not selected and len(parts) > 1:
        selected = keywords(parts[1])
    return slugify("-".join(selected[:5]) or title)


def choose_output_slug(override: str | None, paper_title: str, pdf_stem: str) -> str:
    if override:
        return slugify(override)
    return title_keyword_slug(paper_title) or slugify(pdf_stem)


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def rect_area(rect: fitz.Rect) -> float:
    return max(rect.width, 0.0) * max(rect.height, 0.0)


def intersect(a: fitz.Rect, b: fitz.Rect) -> fitz.Rect:
    x0, y0 = max(a.x0, b.x0), max(a.y0, b.y0)
    x1, y1 = min(a.x1, b.x1), min(a.y1, b.y1)
    return fitz.Rect(x0, y0, x1, y1) if x1 >= x0 and y1 >= y0 else fitz.Rect(0, 0, 0, 0)


def expand(rect: fitz.Rect, dx: float, dy: float) -> fitz.Rect:
    return fitz.Rect(rect.x0 - dx, rect.y0 - dy, rect.x1 + dx, rect.y1 + dy)


def union(rects: list[fitz.Rect]) -> fitz.Rect:
    return fitz.Rect(
        min(rect.x0 for rect in rects),
        min(rect.y0 for rect in rects),
        max(rect.x1 for rect in rects),
        max(rect.y1 for rect in rects),
    )


def page_blocks(page: fitz.Page) -> list[tuple[fitz.Rect, str]]:
    blocks: list[tuple[fitz.Rect, str]] = []
    for block in page.get_text("blocks"):
        x0, y0, x1, y1, text, *_ = block
        text = text.strip()
        if text:
            blocks.append((fitz.Rect(x0, y0, x1, y1), text))
    return sorted(blocks, key=lambda item: (item[0].y0, item[0].x0))


def is_wide(page: fitz.Page, rect: fitz.Rect) -> bool:
    midpoint = page.rect.width / 2
    return rect.width > page.rect.width * 0.55 or (rect.x0 < midpoint - 12 and rect.x1 > midpoint + 12)


def same_column(page: fitz.Page, anchor: fitz.Rect, rect: fitz.Rect) -> bool:
    if page.rect.width < 500 or is_wide(page, anchor):
        return True
    midpoint = page.rect.width / 2
    return ((anchor.x0 + anchor.x1) / 2 < midpoint) == ((rect.x0 + rect.x1) / 2 < midpoint)


def column_bounds(page: fitz.Page, anchor: fitz.Rect) -> tuple[float, float]:
    if page.rect.width < 500 or is_wide(page, anchor):
        return page.rect.x0 + 18, page.rect.x1 - 18
    midpoint = page.rect.width / 2
    if (anchor.x0 + anchor.x1) / 2 < midpoint:
        return page.rect.x0 + 24, midpoint - 16
    return midpoint + 16, page.rect.x1 - 24


def markdown_from_pdf(pdf_path: Path) -> str:
    result = pymupdf4llm.to_markdown(str(pdf_path))
    if isinstance(result, list):
        text = "\n\n".join(str(item).strip() for item in result if str(item).strip())
    else:
        text = str(result).strip()
    if not text:
        raise RuntimeError("pymupdf4llm returned empty Markdown")
    return text


def strip_references(text: str) -> tuple[str, bool]:
    match = REFERENCE_RE.search(text)
    if match is None:
        return text, False
    return text[: match.start()].rstrip(), True


def reference_start_page(doc: fitz.Document) -> int:
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        for _, text in page_blocks(page):
            line = compact(text).strip("#* ")
            if REFERENCE_PAGE_RE.match(line):
                return page_index
    return doc.page_count


def document_links(doc: fitz.Document, max_pages: int = 3) -> dict[str, list[str]]:
    links: dict[str, list[str]] = {"paper": [], "code": [], "other": []}

    def add(kind: str, url: str) -> None:
        url = url.strip().rstrip(".,;)")
        if url and url not in links[kind]:
            links[kind].append(url)

    for page_index in range(min(doc.page_count, max_pages)):
        page = doc.load_page(page_index)
        for link in page.get_links():
            url = (link.get("uri") or "").strip()
            lowered = url.lower()
            if not url:
                continue
            if "arxiv.org/abs/" in lowered or "arxiv.org/pdf/" in lowered or "doi.org/" in lowered:
                add("paper", url.replace("/pdf/", "/abs/").removesuffix(".pdf"))
            elif any(host in lowered for host in ("github.com", "gitlab.com", "huggingface.co", "modelscope.cn")):
                add("code", url)
            else:
                add("other", url)

    first_text = "\n".join(doc.load_page(i).get_text() for i in range(min(doc.page_count, max_pages)))
    for arxiv_id in ARXIV_ID_RE.findall(first_text):
        add("paper", f"https://arxiv.org/abs/{arxiv_id}")
    return {kind: urls for kind, urls in links.items() if urls}


def caption_records(doc: fitz.Document, max_assets: int) -> list[dict]:
    last_page = reference_start_page(doc)
    records: list[dict] = []
    counts = {"figure": 0, "table": 0}
    seen: set[tuple[int, str]] = set()

    for page_index in range(last_page):
        page = doc.load_page(page_index)
        for rect, text in page_blocks(page):
            caption = compact(text)
            match = CAPTION_RE.match(caption)
            if not match:
                continue
            kind = "table" if match.group(1).lower().startswith(("tab", "table")) else "figure"
            key = (page_index, caption[:100].lower())
            if key in seen:
                continue
            seen.add(key)
            counts[kind] += 1
            records.append(
                {
                    "id": f"{kind}_{counts[kind]:02d}_p{page_index + 1:03d}",
                    "kind": kind,
                    "page_index": page_index,
                    "page": page_index + 1,
                    "caption": caption,
                    "caption_rect": rect,
                }
            )
            if len(records) >= max_assets:
                return records
    return records


def nearby_text(page: fitz.Page, anchor: fitz.Rect, limit: int = 700) -> str:
    center_y = (anchor.y0 + anchor.y1) / 2
    snippets = []
    for rect, text in page_blocks(page):
        if same_column(page, anchor, rect) and abs(((rect.y0 + rect.y1) / 2) - center_y) <= 280:
            snippets.append(compact(text))
    return compact(" ".join(snippets))[:limit]


def visual_rects(page: fitz.Page) -> list[fitz.Rect]:
    rects: list[fitz.Rect] = []
    for info in page.get_image_info(xrefs=True):
        rect = fitz.Rect(info["bbox"])
        if rect.width >= 40 and rect.height >= 30:
            rects.append(rect)
    for drawing in page.get_drawings():
        raw = drawing.get("rect")
        if raw is None:
            continue
        rect = fitz.Rect(raw)
        if rect.width >= 35 or rect.height >= 35:
            rects.append(rect)
    return rects


def visual_crop(page: fitz.Page, caption: fitz.Rect, kind: str) -> fitz.Rect | None:
    above, below = [], []
    for rect in visual_rects(page):
        if not same_column(page, caption, rect):
            continue
        above_gap = caption.y0 - rect.y1
        below_gap = rect.y0 - caption.y1
        if -8 <= above_gap <= 260:
            above.append((abs(above_gap), rect))
        if -8 <= below_gap <= 220:
            below.append((abs(below_gap), rect))

    preferred = above if kind == "figure" else below
    pool = preferred or (below if kind == "figure" else above)
    if not pool:
        return None

    crop = sorted(pool, key=lambda item: item[0])[0][1]
    candidates = [rect for _, rect in above + below]
    changed = True
    while changed:
        changed = False
        area = expand(crop, 28, 55)
        for rect in candidates:
            if rect_area(intersect(area, rect)) > 0:
                merged = union([crop, rect])
                if merged != crop:
                    crop = merged
                    changed = True

    content = expand(crop, 4, 4)
    for rect, _ in page_blocks(page):
        if rect_area(intersect(content, rect)) / max(rect_area(rect), 1.0) >= 0.45:
            content = union([content, rect])
    return intersect(expand(union([content, caption]), 8, 8), page.rect)


def text_crop(page: fitz.Page, caption: fitz.Rect, kind: str) -> fitz.Rect | None:
    rects = []
    for rect, text in page_blocks(page):
        if rect == caption or not same_column(page, caption, rect) or CAPTION_RE.match(compact(text)):
            continue
        above_gap = caption.y0 - rect.y1
        below_gap = rect.y0 - caption.y1
        limit = 180 if kind == "figure" else 230
        if -4 <= above_gap <= limit or -4 <= below_gap <= limit:
            rects.append(rect)
    if not rects:
        return None
    return intersect(expand(union(rects + [caption]), 8, 8), page.rect)


def fallback_crop(page: fitz.Page, caption: fitz.Rect, kind: str) -> fitz.Rect:
    left, right = column_bounds(page, caption)
    if kind == "figure":
        rect = fitz.Rect(left, caption.y0 - 260, right, caption.y1 + 36)
    else:
        rect = fitz.Rect(left, caption.y0 - 90, right, caption.y1 + 230)
    return intersect(rect, page.rect)


def crop_for_caption(page: fitz.Page, caption: fitz.Rect, kind: str) -> fitz.Rect:
    for crop in (visual_crop(page, caption, kind), text_crop(page, caption, kind)):
        if crop is not None and crop.height >= caption.height + 35:
            return crop
    return fallback_crop(page, caption, kind)


def clear_images(images_dir: Path) -> None:
    images_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ("figure_*.png", "table_*.png"):
        for path in images_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def process_pdf(
    pdf_path: Path,
    report_dir: Path,
    max_assets: int,
    scale: float,
    source_text: str | None = None,
    stripped_references: bool | None = None,
    paper_title: str = "",
) -> dict:
    require_pdf_dependencies()
    report_dir.mkdir(parents=True, exist_ok=True)
    images_dir = report_dir / "images"
    clear_images(images_dir)

    if source_text is None:
        source, stripped = strip_references(markdown_from_pdf(pdf_path))
    else:
        source = source_text
        stripped = bool(stripped_references)
    (report_dir / "source_text.md").write_text(source, encoding="utf-8")

    with fitz.open(str(pdf_path)) as doc:
        assets = []
        for record in caption_records(doc, max_assets):
            page = doc.load_page(record["page_index"])
            image = f"images/{record['id']}.png"
            pix = page.get_pixmap(
                matrix=fitz.Matrix(scale, scale),
                clip=crop_for_caption(page, record["caption_rect"], record["kind"]),
                alpha=False,
                colorspace=fitz.csRGB,
            )
            pix.save(str(report_dir / image))
            assets.append(
                {
                    "id": record["id"],
                    "kind": record["kind"],
                    "page": record["page"],
                    "image": image,
                    "caption": record["caption"],
                    "nearby_text": nearby_text(page, record["caption_rect"]),
                }
            )

        metadata = {
            "pdf": str(pdf_path),
            "title": paper_title,
            "slug": report_dir.name,
            "source": "source_text.md",
            "images_dir": "images",
            "stripped_references": stripped,
            "links": document_links(doc),
            "assets": assets,
        }
    (report_dir / "captions.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    stale_captions_md = report_dir / "captions.md"
    if stale_captions_md.exists():
        stale_captions_md.unlink()
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract paper Markdown, figure/table screenshots, and captions.")
    parser.add_argument("pdf_path")
    parser.add_argument(
        "--output-root",
        help="Root directory for the paper output folder. Defaults to ./outputs in the current working directory.",
    )
    parser.add_argument("--slug")
    parser.add_argument("--max-assets", type=int, default=30)
    parser.add_argument("--scale", type=float, default=4)
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).expanduser().resolve()
    if not pdf_path.is_file():
        parser.error(f"PDF not found: {pdf_path}")
    if args.max_assets < 1:
        parser.error("--max-assets must be at least 1")
    if args.scale <= 0:
        parser.error("--scale must be greater than 0")
    try:
        require_pdf_dependencies()
    except RuntimeError as exc:
        parser.error(str(exc))

    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else Path.cwd() / "outputs"
    )
    try:
        source, stripped = strip_references(markdown_from_pdf(pdf_path))
    except Exception as exc:
        parser.error(f"Could not extract Markdown from {pdf_path.name}: {exc}")
    paper_title = paper_title_from_markdown(source)
    report_dir = output_root / choose_output_slug(args.slug, paper_title, pdf_path.stem)
    try:
        metadata = process_pdf(
            pdf_path,
            report_dir,
            args.max_assets,
            args.scale,
            source_text=source,
            stripped_references=stripped,
            paper_title=paper_title,
        )
    except Exception as exc:
        parser.error(f"Could not process {pdf_path.name}: {exc}")

    print(f"report_dir={report_dir}")
    print(f"source={report_dir / metadata['source']}")
    print(f"captions_json={report_dir / 'captions.json'}")
    print(f"images_dir={report_dir / 'images'}")
    print(f"asset_count={len(metadata['assets'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

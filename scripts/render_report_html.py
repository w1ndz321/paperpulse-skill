#!/usr/bin/env python3

from __future__ import annotations

import argparse
from datetime import datetime
import html
import re
from pathlib import Path

try:
    import markdown as markdown_lib  # type: ignore
except ImportError:  # pragma: no cover
    markdown_lib = None

try:
    from jinja2 import Environment, FileSystemLoader  # type: ignore
    from markupsafe import Markup  # type: ignore
except ImportError:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    Markup = None


SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_ROOT / "templates"
DEFAULT_TEMPLATE = "summary.html"


STYLE = """
body {
  margin: 0;
  background: #f6f2e9;
  color: #1f1f1f;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
.report-shell {
  max-width: 820px;
  margin: 0 auto;
  padding: 40px 20px 80px;
}
.report-article {
  background: #fffdf8;
  border: 1px solid #e7dcc5;
  box-shadow: 0 18px 60px rgba(84, 60, 28, 0.08);
  padding: 42px 34px 52px;
}
.article-title {
  margin: 0 0 18px;
  font-size: 34px;
  line-height: 1.28;
  letter-spacing: 0.02em;
  color: #2d2417;
}
.meta-box {
  margin: 0 0 28px;
  padding: 16px 18px;
  background: #fbf5e8;
  border-left: 4px solid #b58b45;
}
.meta-item {
  margin: 6px 0;
  font-size: 15px;
  line-height: 1.8;
}
.meta-label {
  font-weight: 700;
  color: #6d5223;
}
h2, h3, h4 {
  color: #3d2d14;
}
h2 {
  margin: 34px 0 14px;
  padding-left: 12px;
  border-left: 5px solid #b58b45;
  font-size: 28px;
  line-height: 1.35;
}
h3 {
  margin: 24px 0 10px;
  font-size: 22px;
  line-height: 1.4;
}
h4 {
  margin: 18px 0 8px;
  font-size: 18px;
}
p, li {
  font-size: 16px;
  line-height: 1.9;
}
p {
  margin: 14px 0;
}
ul, ol {
  margin: 14px 0;
  padding-left: 1.5em;
}
blockquote {
  margin: 18px 0;
  padding: 12px 16px;
  background: #f7f1e4;
  border-left: 4px solid #ccb07a;
}
code {
  padding: 0.1em 0.35em;
  background: #f1eadc;
  border-radius: 4px;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 0.92em;
}
pre {
  margin: 18px 0;
  padding: 14px 16px;
  overflow-x: auto;
  background: #f1eadc;
  border-radius: 8px;
}
pre code {
  padding: 0;
  background: transparent;
}
.image-block {
  margin: 22px 0;
  text-align: center;
}
.image-block img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid #eadfcb;
}
.image-caption {
  margin-top: 10px;
  padding: 8px 12px;
  color: #2d2417;
  background: #fbf5e8;
  border: 1px solid #eadfcb;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.65;
}
a {
  color: #1d63c4;
  text-decoration: none;
}
strong {
  color: #2e2415;
}
hr {
  margin: 28px 0;
  border: none;
  border-top: 1px solid #eadfcb;
}
"""


def inline_format(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def is_ordered_item(line: str) -> bool:
    return bool(re.match(r"^\d+\.\s+", line))


def is_unordered_item(line: str) -> bool:
    return bool(re.match(r"^[-*]\s+", line))


def render_image(line: str) -> str | None:
    match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
    if not match:
        return None
    alt, src = match.groups()
    alt = html.escape(alt)
    src = html.escape(src)
    caption = f'<figcaption>{alt}</figcaption>' if alt else ""
    return f'<figure class="image-block"><img src="{src}" alt="{alt}" />{caption}</figure>'


def extract_title_from_markdown(markdown_text: str) -> str:
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "论文解读"


def strip_top_title(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip() + "\n"


def add_image_figures(content: str) -> str:
    def repl(match: re.Match[str]) -> str:
        before_alt, alt, after_alt = match.groups()
        caption = html.escape(html.unescape(alt))
        return (
            f'<figure class="image-block"><img{before_alt} alt="{alt}"{after_alt} />'
            f'<figcaption>{caption}</figcaption></figure>'
        )

    return re.sub(r'<p><img([^>]*?) alt="([^"]*)"([^>]*?) /></p>', repl, content)


def render_markdown_content(markdown_text: str) -> str:
    body_markdown = strip_top_title(markdown_text)
    if markdown_lib is not None:
        content = markdown_lib.markdown(
            body_markdown,
            extensions=["tables", "fenced_code", "sane_lists", "toc"],
            output_format="html5",
        )
        return add_image_figures(content)
    lines = markdown_text.splitlines()
    _, _, body_start = extract_header(lines)
    return render_body(lines, body_start)


def simple_template_render(template_text: str, values: dict[str, str]) -> str:
    rendered = template_text
    content = values.get("content", "")
    rendered = rendered.replace("{{ content | safe }}", content)
    rendered = rendered.replace("{{ content|safe }}", content)
    rendered = rendered.replace("{{ content }}", content)
    rendered = rendered.replace("{{content}}", content)
    for key, value in values.items():
        if key == "content":
            continue
        rendered = rendered.replace("{{ " + key + " }}", html.escape(value))
        rendered = rendered.replace("{{" + key + "}}", html.escape(value))
    return rendered


def render_template_page(title: str, content: str, template_name: str) -> str | None:
    template_path = (TEMPLATES_DIR / template_name).resolve()
    if template_path != TEMPLATES_DIR and TEMPLATES_DIR not in template_path.parents:
        raise ValueError(f"Template must be inside {TEMPLATES_DIR}")
    if not template_path.exists():
        return None

    values = {
        "title": title,
        "content": content,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

    if Environment is not None and FileSystemLoader is not None:
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
        template = env.get_template(template_name)
        jinja_values = dict(values)
        if Markup is not None:
            jinja_values["content"] = Markup(content)
        return template.render(**jinja_values)

    return simple_template_render(template_path.read_text(encoding="utf-8"), values)


def consume_list(lines: list[str], index: int) -> tuple[str, int]:
    ordered = is_ordered_item(lines[index])
    tag = "ol" if ordered else "ul"
    items: list[str] = []
    while index < len(lines):
        line = lines[index]
        if ordered and not is_ordered_item(line):
            break
        if not ordered and not is_unordered_item(line):
            break
        content = re.sub(r"^(\d+\.\s+|[-*]\s+)", "", line)
        items.append(f"<li>{inline_format(content.strip())}</li>")
        index += 1
    return f"<{tag}>\n" + "\n".join(items) + f"\n</{tag}>", index


def render_body(lines: list[str], start_index: int) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    index = start_index
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(part.strip() for part in paragraph if part.strip())
            if text:
                blocks.append(f"<p>{inline_format(text)}</p>")
        paragraph = []

    while index < len(lines):
        raw = lines[index]
        line = raw.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            if in_code:
                code_html = html.escape("\n".join(code_lines))
                blocks.append(f"<pre><code>{code_html}</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        image_html = render_image(stripped)
        if image_html:
            flush_paragraph()
            blocks.append(image_html)
            index += 1
            continue

        if stripped == "---":
            flush_paragraph()
            blocks.append("<hr />")
            index += 1
            continue

        heading = re.match(r"^(#{2,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{inline_format(heading.group(2).strip())}</h{level}>")
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            blocks.append(f"<blockquote>{inline_format(stripped.lstrip('>').strip())}</blockquote>")
            index += 1
            continue

        if is_ordered_item(stripped) or is_unordered_item(stripped):
            flush_paragraph()
            list_html, index = consume_list([ln.strip() for ln in lines], index)
            blocks.append(list_html)
            continue

        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    return "\n".join(blocks)


def extract_header(lines: list[str]) -> tuple[str, dict[str, str], int]:
    title = "论文精读"
    metadata: dict[str, str] = {}
    index = 0

    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        index = 1

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        meta = re.match(r"^- ([^：:]+)[：:]\s*(.*)$", stripped)
        if not meta:
            break
        metadata[meta.group(1).strip()] = meta.group(2).strip()
        index += 1

    return title, metadata, index


def render_document(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    title, metadata, body_start = extract_header(lines)
    meta_html = ""
    if metadata:
        items = []
        preferred_order = ["关键词", "DOI / 论文链接"]
        seen = set()
        for key in preferred_order:
            if key in metadata:
                seen.add(key)
                items.append(
                    f'<div class="meta-item"><span class="meta-label">{html.escape(key)}：</span>{inline_format(metadata[key])}</div>'
                )
        for key, value in metadata.items():
            if key in seen:
                continue
            items.append(
                f'<div class="meta-item"><span class="meta-label">{html.escape(key)}：</span>{inline_format(value)}</div>'
            )
        meta_html = '<section class="meta-box">\n' + "\n".join(items) + "\n</section>"

    body_html = render_body(lines, body_start)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>{STYLE}</style>
</head>
<body>
  <div class="report-shell">
    <article class="report-article">
      <h1 class="article-title">{html.escape(title)}</h1>
      {meta_html}
      {body_html}
    </article>
  </div>
</body>
</html>
"""


def render_html(markdown_text: str, template_name: str, use_template: bool) -> str:
    if use_template:
        title = extract_title_from_markdown(markdown_text)
        content = render_markdown_content(markdown_text)
        html_text = render_template_page(title, content, template_name)
        if html_text is not None:
            return html_text
    return render_document(markdown_text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a paper deep-reading markdown report into a local/GitHub Pages-ready HTML article.",
    )
    parser.add_argument("report_md", help="Path to report.md")
    parser.add_argument("output_html", help="Path to output HTML")
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE,
        help=f"Template file under {TEMPLATES_DIR}. Defaults to {DEFAULT_TEMPLATE}.",
    )
    parser.add_argument(
        "--no-template",
        action="store_true",
        help="Use the built-in dependency-free renderer instead of templates.",
    )
    args = parser.parse_args()

    report_path = Path(args.report_md).expanduser().resolve()
    output_path = Path(args.output_html).expanduser().resolve()

    if not report_path.is_file():
        parser.error(f"Report not found: {report_path}")

    markdown_text = report_path.read_text(encoding="utf-8")
    try:
        html_text = render_html(markdown_text, args.template, not args.no_template)
    except ValueError as exc:
        parser.error(str(exc))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    print(f"wrote={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

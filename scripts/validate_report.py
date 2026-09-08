#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_METADATA = ("论文链接", "代码链接", "作者团队", "关键词")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
METADATA_RE = re.compile(r"^-\s*([^：:]+)[：:]\s*(.+?)\s*$")


def validate_report(report_path: Path, html_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    if not report_path.is_file():
        return [f"report.md not found: {report_path}"]

    text = report_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    first_content = next((line.strip() for line in lines if line.strip()), "")
    if not first_content.startswith("# "):
        errors.append("report.md must start with one '# ' title")

    if not re.search(r"(?im)^##\s+TL;DR\s*$", text):
        errors.append("missing '## TL;DR' section")

    metadata: dict[str, str] = {}
    for line in lines[:60]:
        match = METADATA_RE.match(line.strip())
        if match:
            metadata[match.group(1).strip()] = match.group(2).strip()
    for label in REQUIRED_METADATA:
        if not metadata.get(label):
            errors.append(f"missing metadata field: {label}")

    report_dir = report_path.parent.resolve()
    for raw_target in IMAGE_RE.findall(text):
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        if re.match(r"^[a-z]+://", target, re.I):
            errors.append(f"report images must be local relative paths: {target}")
            continue
        image_path = (report_dir / target).resolve()
        if report_dir != image_path and report_dir not in image_path.parents:
            errors.append(f"report image escapes its output folder: {target}")
        elif not image_path.is_file():
            errors.append(f"referenced image not found: {target}")

    if html_path is not None:
        if not html_path.is_file():
            errors.append(f"report.html not found: {html_path}")
        elif not html_path.read_text(encoding="utf-8").strip():
            errors.append(f"report.html is empty: {html_path}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a PaperPulse report's required structure and local image references."
    )
    parser.add_argument("report_md", help="Path to report.md")
    parser.add_argument("--html", help="Optional path to the rendered report.html")
    args = parser.parse_args()

    report_path = Path(args.report_md).expanduser().resolve()
    html_path = Path(args.html).expanduser().resolve() if args.html else None
    errors = validate_report(report_path, html_path)
    if errors:
        for error in errors:
            print(f"error: {error}")
        return 1

    print(f"validated={report_path}")
    if html_path is not None:
        print(f"html={html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

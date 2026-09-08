---
name: paperpulse-skill
description: Turn one local CS, AI, or LLM paper PDF into a Chinese, screenshot-backed research brief and a shareable HTML page. Use when readers need the paper's argument, original figures or tables, evidence, and a grounded critique—not for generic PDF extraction or literature searches.
---

# PaperPulse

Turn one local paper PDF into:

```text
outputs/<title-keyword-slug>/
├── source_text.md
├── captions.json
├── images/
├── report.md
└── report.html
```

Resolve `<skill-dir>` as the directory containing this `SKILL.md`; do not assume the current working directory is the skill directory. Generated output defaults to `./outputs` in the current working directory. Use relative report image paths such as `images/main_results.png` so the folder remains portable.

## Choose the path

- If `report.md` exists and every referenced image exists, skip PDF extraction and screenshot cropping. Render and validate only.
- Otherwise, run the complete workflow below.
- Reuse valid `source_text.md`, `captions.json`, and screenshots when only the writing needs revision.

## Complete workflow

1. Extract text, links, captions, and candidate screenshots:

```bash
python "<skill-dir>/scripts/pdf_process.py" "<pdf-path>"
```

Pass `--output-root <dir>` when the user specifies another destination. The script derives the folder slug from the paper title; use `--slug <title-keywords>` only when the derived name is unclear.

If a required PDF dependency is missing, report the provided installation command and stop before changing the environment. If extraction fails, surface the actual error; do not silently switch to OCR or another extractor.

2. Read `source_text.md` and `captions.json`. Use the paper body, captions, and nearby text to choose evidence. At this point, read [references/image-selection.md](references/image-selection.md). Visually inspect only the screenshots selected for the final report, and re-crop any incomplete figure or table before drafting.

3. Read [references/reportstyle.md](references/reportstyle.md), then write `report.md` in Chinese. Keep claims tied to the extracted paper. Do not browse for missing paper or code links unless the user asks; write `未在 PDF 中提取到` when a link is absent.

4. Render and validate:

```bash
python "<skill-dir>/scripts/render_report_html.py" "<output-dir>/report.md" "<output-dir>/report.html"
python "<skill-dir>/scripts/validate_report.py" "<output-dir>/report.md" --html "<output-dir>/report.html"
```

5. Open the rendered HTML and check the main reading flow on desktop and a narrow/mobile viewport. Confirm:

- the hero title and TL;DR are populated;
- `PAPER`, `CODE`, `AUTHORS`, and `KEYWORDS` contain only their intended data;
- every selected image loads, remains legible, and sits next to the claim it supports;
- headings, lists, links, and long metadata do not break the layout.

Fix `report.md` first and rerender. Edit the template only when the defect is genuinely presentational.

## Completion contract

Keep `source_text.md` and `captions.json` for traceability. In the final response, link `report.md` and `report.html`, state the output directory, and say whether the selected screenshots and rendered page were visually inspected. Never claim a check that was not performed.

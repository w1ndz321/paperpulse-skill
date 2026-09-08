from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


pdf_process = load_module("pdf_process", ROOT / "scripts" / "pdf_process.py")
renderer = load_module("render_report_html", ROOT / "scripts" / "render_report_html.py")
validator = load_module("validate_report", ROOT / "scripts" / "validate_report.py")


class PdfProcessTests(unittest.TestCase):
    def test_empty_title_falls_back_to_pdf_stem(self):
        self.assertEqual(
            pdf_process.choose_output_slug(None, "", "2510.04618v3"),
            "2510-04618v3",
        )

    def test_override_slug_cannot_escape_output_root(self):
        self.assertEqual(
            pdf_process.choose_output_slug("../../My Paper", "ignored", "ignored"),
            "my-paper",
        )

    def test_strip_references_keeps_body_only(self):
        body, stripped = pdf_process.strip_references("# Paper\nBody\n\n## References\n[1] Source")
        self.assertTrue(stripped)
        self.assertEqual(body, "# Paper\nBody")

    def test_rect_area_does_not_depend_on_deprecated_pymupdf_method(self):
        class Rect:
            width = 4
            height = 3

        self.assertEqual(pdf_process.rect_area(Rect()), 12)


class RenderTests(unittest.TestCase):
    def test_dependency_free_renderer_supports_python_39(self):
        markdown = "# 标题\n\n- 论文链接：未在 PDF 中提取到\n\n## TL;DR\n\n摘要"
        html = renderer.render_html(markdown, "summary.html", use_template=False)
        self.assertIn("<h1 class=\"article-title\">标题</h1>", html)
        self.assertIn("<h2>TL;DR</h2>", html)

    def test_template_path_cannot_escape_template_folder(self):
        with self.assertRaises(ValueError):
            renderer.render_template_page("title", "content", "../SKILL.md")


class ValidateTests(unittest.TestCase):
    def test_valid_report_and_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir)
            images = report_dir / "images"
            images.mkdir()
            (images / "figure.png").write_bytes(b"png")
            report = report_dir / "report.md"
            report.write_text(
                "# 标题\n\n## TL;DR\n\n摘要\n\n"
                "- 论文链接：未在 PDF 中提取到\n"
                "- 代码链接：未在 PDF 中提取到\n"
                "- 作者团队：作者\n"
                "- 关键词：关键词一、关键词二、关键词三\n\n"
                "![图](images/figure.png)\n",
                encoding="utf-8",
            )
            self.assertEqual(validator.validate_report(report), [])

    def test_missing_image_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "report.md"
            report.write_text(
                "# 标题\n\n## TL;DR\n\n摘要\n\n"
                "- 论文链接：无\n- 代码链接：无\n- 作者团队：作者\n- 关键词：词\n\n"
                "![图](images/missing.png)\n",
                encoding="utf-8",
            )
            errors = validator.validate_report(report)
            self.assertTrue(any("referenced image not found" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

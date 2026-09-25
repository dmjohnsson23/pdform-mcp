"""Tests for PyMuPDF-based text and layout extraction tools."""

import pytest
import pymupdf
from xml.etree.ElementTree import fromstring

from mcp.server.mcpserver.exceptions import ToolError
from pdf_mcp.tools import read_text, read_layout_as_xml


def make_mixed_content_pdf(path):
    """A one-page PDF with two lines of text, some vector graphics, and an embedded image."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello world", fontsize=12, fontname="helv")
    page.insert_text((50, 80), "Second line", fontsize=10, fontname="helv")
    page.draw_line((10, 100), (200, 100), width=2, dashes="[3 3] 0")
    page.draw_rect(pymupdf.Rect(10, 110, 100, 150), width=1, fill=(1, 0, 0), color=(0, 0, 1))
    page.draw_bezier((10, 160), (30, 140), (60, 180), (90, 160), width=1.5)
    pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 10, 10), False)
    pix.set_rect(pix.irect, (255, 0, 0))
    page.insert_image(pymupdf.Rect(20, 200, 60, 240), pixmap=pix)
    doc.new_page()  # a trailing blank page
    doc.save(path)
    return str(path)


class TestReadText:
    def test_extracts_text_from_all_pages(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        text = read_text(pdf)
        assert "Hello world" in text
        assert "Second line" in text

    def test_page_range_selects_subset(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        text = read_text(pdf, page_range="2")
        assert "Hello world" not in text

    def test_invalid_page_range_raises_tool_error(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        with pytest.raises(ToolError, match="out of range"):
            read_text(pdf, page_range="99")

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            read_text(str(tmp_path / "nonexistent.pdf"))


class TestReadLayoutAsXml:
    def test_granularity_0_gives_block_level_text(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        xml = fromstring(read_layout_as_xml(pdf, page_range="1", text_granularity=0))
        boxes = xml.findall("./page/text-box")
        assert [b.text for b in boxes] == ["Hello world", "Second line"]

    def test_granularity_1_gives_line_level_text(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        xml = fromstring(read_layout_as_xml(pdf, page_range="1", text_granularity=1))
        lines = xml.findall("./page/text-box/text-line")
        assert [l.text for l in lines] == ["Hello world", "Second line"]
        assert lines[0].get("orientation") == "horizontal"

    def test_granularity_2_gives_character_level_text_with_style(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        xml = fromstring(read_layout_as_xml(
            pdf, page_range="1", text_granularity=2, include_text_style=True,
        ))
        chars = xml.findall("./page/text-box/text-line/text")
        assert "".join(c.text for c in chars[:11]) == "Hello world"
        assert chars[0].get("font") == "Helvetica"
        assert chars[0].get("size") == "12.0"

    def test_include_text_false_omits_text_boxes(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        xml = fromstring(read_layout_as_xml(pdf, page_range="1", include_text=False))
        assert xml.findall("./page/text-box") == []

    def test_include_graphics_emits_line_rect_and_curve(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        xml = fromstring(read_layout_as_xml(
            pdf, page_range="1", include_text=False, include_graphics=True,
        ))
        figures = xml.findall("./page/figure")
        assert len(figures) == 3
        child_tags = {fig[0].tag for fig in figures}
        assert child_tags == {"line", "rect", "curve"}

    def test_include_images_emits_image_with_bbox_and_xref(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        xml = fromstring(read_layout_as_xml(
            pdf, page_range="1", include_text=False, include_images=True,
        ))
        images = xml.findall("./page/image")
        assert len(images) == 1
        assert images[0].get("width") == "10"
        assert images[0].get("height") == "10"
        assert images[0].get("xref") is not None

    def test_multiple_pages_produce_multiple_page_elements(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        xml = fromstring(read_layout_as_xml(pdf))
        pages = xml.findall("./page")
        assert [p.get("page-id") for p in pages] == ["1", "2"]

    def test_invalid_page_range_raises_tool_error(self, tmp_path):
        pdf = make_mixed_content_pdf(tmp_path / "input.pdf")

        with pytest.raises(ToolError, match="out of range"):
            read_layout_as_xml(pdf, page_range="99")

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            read_layout_as_xml(str(tmp_path / "nonexistent.pdf"))

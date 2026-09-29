"""Tests for PyMuPDF-based PDF page manipulation operations."""

import pytest
import pymupdf

from mcp.server.mcpserver.exceptions import ToolError
from pdform_mcp.tools import extract_pages_from_pdf, merge_pdfs, get_page_details
from pdform_mcp.models import PageSource


def make_pdf(path, num_pages: int, label: str = "Page"):
    """Create a PDF with the given number of pages, each containing distinguishable text."""
    doc = pymupdf.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"{label} {i + 1}")
    doc.save(path)
    return str(path)


def page_texts(path):
    """Return the text of every page, in order, for content/order verification."""
    with pymupdf.open(path) as doc:
        return [page.get_text().strip() for page in doc]


class TestExtractPagesFromPdf:
    def test_extract_all_pages(self, tmp_path):
        input_pdf = make_pdf(tmp_path / "input.pdf", 5)
        output_pdf = str(tmp_path / "output.pdf")

        result = extract_pages_from_pdf(input_pdf, None, output_pdf)
        assert "5 page(s)" in result
        assert page_texts(output_pdf) == [f"Page {i}" for i in range(1, 6)]

    def test_extract_specific_range(self, tmp_path):
        input_pdf = make_pdf(tmp_path / "input.pdf", 10)
        output_pdf = str(tmp_path / "output.pdf")

        result = extract_pages_from_pdf(input_pdf, "3-7", output_pdf)
        assert "5 page(s)" in result
        assert page_texts(output_pdf) == [f"Page {i}" for i in range(3, 8)]

    def test_extract_specific_pages(self, tmp_path):
        input_pdf = make_pdf(tmp_path / "input.pdf", 10)
        output_pdf = str(tmp_path / "output.pdf")

        result = extract_pages_from_pdf(input_pdf, "1,3,5,7", output_pdf)
        assert "4 page(s)" in result
        assert page_texts(output_pdf) == ["Page 1", "Page 3", "Page 5", "Page 7"]

    def test_extract_reversed_pages_preserves_order(self, tmp_path):
        input_pdf = make_pdf(tmp_path / "input.pdf", 5)
        output_pdf = str(tmp_path / "output.pdf")

        result = extract_pages_from_pdf(input_pdf, "z-1", output_pdf)
        assert "5 page(s)" in result
        assert page_texts(output_pdf) == [f"Page {i}" for i in (5, 4, 3, 2, 1)]

    def test_extract_repeated_page(self, tmp_path):
        input_pdf = make_pdf(tmp_path / "input.pdf", 3)
        output_pdf = str(tmp_path / "output.pdf")

        result = extract_pages_from_pdf(input_pdf, "1,1,2", output_pdf)
        assert "3 page(s)" in result
        assert page_texts(output_pdf) == ["Page 1", "Page 1", "Page 2"]

    def test_overwrite_input_when_no_output_given(self, tmp_path):
        input_pdf = make_pdf(tmp_path / "input.pdf", 10)

        result = extract_pages_from_pdf(input_pdf, "1-5")
        assert "5 page(s)" in result
        assert page_texts(input_pdf) == [f"Page {i}" for i in range(1, 6)]

    def test_invalid_page_range_raises_tool_error(self, tmp_path):
        input_pdf = make_pdf(tmp_path / "input.pdf", 5)

        with pytest.raises(ToolError, match="out of range"):
            extract_pages_from_pdf(input_pdf, "1-10")

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            extract_pages_from_pdf(str(tmp_path / "nonexistent.pdf"), "1-5", str(tmp_path / "output.pdf"))


class TestMergePdfs:
    def test_merge_two_pdfs_all_pages(self, tmp_path):
        pdf1 = make_pdf(tmp_path / "a.pdf", 3, label="A")
        pdf2 = make_pdf(tmp_path / "b.pdf", 4, label="B")
        output_pdf = str(tmp_path / "merged.pdf")

        result = merge_pdfs([PageSource(file=pdf1), PageSource(file=pdf2)], output_pdf)
        assert "2 PDF(s)" in result
        assert "7 total pages" in result
        assert page_texts(output_pdf) == [f"A {i}" for i in range(1, 4)] + [f"B {i}" for i in range(1, 5)]

    def test_merge_with_page_ranges(self, tmp_path):
        pdf1 = make_pdf(tmp_path / "a.pdf", 10, label="A")
        pdf2 = make_pdf(tmp_path / "b.pdf", 10, label="B")
        output_pdf = str(tmp_path / "merged.pdf")

        sources = [
            PageSource(file=pdf1, page_range="1-3"),
            PageSource(file=pdf2, page_range="8-10"),
        ]
        result = merge_pdfs(sources, output_pdf)
        assert "6 total pages" in result
        assert page_texts(output_pdf) == ["A 1", "A 2", "A 3", "B 8", "B 9", "B 10"]

    def test_merge_with_reversed_and_repeated_ranges(self, tmp_path):
        pdf1 = make_pdf(tmp_path / "a.pdf", 3, label="A")
        pdf2 = make_pdf(tmp_path / "b.pdf", 3, label="B")
        output_pdf = str(tmp_path / "merged.pdf")

        sources = [
            PageSource(file=pdf1, page_range="1,1"),
            PageSource(file=pdf2, page_range="3-1"),
        ]
        result = merge_pdfs(sources, output_pdf)
        assert "5 total pages" in result
        assert page_texts(output_pdf) == ["A 1", "A 1", "B 3", "B 2", "B 1"]

    def test_merge_multiple_pdfs(self, tmp_path):
        pdfs = [make_pdf(tmp_path / f"{i}.pdf", 2, label=str(i)) for i in range(4)]
        output_pdf = str(tmp_path / "merged.pdf")

        result = merge_pdfs([PageSource(file=p) for p in pdfs], output_pdf)
        assert "4 PDF(s)" in result
        assert "8 total pages" in result

    def test_merge_invalid_page_range_raises_tool_error(self, tmp_path):
        pdf1 = make_pdf(tmp_path / "a.pdf", 5)
        output_pdf = str(tmp_path / "merged.pdf")

        with pytest.raises(ToolError, match="out of range"):
            merge_pdfs([PageSource(file=pdf1, page_range="1-20")], output_pdf)

    def test_merge_file_not_found_raises_tool_error(self, tmp_path):
        output_pdf = str(tmp_path / "merged.pdf")

        with pytest.raises(ToolError, match="not found"):
            merge_pdfs([PageSource(file=str(tmp_path / "nonexistent.pdf"))], output_pdf)


class TestGetPageDetails:
    def test_basic_fields(self, tmp_path):
        pdf = make_pdf(tmp_path / "input.pdf", 5)

        details = get_page_details(pdf, 3)
        assert details["index"] == 2
        assert details["label"] == "3"
        assert details["rotation"] == 0
        assert isinstance(details["xref"], int)
        assert details["annotation_count"] == 0
        assert details["image_count"] == 0

    def test_mediabox_and_cropbox(self, tmp_path):
        pdf = make_pdf(tmp_path / "input.pdf", 1)

        details = get_page_details(pdf, 1)
        # A default new_page() is A4-ish/letter-sized; just check the box is well-formed.
        box = details["mediabox"]
        assert box["left"] < box["right"]
        assert box["top"] < box["bottom"]
        assert details["cropbox"] == details["mediabox"]

    def test_out_of_range_page_raises_tool_error(self, tmp_path):
        pdf = make_pdf(tmp_path / "input.pdf", 3)

        with pytest.raises(ToolError, match="out of range"):
            get_page_details(pdf, 99)

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            get_page_details(str(tmp_path / "nonexistent.pdf"), 1)

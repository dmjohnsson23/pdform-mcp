"""Tests for PDF page manipulation operations."""

import pytest
import tempfile
import os
from pathlib import Path
from pikepdf import Pdf

from pikepdf_mcp.utils import parse_page_range
from pikepdf_mcp.tools import extract_pages_from_pdf, merge_pdfs
from pikepdf_mcp.models import PageSource


class TestParsePageRange:
    """Test the QPDF-style page range parsing function."""

    # Note: if the below tests look wrong, remember that we are also converting from a 1-indexed 
    # system to a 0-indexed system. Things will make more sense with that in mind.

    def test_none_returns_all_pages(self):
        """Test that None returns all pages."""
        result = parse_page_range(None, 10)
        assert result == list(range(10))

    def test_empty_string_returns_all_pages(self):
        """Test that empty string returns all pages."""
        result = parse_page_range("", 10)
        assert result == list(range(10))

    def test_simple_range(self):
        """Test a simple range like '1-5'."""
        result = parse_page_range("1-5", 10)
        assert result == [0, 1, 2, 3, 4]

    def test_single_page(self):
        """Test a single page number."""
        result = parse_page_range("3", 10)
        assert result == [2]

    def test_multiple_single_pages(self):
        """Test multiple single pages like '1,6,4'."""
        result = parse_page_range("1,6,4", 10)
        assert result == [0, 5, 3]

    def test_last_page_z(self):
        """Test 'z' notation for last page."""
        result = parse_page_range("z", 10)
        assert result == [9]

    def test_reverse_range_z_to_1(self):
        """Test reversed range 'z-1' (all pages reversed)."""
        result = parse_page_range("z-1", 5)
        assert result == [4, 3, 2, 1, 0]

    def test_reverse_range_descending(self):
        """Test descending range '7-3'."""
        result = parse_page_range("7-3", 10)
        assert result == [6, 5, 4, 3, 2]

    def test_r_prefix_last_page(self):
        """Test 'r1' for last page."""
        result = parse_page_range("r1", 10)
        assert result == [9]

    def test_r_prefix_second_to_last(self):
        """Test 'r2' for second-to-last page."""
        result = parse_page_range("r2", 10)
        assert result == [8]

    def test_r_prefix_range(self):
        """Test 'r3-r1' for last three pages."""
        result = parse_page_range("r3-r1", 10)
        assert result == [7, 8, 9]

    def test_r_prefix_range_reversed(self):
        """Test 'r1-r3' for last three pages reversed."""
        result = parse_page_range("r1-r3", 10)
        assert result == [9, 8, 7]

    def test_multiple_ranges(self):
        """Test multiple ranges like '1,3,5-9,15-12' (from QPDF docs)."""
        result = parse_page_range("1,3,5-9,15-12", 20)
        assert result == [0, 2, 4, 5, 6, 7, 8, 14, 13, 12, 11]

    def test_mixed_pages_and_ranges(self):
        """Test mixed single pages and ranges '5,7-9,12'."""
        result = parse_page_range("5,7-9,12", 20)
        assert result == [4, 6, 7, 8, 11]

    def test_range_with_last_page(self):
        """Test range '1-z' for all pages."""
        result = parse_page_range("1-z", 10)
        assert result == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    def test_even_filter(self):
        """Test ':even' filter on range '1-20:even'."""
        result = parse_page_range("1-20:even", 20)
        # Even positions: 2nd, 4th, 6th, ... = pages 2, 4, 6, 8, 10, 12, 14, 16, 18, 20
        assert result == [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]

    def test_odd_filter(self):
        """Test ':odd' filter on range '1-20:odd'."""
        result = parse_page_range("1-20:odd", 20)
        # Odd positions: 1st, 3rd, 5th, ... = pages 1, 3, 5, 7, 9, 11, 13, 15, 17, 19
        assert result == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

    def test_odd_filter_on_selection(self):
        """Test ':odd' filter on '5,7-9,12:odd' (from QPDF docs)."""
        result = parse_page_range("5,7-9,12:odd", 20)
        # Pages 5,7,8,9,12 -> odd positions (1st, 3rd, 5th) -> 5, 8, 12
        assert result == [4, 7, 11]

    def test_even_filter_on_selection(self):
        """Test ':even' filter on '5,7-9,12:even' (from QPDF docs)."""
        result = parse_page_range("5,7-9,12:even", 20)
        # Pages 5,7,8,9,12 -> even positions (2nd, 4th) -> 7, 9
        assert result == [6, 8]

    def test_exclusion_simple(self):
        """Test exclusion 'x' operator: '1-10,x3-4'."""
        result = parse_page_range("1-10,x3-4", 20)
        # Pages 1-10 except 3-4 = 1,2,5,6,7,8,9,10
        assert result == [0, 1, 4, 5, 6, 7, 8, 9]

    def test_exclusion_complex(self):
        """Test complex exclusion from QPDF docs: '4-10,x7-9,12-8,xr5' in 15-page file."""
        result = parse_page_range("4-10,x7-9,12-8,xr5", 15)
        # 4-10 = 4,5,6,7,8,9,10
        # x7-9 removes 7,8,9 -> 4,5,6,10
        # 12-8 = 12,11,10,9,8
        # xr5 removes page 11 (r5 in 15-page = page 11) -> 12,10,9,8
        # Combined: 4,5,6,10,12,10,9,8
        assert result == [3, 4, 5, 9, 11, 9, 8, 7]

    def test_out_of_range_raises_error(self):
        """Test that out of range pages raise ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            parse_page_range("1-20", 10)

    def test_invalid_filter_raises_error(self):
        """Test that invalid filters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid filter"):
            parse_page_range("1-10:invalid", 10)


class TestExtractPages:
    """Test the extract_pages_from_pdf function."""

    def create_test_pdf(self, num_pages: int) -> str:
        """Create a test PDF with the specified number of pages."""
        pdf = Pdf.new()
        for i in range(num_pages):
            page = pdf.add_blank_page(page_size=(612, 792))

        temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False)
        pdf.save(temp_file.name)
        temp_file.close()
        return temp_file.name

    def test_extract_all_pages(self):
        """Test extracting all pages (no page range specified)."""
        input_pdf = self.create_test_pdf(5)
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            result = extract_pages_from_pdf(input_pdf, None, output_pdf)
            assert "5 page(s)" in result

            # Verify output
            with Pdf.open(output_pdf) as pdf:
                assert len(pdf.pages) == 5
        finally:
            os.unlink(input_pdf)
            os.unlink(output_pdf)

    def test_extract_specific_range(self):
        """Test extracting a specific range of pages."""
        input_pdf = self.create_test_pdf(10)
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            result = extract_pages_from_pdf(input_pdf, "3-7", output_pdf)
            assert "5 page(s)" in result

            # Verify output
            with Pdf.open(output_pdf) as pdf:
                assert len(pdf.pages) == 5
        finally:
            os.unlink(input_pdf)
            os.unlink(output_pdf)

    def test_extract_specific_pages(self):
        """Test extracting specific pages."""
        input_pdf = self.create_test_pdf(10)
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            result = extract_pages_from_pdf(input_pdf, "1,3,5,7", output_pdf)
            assert "4 page(s)" in result

            # Verify output
            with Pdf.open(output_pdf) as pdf:
                assert len(pdf.pages) == 4
        finally:
            os.unlink(input_pdf)
            os.unlink(output_pdf)

    def test_extract_reversed_pages(self):
        """Test extracting pages in reverse order."""
        input_pdf = self.create_test_pdf(5)
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            result = extract_pages_from_pdf(input_pdf, "z-1", output_pdf)
            assert "5 page(s)" in result

            # Verify output has all pages
            with Pdf.open(output_pdf) as pdf:
                assert len(pdf.pages) == 5
        finally:
            os.unlink(input_pdf)
            os.unlink(output_pdf)

    def test_overwrite_input(self):
        """Test overwriting the input file when no output path specified."""
        input_pdf = self.create_test_pdf(10)

        try:
            result = extract_pages_from_pdf(input_pdf, "1-5")
            assert "5 page(s)" in result

            # Verify input was overwritten
            with Pdf.open(input_pdf) as pdf:
                assert len(pdf.pages) == 5
        finally:
            os.unlink(input_pdf)

    def test_invalid_page_range(self):
        """Test that invalid page ranges raise appropriate errors."""
        input_pdf = self.create_test_pdf(5)

        try:
            from mcp.server.mcpserver.exceptions import ToolError
            with pytest.raises(ToolError, match="out of range"):
                extract_pages_from_pdf(input_pdf, "1-10")
        finally:
            os.unlink(input_pdf)

    def test_file_not_found(self):
        """Test that missing files raise appropriate errors."""
        from mcp.server.mcpserver.exceptions import ToolError
        with pytest.raises(ToolError, match="not found"):
            extract_pages_from_pdf("/nonexistent/file.pdf", "1-5", "/tmp/output.pdf")


class TestMergePDFs:
    """Test the merge_pdfs function."""

    def create_test_pdf(self, num_pages: int) -> str:
        """Create a test PDF with the specified number of pages."""
        pdf = Pdf.new()
        for i in range(num_pages):
            page = pdf.add_blank_page(page_size=(612, 792))

        temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False)
        pdf.save(temp_file.name)
        temp_file.close()
        return temp_file.name

    def test_merge_two_pdfs_all_pages(self):
        """Test merging two PDFs with all pages."""
        pdf1 = self.create_test_pdf(3)
        pdf2 = self.create_test_pdf(4)
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            sources = [
                PageSource(file=pdf1),
                PageSource(file=pdf2),
            ]
            result = merge_pdfs(sources, output_pdf)
            assert "2 PDF(s)" in result
            assert "7 total pages" in result

            # Verify output
            with Pdf.open(output_pdf) as pdf:
                assert len(pdf.pages) == 7
        finally:
            os.unlink(pdf1)
            os.unlink(pdf2)
            os.unlink(output_pdf)

    def test_merge_with_page_ranges(self):
        """Test merging PDFs with specific page ranges."""
        pdf1 = self.create_test_pdf(10)
        pdf2 = self.create_test_pdf(10)
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            sources = [
                PageSource(file=pdf1, page_range="1-3"),
                PageSource(file=pdf2, page_range="8-10"),
            ]
            result = merge_pdfs(sources, output_pdf)
            assert "2 PDF(s)" in result
            assert "6 total pages" in result

            # Verify output
            with Pdf.open(output_pdf) as pdf:
                assert len(pdf.pages) == 6
        finally:
            os.unlink(pdf1)
            os.unlink(pdf2)
            os.unlink(output_pdf)

    def test_merge_specific_pages(self):
        """Test merging specific pages from PDFs."""
        pdf1 = self.create_test_pdf(5)
        pdf2 = self.create_test_pdf(5)
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            sources = [
                PageSource(file=pdf1, page_range="1,3,5"),
                PageSource(file=pdf2, page_range="2,4"),
            ]
            result = merge_pdfs(sources, output_pdf)
            assert "2 PDF(s)" in result
            assert "5 total pages" in result

            # Verify output
            with Pdf.open(output_pdf) as pdf:
                assert len(pdf.pages) == 5
        finally:
            os.unlink(pdf1)
            os.unlink(pdf2)
            os.unlink(output_pdf)

    def test_merge_multiple_pdfs(self):
        """Test merging multiple PDFs."""
        pdfs = [self.create_test_pdf(2) for _ in range(4)]
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            sources = [PageSource(file=pdf) for pdf in pdfs]
            result = merge_pdfs(sources, output_pdf)
            assert "4 PDF(s)" in result
            assert "8 total pages" in result

            # Verify output
            with Pdf.open(output_pdf) as pdf:
                assert len(pdf.pages) == 8
        finally:
            for pdf in pdfs:
                os.unlink(pdf)
            os.unlink(output_pdf)

    def test_merge_with_reversed_pages(self):
        """Test merging with reversed page order."""
        pdf1 = self.create_test_pdf(5)
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            sources = [
                PageSource(file=pdf1, page_range="z-1"),
            ]
            result = merge_pdfs(sources, output_pdf)
            assert "5 total pages" in result

            # Verify output
            with Pdf.open(output_pdf) as pdf:
                assert len(pdf.pages) == 5
        finally:
            os.unlink(pdf1)
            os.unlink(output_pdf)

    def test_merge_invalid_page_range(self):
        """Test that invalid page ranges raise appropriate errors."""
        pdf1 = self.create_test_pdf(5)
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            from mcp.server.mcpserver.exceptions import ToolError
            sources = [
                PageSource(file=pdf1, page_range="1-20"),
            ]
            with pytest.raises(ToolError, match="out of range"):
                merge_pdfs(sources, output_pdf)
        finally:
            os.unlink(pdf1)
            if os.path.exists(output_pdf):
                os.unlink(output_pdf)

    def test_merge_file_not_found(self):
        """Test that missing files raise appropriate errors."""
        output_pdf = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False).name

        try:
            from mcp.server.mcpserver.exceptions import ToolError
            sources = [
                PageSource(file="/nonexistent/file.pdf"),
            ]
            with pytest.raises(ToolError, match="not found"):
                merge_pdfs(sources, output_pdf)
        finally:
            if os.path.exists(output_pdf):
                os.unlink(output_pdf)

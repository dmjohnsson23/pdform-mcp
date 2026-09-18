"""Tools for extracting and merging PDF pages."""

from typing import Annotated, Optional, Sequence

from pikepdf import Pdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError

from pikepdf_mcp.models import PageSource
from pikepdf_mcp.utils import parse_page_range


def extract_pages_from_pdf(
    input_path: Annotated[str, Field(description="Path to the source PDF file.")],
    page_range: Annotated[
        Optional[str],
        Field(description="QPDF page range: '1-5' (range), '1,3,5' (specific), 'z' (last), 'r1' (last), 'r2' (second-to-last), '7-3' (reversed), '1-20:even' (even positions), '1-10,x3-4' (exclude 3-4). Omit for all pages.")
    ] = None,
    output_path: Annotated[
        Optional[str],
        Field(description="Path for the output PDF. If omitted, overwrites the input file.")
    ] = None,
) -> str:
    """
    Extract specific pages from a PDF file and create a new PDF with only those pages.

    Uses QPDF page range syntax:
    - Numbers are 1-indexed: '1' = first page, '5' = fifth page
    - 'z' = last page, 'r1' = last page, 'r2' = second-to-last, etc.
    - Ranges: '1-5' = pages 1-5, '5-1' = pages 5,4,3,2,1 (reversed)
    - Comma-separated: '1,3,5,7-9' = pages 1, 3, 5, 7, 8, 9
    - Filters: '1-20:even' = even positions, '1-20:odd' = odd positions
    - Exclusions: '1-10,x3-4' = pages 1,2,5,6,7,8,9,10 (excludes 3-4)
    """
    try:
        with Pdf.open(input_path) as src_pdf:
            total_pages = len(src_pdf.pages)
            page_indices = parse_page_range(page_range, total_pages)
            _validate_page_indices(page_indices, input_path, total_pages)
            dst_pdf = Pdf.new()
            dst_pdf.add_pages_from(src_pdf, page_indices)
            output = output_path if output_path else input_path
            dst_pdf.save(output)
            return f"Successfully extracted {len(page_indices)} page(s) from {input_path} to {output}"

    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {input_path}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to extract pages: {str(e)}")


def merge_pdfs(
    sources: Annotated[Sequence[PageSource], Field(description="List of PDF sources with optional QPDF page ranges to merge.")],
    output_path: Annotated[str, Field(description="Path for the merged output PDF.")],
) -> str:
    """
    Merge pages from multiple PDF files into a single PDF.

    Pages are combined in the order specified. Each source can specify a QPDF-style page range.
    See extract_pages_from_pdf documentation for complete page range syntax.
    """
    try:
        merged_pdf = Pdf.new()
        total_pages_added = 0

        for source in sources:
            with Pdf.open(source.file) as src_pdf:
                total_pages = len(src_pdf.pages)
                page_indices = parse_page_range(source.page_range, total_pages)
                _validate_page_indices(page_indices, source.file, total_pages)
                merged_pdf.add_pages_from(src_pdf, page_indices)
                total_pages_added += len(page_indices)
        merged_pdf.save(output_path)
        return f"Successfully merged {len(sources)} PDF(s) ({total_pages_added} total pages) into {output_path}"

    except FileNotFoundError as e:
        raise ToolError(f"PDF file not found: {str(e)}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to merge PDFs: {str(e)}")


def _validate_page_indices(page_indices:list[int], filename:str, total_pages:int):
        invalid_pages = [i for i in page_indices if i < 0 or i >= total_pages]
        if invalid_pages:
            raise ToolError(
                f"Invalid page indices in {filename} (out of range 1-{total_pages}): "
                f"{[i+1 for i in invalid_pages]}"
            )

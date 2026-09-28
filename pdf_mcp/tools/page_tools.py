"""Tools for extracting and merging PDF pages."""

from typing import Annotated, Optional, Sequence

import pymupdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError

from pdf_mcp.models import PageSource
from pdf_mcp.utils import parse_page_range, rect_to_dict


def extract_pages_from_pdf(
    input_path: Annotated[str, Field(description="Path to the source PDF file.")],
    page_range: Annotated[
        Optional[str],
        Field(description="Page range: '1-5' (range), '1,3,5' (specific), 'z' (last), 'r1' (last), 'r2' (second-to-last), '7-3' (reversed), '1-20:even' (even positions), '1-10,x3-4' (exclude 3-4). Omit for all pages.")
    ] = None,
    output_path: Annotated[
        Optional[str],
        Field(description="Path for the output PDF. If omitted, overwrites the input file.")
    ] = None,
) -> str:
    """
    Extract specific pages from a PDF file and create a new PDF with only those pages.
    """
    try:
        with pymupdf.open(input_path) as src_pdf:
            page_indices = parse_page_range(page_range, src_pdf.page_count)
            src_pdf.select(page_indices)
            # A document can't be saved back over the file it was opened from (except
            # incrementally), so render to bytes first and write those out ourselves.
            data = src_pdf.tobytes()
        output = output_path if output_path else input_path
        with open(output, "wb") as f:
            f.write(data)
        return f"Successfully extracted {len(page_indices)} page(s) from {input_path} to {output}"

    except pymupdf.FileNotFoundError:
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
        merged_pdf = pymupdf.open()
        total_pages_added = 0

        for source in sources:
            with pymupdf.open(source.file) as src_pdf:
                page_indices = parse_page_range(source.page_range, src_pdf.page_count)
                # select() reorders/subsets src_pdf in place (supporting arbitrary QPDF-style
                # ranges, including reversed and repeated pages); insert_pdf then copies it whole.
                src_pdf.select(page_indices)
                merged_pdf.insert_pdf(src_pdf)
                total_pages_added += len(page_indices)
        merged_pdf.save(output_path)
        return f"Successfully merged {len(sources)} PDF(s) ({total_pages_added} total pages) into {output_path}"

    except pymupdf.FileNotFoundError as e:
        raise ToolError(f"PDF file not found: {str(e)}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to merge PDFs: {str(e)}")


def get_page_details(
    path: Annotated[str, Field(description="Path to the PDF file to read.")],
    page: Annotated[int, Field(description="The page number to inspect (1-indexed).")],
) -> dict:
    """Get basic information about a specific page."""
    try:
        with pymupdf.open(path) as pdf:
            if page < 1 or page > pdf.page_count:
                raise ToolError(
                    f"Invalid page number {page} for {path} (out of range 1-{pdf.page_count})"
                )
            pdf_page = pdf[page - 1]

            return {
                "index": pdf_page.number,
                # get_label() returns '' when there's no explicit /PageLabels entry; fall back to
                # the default numbering (matching what a reader would display in that case).
                "label": pdf_page.get_label() or str(pdf_page.number + 1),
                "xref": pdf_page.xref,
                "rotation": pdf_page.rotation,
                "mediabox": rect_to_dict(pdf_page.mediabox),
                "cropbox": rect_to_dict(pdf_page.cropbox),
                "annotation_count": len(pdf_page.annot_xrefs()),
                "image_count": len(pdf_page.get_images()),
            }
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to read page details: {str(e)}")

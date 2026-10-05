"""Tools for drawing text or graphics onto PDF pages."""

from typing import Annotated, Optional

import pymupdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError

from pdform_mcp.utils import parse_page_range, open_pdf_rw


def draw_image(
    input_path: Annotated[str, Field(description="Path to the source PDF file.")],
    image_path: Annotated[str, Field(description="Path to the image to add.")],
    rect: Annotated[tuple[float,float,float,float], Field(description='The location on the page to paste the image.')],
    rotate: Annotated[int, Field(description='The rotation to apply, if desired.', multiple_of=90)] = 0,
    overlay: Annotated[bool, Field(description='If true, this is an overlay. If false, an underlay.')] = True,
    page_range: Annotated[
        Optional[str],
        Field(description="Page range, e.g. '1-5' or '1,3,5'.  Omit for all pages.")
    ] = None,
    output_path: Annotated[
        Optional[str],
        Field(description="Path for the output PDF. If omitted, overwrites the input file.")
    ] = None,
) -> str:
    """
    Add an overlay or underlay image.
    """
    try:
        with open_pdf_rw(input_path, output_path) as pdf:
            image_xref = 0
            for index in parse_page_range(page_range, pdf.page_count):
                page = pdf[index]
                image_xref = page.insert_image(rect, filename=image_path, rotate=rotate, overlay=overlay, xref=image_xref)
        return f"Successfully added images to {output_path or input_path}"

    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {input_path}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to extract pages: {str(e)}")

# TODO
# - insert_text
# - insert_textbox
# - insert_htmlbox


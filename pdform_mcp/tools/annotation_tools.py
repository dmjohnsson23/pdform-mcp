"""Tools for working with PDF annotations."""

from typing import Annotated, Optional, Literal, Union, Sequence, Mapping

import pymupdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError

from pdform_mcp.utils import  open_pdf_rw, rect_to_list


def list_annotations_on_page(
    path: Annotated[str, Field(description='The PDF to read.')],
    page: Annotated[int, Field(description="The page to list annotations for.")],
    )->Sequence[Mapping]:
    """List all annotations on the given page, with some basic information about each."""
    try:
        with pymupdf.open(path) as pdf:
            pdf_page = pdf[page-1]
        return [_annot_summary(annot) for annot in pdf_page.annots()]
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read annotations from PDF: {str(e)}")


def _annot_summary(annot:pymupdf.Annot):
    return {
        'type': annot.type[1:],
        'rect': rect_to_list(annot.rect),
        'rotation': max(0, annot.rotation), # -1 is a special value that means "no rotation value exists" so we clamp to 0
        'info': annot.info,
        'xref':  annot.xref,
        'popup_xref': annot.popup_xref or None,
        'responds_to_xref': annot.irt_xref or None,
    }


def add_text_marker_annotation(
    input_path: Annotated[str, Field(description="Path to the source PDF file.")],
    page: Annotated[int, Field(description="The page to add the annotation to.")],
    rect_or_quad: Annotated[Union[tuple[float,float,float,float],tuple[tuple[float,float],tuple[float,float],tuple[float,float],tuple[float,float]]], Field(description='The location on the page to add the annotation. You\'ll typically use `locate_text_on_page` or `locate_text_on_page_as_quads` to get this value.')],
    type: Annotated[Literal['highlight','underline','strikeout','squiggle'], Field(description='The type of annotation to add')],
    output_path: Annotated[
        Optional[str],
        Field(description="Path for the output PDF. If omitted, overwrites the input file.")
    ] = None,
):
    """
    Add a text marker annotation (highlight, underline, etc...).
    """
    try:
        with open_pdf_rw(input_path, output_path) as pdf:
            pdf_page = pdf[page-1]
            if type == 'highlight':
                annot = pdf_page.add_highlight_annot(rect_or_quad)
            elif type == 'underline':
                annot = pdf_page.add_underline_annot(rect_or_quad)
            elif type == 'strikeout':
                annot = pdf_page.add_strikeout_annot(rect_or_quad)
            elif type == 'squiggle':
                annot = pdf_page.add_squiggly_annot(rect_or_quad)
            else:
                raise ToolError('Unknown annotation type')
        return f"Successfully added annotation to {output_path or input_path} (new xref: {annot.xref})"

    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {input_path}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to extract pages: {str(e)}")

    
def add_ink_annotation(
    input_path: Annotated[str, Field(description="Path to the source PDF file.")],
    page: Annotated[int, Field(description="The page to add the annotation to.")],
    points: Annotated[list[list[tuple[float,float]]], Field(description='Each sub-list is a list of connected points in the drawing.')],
    output_path: Annotated[
        Optional[str],
        Field(description="Path for the output PDF. If omitted, overwrites the input file.")
    ] = None,
):
    """
    Add a free-hand ink drawing annotation.
    """
    try:
        with open_pdf_rw(input_path, output_path) as pdf:
            pdf_page = pdf[page-1]
            annot = pdf_page.add_ink_annot(points)
        return f"Successfully added annotation to {output_path or input_path} (new xref: {annot.xref})"

    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {input_path}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to extract pages: {str(e)}")


def add_free_text_annotation_as_html(
    input_path: Annotated[str, Field(description="Path to the source PDF file.")],
    page: Annotated[int, Field(description="The page to add the annotation to.")],
    rect: Annotated[tuple[float,float,float,float], Field(description='The location on the page to add the annotation. Text will be wrapped at the box width.')],
    html: Annotated[str, Field(description='The HTML content to add. May be a fragment.')],
    css: Annotated[Optional[str], Field(description='Optional CSS to style the HTML.')],
    rotate: Annotated[int, Field(description='The rotation to apply, if desired.', multiple_of=90)] = 0,
    opacity: Annotated[float, Field(description='The opacity of the annotation.', ge=0, le=1)] = 1,
    border_width: Annotated[float, Field(description='The with of the border line to add around the annotation.')] = 0,
    border_color: Annotated[Optional[list[float]], Field(description='The color of the border line to add around the annotation.', max_length=4)] = None,
    fill_color: Annotated[Optional[list[float]], Field(description='The color of the background add behind the annotation content.', max_length=4)] = None,
    output_path: Annotated[
        Optional[str],
        Field(description="Path for the output PDF. If omitted, overwrites the input file.")
    ] = None,
):
    """
    Add a free text annotation (floating text) using a simple subset of HTML syntax.

    Basic tags like `<h1-6>`, `<p>`, `<b>`, and `<i>` are supported, as well as basic CSS like `align`, `font-size`, and `color`.
    """
    try:
        with open_pdf_rw(input_path, output_path) as pdf:
            pdf_page = pdf[page-1]
            annot = pdf_page.add_freetext_annot(
                rect, 
                html, 
                richtext=True, 
                style=css, 
                rotate=rotate, 
                opacity=opacity, 
                border_width=border_width,
                border_color=border_color,
                fill_color=fill_color,
            )
        return f"Successfully added annotation to {output_path or input_path} (new xref: {annot.xref})"

    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {input_path}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to extract pages: {str(e)}")



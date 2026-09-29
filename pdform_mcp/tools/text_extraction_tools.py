from typing import Annotated, Optional, Mapping
from xml.etree.ElementTree import Element, SubElement, tostring

import pymupdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError
from pdform_mcp.utils.output_helpers import rect_to_dict

from pdform_mcp.utils import parse_page_range


def read_layout_as_xml(
    path: Annotated[str, Field(description='The PDF to read.')],
    page_range: Annotated[
        Optional[str],
        Field(description="The page range or pages to extract, e.g. '1-4' or '3,5,8'. Omit for all pages.")
    ] = None,
    include_text: Annotated[bool, Field(description='If true, include text objects in the output')] = True,
    include_graphics: Annotated[bool, Field(description='If true, include figure objects, lines, curves, and rectangles in the output.')] = False,
    include_images: Annotated[bool, Field(description='If true, include image objects in the output.')] = False,
    text_granularity: Annotated[int, Field(description='The level of granularity at which to show text. Use 0 for large text blocks, 1 for individual lines, and 2 for individual characters.', ge=0, le=2)]=0,
    include_text_style: Annotated[bool, Field(description='If true, includes graphical information about text, such as font and size. This is only relevant if `text_granularity` >= 2')] = False,
    )->str:
    """
    Show the layout of the PDF content (text, images, lines, figures) in a bespoke XML format.

    This is useful for understanding the positions of text or other objects on the page, and understanding the document hierarchy.
    """
    try:
        with pymupdf.open(path) as pdf:
            include_pages = parse_page_range(page_range, pdf.page_count)
            xml = Element('document')
            for index in include_pages:
                page = pdf[index]
                page_xml = SubElement(xml, 'page', {
                    'page-id': str(index + 1),
                    'rotate': str(page.rotation),
                })
                if include_text:
                    _text_to_xml(page, page_xml, text_granularity, include_text_style)
                if include_graphics:
                    for drawing in page.get_drawings():
                        _drawing_to_xml(drawing, page_xml)
                if include_images:
                    for image in page.get_image_info(xrefs=True):
                        _image_to_xml(image, page_xml)
            return tostring(xml, 'unicode')
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to read layout from PDF: {str(e)}")


def read_text(
    path: Annotated[str, Field(description='The PDF to read.')],
    page_range: Annotated[
        Optional[str],
        Field(description="The page range or pages to extract, e.g. '1-4' or '3,5,8'. Omit for all pages.")
    ] = None,
    ) -> str:
    """Extract the plain text content of a PDF."""
    try:
        with pymupdf.open(path) as pdf:
            include_pages = parse_page_range(page_range, pdf.page_count)
            return '\f'.join(pdf[index].get_text() for index in include_pages)
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to read text from PDF: {str(e)}")

    
def locate_text_on_page(
    path: Annotated[str, Field(description='The PDF to read.')],
    page: Annotated[int, Field(description="The page to locate text on, indexed from 1.")],
    text: Annotated[str, Field(description='The text to search for.')]
    ) -> list[Mapping]:
    """
    Search a page for a specific string and return the rectangles of where it was found on the page.
    """
    try:
        with pymupdf.open(path) as pdf:
            pdf_page = pdf[page-1]
            areas = pdf_page.search_for(text)
            return [rect_to_dict(rect) for rect in areas]
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to read text from PDF: {str(e)}")


def _bbox_str(bbox) -> str:
    return f'{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}'


def _pts_str(points) -> str:
    return ' '.join(f'{p[0]},{p[1]}' for p in points)


def _color_to_str(color) -> str:
    return ','.join(str(c) for c in color)


# Note: page.get_text() already has an XML mode we could use instead, but doing it ourselves lets us
# turn down the noise level by excluding things. Our XML format is similar but not compatible.
def _text_to_xml(page: pymupdf.Page, xml_parent: Element, text_granularity: int, include_text_style: bool):
    for block in page.get_text('rawdict')['blocks']:
        if block['type'] != 0:  # 1 = image block; images are handled separately via include_images
            continue
        block_xml = SubElement(xml_parent, 'text-box', {'bbox': _bbox_str(block['bbox'])})
        if text_granularity == 0:
            block_xml.text = '\n'.join(
                ''.join(char['c'] for span in line['spans'] for char in span['chars'])
                for line in block['lines']
            )
            continue
        for line in block['lines']:
            horizontal = abs(line['dir'][0]) >= abs(line['dir'][1])
            line_xml = SubElement(block_xml, 'text-line', {
                'bbox': _bbox_str(line['bbox']),
                'orientation': 'horizontal' if horizontal else 'vertical',
            })
            if text_granularity == 1:
                line_xml.text = ''.join(char['c'] for span in line['spans'] for char in span['chars'])
                continue
            for span in line['spans']:
                for char in span['chars']:
                    attrs = {'bbox': _bbox_str(char['bbox'])}
                    if include_text_style:
                        attrs['font'] = span['font']
                        attrs['size'] = str(span['size'])
                        attrs['upright'] = 'true' if horizontal else 'false'
                    char_xml = SubElement(line_xml, 'text', attrs)
                    char_xml.text = char['c']


def _drawing_to_xml(drawing: dict, xml_parent: Element):
    attrs = {
        'bbox': _bbox_str(drawing['rect']),
        'linewidth': str(drawing['width'] or 0),
        'stroke': 'true' if drawing['color'] is not None else 'false',
        'fill': 'true' if drawing['fill'] is not None else 'false',
        'evenodd': 'true' if drawing['even_odd'] else 'false',
    }
    if drawing['color'] is not None:
        attrs['stroking-color'] = _color_to_str(drawing['color'])
    if drawing['fill'] is not None:
        attrs['non-stroking-color'] = _color_to_str(drawing['fill'])
    if drawing['dashes']:
        attrs['dashing-style'] = drawing['dashes']
    figure_xml = SubElement(xml_parent, 'figure', attrs)
    for item in drawing['items']:
        _drawing_item_to_xml(item, figure_xml)


def _drawing_item_to_xml(item: tuple, xml_parent: Element):
    op = item[0]
    if op == 'l':
        SubElement(xml_parent, 'line', {'pts': _pts_str(item[1:3])})
    elif op == 'c':
        SubElement(xml_parent, 'curve', {'pts': _pts_str(item[1:5])})
    elif op == 're':
        rect = item[1]
        corners = [(rect.x0, rect.y0), (rect.x1, rect.y0), (rect.x1, rect.y1), (rect.x0, rect.y1)]
        SubElement(xml_parent, 'rect', {'pts': _pts_str(corners)})
    elif op == 'qu':
        quad = item[1]
        SubElement(xml_parent, 'quad', {'pts': _pts_str([quad.ul, quad.ur, quad.lr, quad.ll])})


def _image_to_xml(image: dict, xml_parent: Element):
    SubElement(xml_parent, 'image', {
        'bbox': _bbox_str(image['bbox']),
        'xref': str(image['xref']),
        'width': str(image['width']),
        'height': str(image['height']),
    })

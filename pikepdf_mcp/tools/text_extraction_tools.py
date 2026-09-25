from typing import Annotated, Optional, Any
from pdfminer.high_level import extract_pages, extract_text
from pdfminer.layout import LTText, LTComponent, LTImage, LTItem, LTPage, LTTextBox, LTTextBoxHorizontal, LTTextLineHorizontal, LTTextBoxVertical, LTTextLineVertical, LTTextLine, LTCurve, LTLine, LTRect, LTChar, LTAnno, LTFigure
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError
from pikepdf_mcp.utils import parse_page_range
from xml.etree.ElementTree import Element, SubElement, tostring
from pikepdf import Pdf

def read_layout_as_xml(
    path: Annotated[str, Field(description='The PDF to read.')],
    page_range: Annotated[
        Optional[str],
        Field(description="The page range or pages to extract, e.g. '1-4' or '3,5,8'. Omit for all pages.")
    ] = None,
    include_text: Annotated[bool, Field(description='If true, include text objects in the output')] = True,
    include_graphics: Annotated[bool, Field(description='If true, include figure objects, lines, curves, and rectangles in the output.')] = False,
    include_images: Annotated[bool, Field(description='If true, include image objects in the output. As images may be inside of figures, you should usually also set `include_graphics` to true.')] = False,
    text_granularity: Annotated[int, Field(description='The level of granularity at which to show text. Use 0 for large text blocks, 1 for individual lines, and 2 for individual characters, words, or other small snippets.', ge=0, le=2)]=0,
    include_text_style: Annotated[bool, Field(description='If true, includes graphical information about text, such as font, size, and spacing. This is only relevant if `text_granularity` >= 1')] = False,
    )->str:
    """
    Show the layout of the PDF content (text, images, lines, figures) in a bespoke XML format.

    This is useful for understanding the positions of text or other objects on the page, and understanding the document hierarchy.
    """
    pages = list(extract_pages(path)) # This does have a `pages` parameter but we can't use it because we need a page count to parse a page range...
    include_pages = parse_page_range(page_range, len(pages))
    _validate_page_indices(include_pages, path, len(pages))
    xml = Element('document')
    for index in include_pages:
        page = pages[index]
        _layout_to_xml(page, xml, include_text, include_graphics, include_images, text_granularity, include_text_style)
    return tostring(xml, 'unicode')


def read_text(
    path: Annotated[str, Field(description='The PDF to read.')],
    page_range: Annotated[
        Optional[str],
        Field(description="The page range or pages to extract, e.g. '1-4' or '3,5,8'. Omit for all pages.")
    ] = None,
    ):
    with open(path, 'rb') as file:
        if page_range is not None:
            # We have to open with pikepdf first to get the page count, then open with pdfminer to get the actual text
            pages = len(Pdf.open(file).pages)
            include_pages = parse_page_range(page_range, pages)
        else:
            include_pages = None
        return extract_text(file, page_numbers=include_pages)


def _color_to_str(color: Any) -> str:
    if isinstance(color, tuple):
        return ','.join(_color_to_str(c) for c in color)
    return str(color)


def _path_segment_to_str(segment: tuple) -> str:
    op, *points = segment
    return ' '.join([op, *(f'{x},{y}' for x, y in points)])

# Note: extract_text already has an xml mode we could use instead, but doing it ourselves lets us 
# turn down the noise level by excluding things. Our XML format is similar but not compatible.
def _layout_to_xml(item:LTItem, xml_parent:Element, include_text:bool, include_graphics:bool, include_images:bool, text_granularity:int, include_text_style:bool):
    tag = None
    attrs = {}
    text_body = None
    has_children = False

    if isinstance(item, LTText) and not include_text:
        return
    if isinstance(item, (LTCurve, LTFigure)) and not include_graphics:
        return
    if isinstance(item, LTImage) and not include_images:
        return

    # Basic mapping for tags and common attrs
    if isinstance(item, LTPage):
        tag = 'page'
        has_children = True
        attrs['page-id'] = str(item.pageid)
        attrs['rotate'] = str(item.rotate)
    elif isinstance(item, LTTextBox):
        tag = 'text-box'
        if text_granularity >= 1:
            has_children = True
        else:
            text_body = item.get_text()
    elif isinstance(item, LTTextLine):
        tag = 'text-line'
        if include_text_style:
            attrs['word-margin'] = str(item.word_margin)
        if text_granularity >= 2:
            has_children = True
        else:
            text_body = item.get_text()
    elif isinstance(item, (LTChar, LTAnno)):
        tag = 'text'
        text_body = item.get_text()
    elif isinstance(item, LTLine):
        tag = 'line'
    elif isinstance(item, LTRect):
        tag = 'rect'
    elif isinstance(item, LTCurve):
        tag = 'curve'
    elif isinstance(item, LTImage):
        tag = 'image'
        attrs['name'] = item.name
        if item.stream.objid is not None:
            attrs['stream-objgen'] = f"{item.stream.objid} {item.stream.genno}" 
    elif isinstance(item, LTFigure):
        tag = 'figure'
        has_children = True
        attrs['name'] = item.name
        attrs['matrix'] = ','.join(str(f) for f in item.matrix)

    if tag is None:
        return

    # More general attr mappings
    if isinstance(item, LTComponent):
        attrs['bbox'] = ','.join([str(f) for f in item.bbox])

    if isinstance(item, (LTTextBoxHorizontal, LTTextLineHorizontal)):
        attrs['orientation'] = 'horizontal'
    elif isinstance(item, (LTTextBoxVertical, LTTextLineVertical)):
        attrs['orientation'] = 'vertical'

    if isinstance(item, LTCurve):
        attrs['linewidth'] = str(item.linewidth)
        attrs['pts'] = ' '.join(f'{x},{y}' for x, y in item.pts)
        attrs['stroke'] = 'true' if item.stroke else 'false'
        attrs['fill'] = 'true' if item.fill else 'false'
        attrs['evenodd'] = 'true' if item.evenodd else 'false'
        if item.stroking_color is not None:
            attrs['stroking-color'] = _color_to_str(item.stroking_color)
        if item.non_stroking_color is not None:
            attrs['non-stroking-color'] = _color_to_str(item.non_stroking_color)
        if item.original_path is not None:
            attrs['original-path'] = ' '.join(_path_segment_to_str(seg) for seg in item.original_path)
        if item.dashing_style is not None:
            attrs['dashing-style'] = str(item.dashing_style)

    if isinstance(item, LTChar) and include_text_style:
        attrs['font'] = item.fontname
        attrs['size'] = str(item.size)
        attrs['adv'] = str(item.adv)
        attrs['upright'] = 'true' if item.upright else 'false'
        attrs['matrix'] = ','.join(str(f) for f in item.matrix)

    xml = SubElement(xml_parent, tag, attrs)
    if has_children:
        for child in item:
            _layout_to_xml(child, xml, include_text, include_graphics, include_images, text_granularity, include_text_style)
    elif text_body is not None:
        xml.text = text_body


def _validate_page_indices(page_indices:list[int], filename:str, total_pages:int):
        invalid_pages = [i for i in page_indices if i < 0 or i >= total_pages]
        if invalid_pages:
            raise ToolError(
                f"Invalid page indices in {filename} (out of range 1-{total_pages}): "
                f"{[i+1 for i in invalid_pages]}"
            )
"""Tool implementations for pdf-mcp."""

from pdform_mcp.tools.acroform_tools import (
    list_acroform_fields,
    list_acroform_fields_on_page,
    get_acroform_field_details,
    fill_acroform_fields,
)

from pdform_mcp.tools.document_tools import (
    get_document_details,
    flatten,
)

from pdform_mcp.tools.drawing_tools import (
    draw_image,
)

from pdform_mcp.tools.low_level_tools import (
    low_level_read_object,
    low_level_read_stream,
    low_level_read_object_value,
    low_level_set_object_value,
    low_level_smart_set_object_value,
)

from pdform_mcp.tools.page_tools import (
    extract_pages_from_pdf,
    merge_pdfs,
    get_page_details,
)

from pdform_mcp.tools.render_tools import (
    render,
)

from pdform_mcp.tools.text_extraction_tools import (
    read_layout_as_xml,
    locate_text_on_page,
    locate_text_on_page_as_quads,
    read_text,
)

__all__ = [
    "list_acroform_fields",
    "get_acroform_field_details",
    "list_acroform_fields_on_page",
    "fill_acroform_fields",
    "low_level_read_object",
    "low_level_read_stream",
    "low_level_read_object_value",
    "low_level_set_object_value",
    "low_level_smart_set_object_value",
    "extract_pages_from_pdf",
    "merge_pdfs",
    "get_page_details",
    "render",
    "get_document_details",
    "flatten",
    "draw_image",
    "read_layout_as_xml",
    "locate_text_on_page",
    "locate_text_on_page_as_quads",
    "read_text",
]

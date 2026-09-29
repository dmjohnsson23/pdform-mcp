"""MCP server setup and tool registration for pdf-mcp."""

from mcp.server import MCPServer

from pdform_mcp.tools import (
    list_acroform_fields,
    list_acroform_fields_on_page,
    get_acroform_field_details,
    low_level_read_object,
    low_level_read_stream,
    low_level_read_object_value,
    low_level_set_object_value,
    low_level_smart_set_object_value,
    extract_pages_from_pdf,
    merge_pdfs,
    get_page_details,
    render,
    get_document_details,
    read_layout_as_xml,
    locate_text_on_page,
    read_text,
)


mcp = MCPServer(
    "pdf",
    description="Tools for inspecting and working with PDF documents on a deep level",
    instructions="Be aware that, except for the low-level tools, all tools translate coordinates for rects and bboxes from PDF space (origin at the bottom left) to screen space (origin at the top left)."
)


for tool in (
    list_acroform_fields,
    list_acroform_fields_on_page,
    get_acroform_field_details,
    low_level_read_object,
    low_level_read_stream,
    low_level_read_object_value,
    low_level_set_object_value,
    low_level_smart_set_object_value,
    extract_pages_from_pdf,
    merge_pdfs,
    get_page_details,
    render,
    get_document_details,
    read_layout_as_xml,
    locate_text_on_page,
    read_text,
):
    mcp.tool()(tool)
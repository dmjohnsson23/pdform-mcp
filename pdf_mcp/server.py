"""MCP server setup and tool registration for pdf-mcp."""

from mcp.server import MCPServer
from mcp.types import ImageContent, TextContent

from pdf_mcp.tools import (
    list_acroform_fields,
    list_acroform_fields_on_page,
    get_acroform_field_details,
    describe_qpdf_json_format,
    read_pdf_as_json,
    read_pdf_object_as_json,
    write_pdf_from_json,
    update_pdf_from_json,
    extract_pages_from_pdf,
    merge_pdfs,
    get_page_details,
    get_document_details,
    validate_pdf,
    read_layout_as_xml,
    locate_text_on_page,
    read_text,
)


mcp = MCPServer("pikepdf")


for tool in (
    list_acroform_fields,
    list_acroform_fields_on_page,
    get_acroform_field_details,
    describe_qpdf_json_format,
    read_pdf_as_json,
    read_pdf_object_as_json,
    write_pdf_from_json,
    update_pdf_from_json,
    extract_pages_from_pdf,
    merge_pdfs,
    get_page_details,
    get_document_details,
    validate_pdf,
    read_layout_as_xml,
    locate_text_on_page,
    read_text,
):
    mcp.tool()(tool)
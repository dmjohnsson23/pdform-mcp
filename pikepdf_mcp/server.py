"""MCP server setup and tool registration for pikepdf-mcp."""

from mcp.server import MCPServer

from pikepdf_mcp.tools import (
    list_acroform_fields,
    get_acroform_field_details,
    describe_qpdf_json_format,
    read_pdf_as_json,
    read_pdf_object_as_json,
    write_pdf_from_json,
    update_pdf_from_json,
    extract_pages_from_pdf,
    merge_pdfs,
    validate_pdf,
)


mcp = MCPServer("pikepdf")


for tool in (
    list_acroform_fields,
    get_acroform_field_details,
    describe_qpdf_json_format,
    read_pdf_as_json,
    read_pdf_object_as_json,
    write_pdf_from_json,
    update_pdf_from_json,
    extract_pages_from_pdf,
    merge_pdfs,
    validate_pdf,
):
    mcp.tool()(tool)

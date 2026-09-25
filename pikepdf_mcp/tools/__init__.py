"""Tool implementations for pikepdf-mcp."""

from pikepdf_mcp.tools.acroform_tools import (
    list_acroform_fields,
    list_acroform_fields_on_page,
    get_acroform_field_details,
)

from pikepdf_mcp.tools.document_tools import (
    get_document_details,
    validate_pdf,
)

from pikepdf_mcp.tools.json_tools import (
    describe_qpdf_json_format,
    read_pdf_as_json,
    read_pdf_object_as_json,
    write_pdf_from_json,
    update_pdf_from_json,
)

from pikepdf_mcp.tools.page_tools import (
    extract_pages_from_pdf,
    merge_pdfs,
    get_page_details,
)

from pikepdf_mcp.tools.text_extraction_tools import (
    read_layout_as_xml,
    read_text,
)

__all__ = [
    "list_acroform_fields",
    "get_acroform_field_details",
    "list_acroform_fields_on_page",
    "describe_qpdf_json_format",
    "read_pdf_as_json",
    "read_pdf_object_as_json",
    "write_pdf_from_json",
    "update_pdf_from_json",
    "extract_pages_from_pdf",
    "merge_pdfs",
    "get_page_details",
    "get_document_details",
    "validate_pdf",
    "read_layout_as_xml",
]

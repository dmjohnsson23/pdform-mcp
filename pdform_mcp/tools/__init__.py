"""Tool implementations for pdf-mcp."""

from pdform_mcp.tools.acroform_tools import (
    list_acroform_fields,
    list_acroform_fields_on_page,
    get_acroform_field_details,
    fill_acroform_fields,
    add_acroform_widget,
    delete_acroform_widget,
)

from pdform_mcp.tools.document_tools import (
    get_document_details,
    flatten,
    read_table_of_contents,
)

from pdform_mcp.tools.drawing_tools import (
    draw_image,
)

from pdform_mcp.tools.low_level_tools import (
    low_level_read_object,
    low_level_read_stream,
    low_level_read_object_value,
    low_level_write_object,
    low_level_write_object_as_json,
    low_level_set_object_value,
    low_level_set_object_value_as_json,
    low_level_create_indirect_object,
    low_level_create_indirect_object_as_json,
    low_level_write_stream,
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
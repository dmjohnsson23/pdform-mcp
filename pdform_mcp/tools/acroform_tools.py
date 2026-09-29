import pymupdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError
from pdform_mcp.utils.output_helpers import rect_to_dict
from typing import Annotated, Optional, Sequence, Mapping


def _widget_summary(widget: pymupdf.Widget) -> Mapping:
    return {
        'fully_qualified_name': widget.field_name,
        'alternate_name': widget.field_label,
        'type': widget.field_type_string,
        # For a radio button group, `xref` is just one of the button widgets; `rb_parent` is the
        # xref of the shared field object (0 for non-radio fields, which have no such parent).
        'xref': widget.rb_parent if widget.rb_parent else widget.xref,
    }


def _xref_key(pdf: pymupdf.Document, xref: int, key: str) -> Optional[str]:
    kind, value = pdf.xref_get_key(xref, key)
    if kind == 'null':
        return None
    if kind == 'name':
        return value.lstrip('/')
    return value


def list_acroform_fields(
    path: Annotated[str, Field(description='The PDF to read.')],
    )->Sequence[Mapping]:
    """List all terminal fields in the AcroForm, with some basic information about each."""
    try:
        with pymupdf.open(path) as pdf:
            # A radio button group shows up as one widget per button, all sharing the same (fully
            # qualified) field_name, so we dedup by name to report the group once. dict (rather than
            # set) preserves first-seen order.
            fields = {}
            for page in pdf:
                for widget in page.widgets():
                    fields.setdefault(widget.field_name, widget)
            return [_widget_summary(widget) for widget in fields.values()]
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read form data from PDF: {str(e)}")


def list_acroform_fields_on_page(
    path: Annotated[str, Field(description='The PDF to read.')],
    page: Annotated[int, Field(description='The page number to select fields from, indexed from 1.')],
    )->Sequence[Mapping]:
    """List all terminal fields on a specific page, with some basic information about each."""
    try:
        with pymupdf.open(path) as pdf:
            if page < 1 or page > pdf.page_count:
                raise ToolError(f"Invalid page number {page} for {path} (out of range 1-{pdf.page_count})")
            fields = {}
            for widget in pdf[page - 1].widgets():
                fields.setdefault(widget.field_name, widget)
            return [_widget_summary(widget) for widget in fields.values()]
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to read form data from PDF: {str(e)}")


def get_acroform_field_details(
    path: Annotated[str, Field(description='The PDF to read.')],
    fully_qualified_name: Annotated[str, Field(description='The name of the field to inspect.')],
    )->dict:
    """Get more detailed information about a specific acroform field."""
    try:
        with pymupdf.open(path) as pdf:
            # Widgets keep only a weak reference to their page, so the pages must stay alive here:
            # `on_state()`/`button_states()` below need it, and it would otherwise be garbage
            # collected as soon as the loop below moves to the next page.
            pages = list(pdf)
            widgets = [w for page in pages for w in page.widgets() if w.field_name == fully_qualified_name]
            if not widgets:
                raise ToolError(f"No field named {fully_qualified_name!r} found in {path}")
            widget = widgets[0]
            field_type = widget.field_type_string
            flags = widget.field_flags

            out = {
                'fully_qualified_name': widget.field_name,
                'alternate_name': widget.field_label,
                'xref': widget.rb_parent if widget.rb_parent else widget.xref,
                'is_required': bool(flags & pymupdf.PDF_FIELD_IS_REQUIRED),
                'is_read_only': bool(flags & pymupdf.PDF_FIELD_IS_READ_ONLY),
                'export_enabled': not (flags & pymupdf.PDF_FIELD_IS_NO_EXPORT),
                'field_flags': flags,
                'type': field_type,
            }
            if len(widgets) == 1:
                out['annotation_flags'] = int(_xref_key(pdf, widget.xref, 'F') or 0)
                out['rectangle'] = rect_to_dict(widget.rect)

            if field_type == 'Text':
                out['value'] = widget.field_value
                out['is_multiline'] = bool(flags & pymupdf.PDF_TX_FIELD_IS_MULTILINE)
                out['default_value'] = _xref_key(pdf, widget.xref, 'DV')
                out['is_combed'] = bool(flags & pymupdf.PDF_TX_FIELD_IS_COMB)
                out['is_file_select'] = bool(flags & pymupdf.PDF_TX_FIELD_IS_FILE_SELECT)
                out['is_password'] = bool(flags & pymupdf.PDF_TX_FIELD_IS_PASSWORD)
                out['is_rich_text'] = bool(flags & pymupdf.PDF_TX_FIELD_IS_RICH_TEXT)
                out['max_length'] = widget.text_maxlen
                out['scrolling_enabled'] = not (flags & pymupdf.PDF_TX_FIELD_IS_DO_NOT_SCROLL)
                out['spell_check_enabled'] = not (flags & pymupdf.PDF_TX_FIELD_IS_DO_NOT_SPELL_CHECK)
            elif field_type == 'CheckBox':
                out['checked'] = widget.field_value == widget.on_state()
                out['value'] = widget.field_value
                out['allowed_values'] = tuple(widget.button_states()['normal'])
            elif field_type == 'RadioButton':
                # Each button is its own widget/annotation sharing one field_name; `rb_parent` is the
                # xref of the shared field, which is where the group's selected value (/V) actually lives.
                out['value'] = _xref_key(pdf, widget.rb_parent, 'V') if widget.rb_parent else None
                out['allowed_values'] = tuple(w.on_state() for w in widgets)
                out['radio_buttons'] = [
                    {
                        'name': _xref_key(pdf, option.xref, 'NM'),
                        'value': option.on_state(),
                        'xref': option.xref,
                        'annotation_flags': int(_xref_key(pdf, option.xref, 'F') or 0),
                        'rectangle': rect_to_dict(option.rect),
                    }
                    for option in widgets
                ]
            elif field_type in ('ComboBox', 'ListBox'):
                out['value'] = widget.field_value
                out['is_combobox'] = field_type == 'ComboBox'
                out['is_multiselect'] = bool(flags & pymupdf.PDF_CH_FIELD_IS_MULTI_SELECT)
                out['spell_check_enabled'] = not (flags & pymupdf.PDF_CH_FIELD_IS_DO_NOT_SPELL_CHECK)
                out['allowed_values'] = tuple(
                    option[1] if isinstance(option, (tuple, list)) else option
                    for option in (widget.choice_values or [])
                )
                out['allow_custom_values'] = bool(flags & pymupdf.PDF_CH_FIELD_IS_EDIT)
            return out
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to read form data from PDF: {str(e)}")
    
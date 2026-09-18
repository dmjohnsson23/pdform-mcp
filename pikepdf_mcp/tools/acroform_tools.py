from pikepdf import Pdf, Name
from pikepdf.form import Form, TextField, CheckboxField, RadioButtonGroup, ChoiceField, SignatureField, PushbuttonField
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError
from typing import Annotated, Sequence, Mapping

def list_acroform_fields(
    path: Annotated[str, Field(description='The PDF to read.')],
    )->Sequence[Mapping]:
    """List all terminal fields in the AcroForm, with some basic information about each."""
    try:
        pdf = Pdf.open(path)
        out = []
        for field in pdf.acroform.fields:
            out.append({
                'fully_qualified_name': field.fully_qualified_name,
                'alternate_name': field.alternate_name,
                'type': 'checkbox' if field.is_checkbox else
                        'choice' if field.is_choice else
                        'pushbutton' if field.is_pushbutton else
                        'radio' if field.is_radio_button else
                        'text' if field.is_text else 'other'
                        'signature' if field.field_type == Name.Sig else 'other',
                'objgen': field.obj.objgen if field.obj.is_indirect else None,
            })
        return out
    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read form data from PDF: {str(e)}")


def list_acroform_fields_on_page(
    path: Annotated[str, Field(description='The PDF to read.')],
    page: Annotated[int, Field(description='The page number to select fields from.')],
    )->Sequence[Mapping]:
    """List all terminal fields on a specific page, with some basic information about each."""
    try:
        pdf = Pdf.open(path)
        form = pdf.acroform
        out = []
        # Get a list of widgets on this page
        # Note that, because of a quirk of how QPDF handles radio buttons, we can't directly use the widget 
        # objects below to fetch the field. Otherwise, we'd get individual radio buttons rather than the whole
        # radio button group together, and we'd have messed-up duplicates. This seemingly-unnecessary 
        # double-loop bypasses all that mess. (Also, we use dict instead of set just to preserve insertion order)
        fields_on_page = dict()
        for widget in form.get_widget_annotations_for_page(pdf.pages.p(page)):
            field = form.get_field_for_annotation(widget)
            fields_on_page[field.fully_qualified_name] = None
        for field_name in fields_on_page.keys():
            field = form.get_fields_with_qualified_name(field_name)[0]
            out.append({
                'fully_qualified_name': field.fully_qualified_name,
                'alternate_name': field.alternate_name,
                'type': 'checkbox' if field.is_checkbox else
                        'choice' if field.is_choice else
                        'pushbutton' if field.is_pushbutton else
                        'radio' if field.is_radio_button else
                        'text' if field.is_text else 'other'
                        'signature' if field.field_type == Name.Sig else 'other',
                'objgen': field.obj.objgen if field.obj.is_indirect else None,
            })
        return out
    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read form data from PDF: {str(e)}")


def get_acroform_field_details(
    path: Annotated[str, Field(description='The PDF to read.')],
    fully_qualified_name: Annotated[str, Field(description='The name of the field to inspect.')], 
    )->dict:
    """Get more detailed information about a specific acroform field."""
    try:
        pdf = Pdf.open(path)
        form = Form(pdf)
        field = form[fully_qualified_name]
        annot = form._acroform.get_annotations_for_field(field._field)[0]
        out = {
            'fully_qualified_name': field.fully_qualified_name,
            'alternate_name': field.alternate_name,
            'objgen': field.obj.objgen if field.obj.is_indirect else None,
            'is_required': field.is_required,
            'is_read_only': field.is_read_only,
            'export_enabled': field.export_enabled,
            'annotation_flags': annot.flags,
            'field_flags': field.flags,
            'rectangle': {
                'left': annot.rect.llx,
                'right': annot.rect.urx,
                'top': annot.rect.ury,
                'bottom': annot.rect.lly,
            }
        }
        if isinstance(field, TextField):
            out['type'] = 'text'
            out['value'] = field.value
            out['is_multiline'] = field.is_multiline
            out['default_value'] = field.default_value
            out['is_combed'] = field.is_combed
            out['is_file_select'] = field.is_file_select
            out['is_password'] = field.is_password
            out['is_rich_text'] = field.is_rich_text
            out['max_length'] = field.max_length
            out['scrolling_enabled'] = field.scrolling_enabled
            out['spell_check_enabled'] = field.spell_check_enabled
        elif isinstance(field, CheckboxField):
            out['type'] = 'checkbox'
            out['checked'] = field.checked
            out['value'] = field.value
            out['allowed_values'] = tuple(map(str, field.states))
        elif isinstance(field, RadioButtonGroup):
            out['type'] = 'radio'
            out['value'] = field.value
            out['allowed_values'] = tuple(map(str, field.states))
        elif isinstance(field, ChoiceField):
            out['type'] = 'choice'
            out['value'] = field.value
            out['is_combobox'] = field.is_combobox
            out['is_multiselect'] = field.is_multiselect
            out['spell_check_enabled'] = field.spell_check_enabled
            out['allowed_values'] = tuple(map(lambda option: option.display_value, field.options))
            out['allow_custom_values'] = field.allow_edit
        elif isinstance(field, SignatureField):
            out['type'] = 'signature'
        elif isinstance(field, PushbuttonField):
            out['type'] = 'pushbutton'
        return out
    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read form data from PDF: {str(e)}")
    
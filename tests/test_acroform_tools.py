"""Tests for PyMuPDF-based AcroForm field inspection tools."""

import pytest
import pymupdf
from pikepdf import Pdf, Dictionary, Array, Name, String

from mcp.server.mcpserver.exceptions import ToolError
from pdf_mcp.tools import list_acroform_fields, list_acroform_fields_on_page, get_acroform_field_details


def make_widget_pdf(path):
    """A PDF with one text field on page 1 and one combobox on page 2.

    Built directly with PyMuPDF's own widget API, which is sufficient for simple
    (non-radio) fields.
    """
    doc = pymupdf.open()
    doc.new_page()
    doc.new_page()
    # Widgets need a page bound to the doc (via a live weakref); the Page object returned
    # directly by new_page() doesn't have that, so fetch the pages back out by index instead.
    page1 = doc[0]
    page2 = doc[1]

    text = pymupdf.Widget()
    text.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    text.field_name = "name"
    text.field_label = "Full Name"
    text.rect = pymupdf.Rect(50, 50, 200, 70)
    page1.add_widget(text)

    checkbox = pymupdf.Widget()
    checkbox.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
    checkbox.field_name = "agree"
    checkbox.rect = pymupdf.Rect(50, 100, 70, 120)
    page1.add_widget(checkbox)

    combo = pymupdf.Widget()
    combo.field_type = pymupdf.PDF_WIDGET_TYPE_COMBOBOX
    combo.field_name = "color"
    combo.choice_values = ["Red", "Green", "Blue"]
    combo.rect = pymupdf.Rect(50, 150, 200, 170)
    page2.add_widget(combo)

    doc.save(path)
    return str(path)


def make_radio_group_pdf(path, selected="B"):
    """A PDF with a two-option radio button group on page 1.

    PyMuPDF's high-level widget API can't build a proper /Kids radio group (it only
    supports one field per widget), so this is built directly with pikepdf instead.
    """
    pdf = Pdf.new()
    page = pdf.add_blank_page(page_size=(200, 200))

    parent = pdf.make_indirect(Dictionary(FT=Name.Btn, T=String("choice"), Ff=1 << 15, Kids=Array([])))

    def make_kid(rect, on_value):
        selected_as = Name(f"/{on_value}") if on_value == selected else Name.Off
        kid = Dictionary(
            Type=Name.Annot,
            Subtype=Name.Widget,
            Rect=Array(rect),
            Parent=parent,
            AS=selected_as,
            NM=String(f"radio_{on_value}"),
            AP=Dictionary(N=Dictionary({
                f'/{on_value}': pdf.make_indirect(Dictionary(Type=Name.XObject, Subtype=Name.Form, BBox=Array([0, 0, 20, 20]), Length=0)),
                '/Off': pdf.make_indirect(Dictionary(Type=Name.XObject, Subtype=Name.Form, BBox=Array([0, 0, 20, 20]), Length=0)),
            })),
        )
        return pdf.make_indirect(kid)

    kid_a = make_kid([50, 150, 70, 170], "A")
    kid_b = make_kid([80, 150, 100, 170], "B")
    parent.Kids = Array([kid_a, kid_b])
    parent.V = Name(f"/{selected}")
    page.Annots = Array([kid_a, kid_b])
    pdf.Root.AcroForm = Dictionary(Fields=Array([parent]), NeedAppearances=True)
    pdf.save(path)
    return str(path)


class TestListAcroformFields:
    def test_lists_all_terminal_fields(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        fields = list_acroform_fields(pdf)
        names = {f["fully_qualified_name"] for f in fields}
        assert names == {"name", "agree", "color"}

    def test_field_summary_shape(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        fields = {f["fully_qualified_name"]: f for f in list_acroform_fields(pdf)}
        assert fields["name"]["type"] == "Text"
        assert fields["name"]["alternate_name"] == "Full Name"
        assert fields["agree"]["type"] == "CheckBox"
        assert fields["color"]["type"] == "ComboBox"

    def test_radio_group_reported_once_with_shared_xref(self, tmp_path):
        pdf = make_radio_group_pdf(tmp_path / "radio.pdf")

        fields = list_acroform_fields(pdf)
        assert len(fields) == 1
        assert fields[0]["fully_qualified_name"] == "choice"
        assert fields[0]["type"] == "RadioButton"

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            list_acroform_fields(str(tmp_path / "nonexistent.pdf"))


class TestListAcroformFieldsOnPage:
    def test_filters_by_page(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        page1_fields = {f["fully_qualified_name"] for f in list_acroform_fields_on_page(pdf, 1)}
        page2_fields = {f["fully_qualified_name"] for f in list_acroform_fields_on_page(pdf, 2)}
        assert page1_fields == {"name", "agree"}
        assert page2_fields == {"color"}

    def test_invalid_page_raises_tool_error(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        with pytest.raises(ToolError, match="out of range"):
            list_acroform_fields_on_page(pdf, 99)

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            list_acroform_fields_on_page(str(tmp_path / "nonexistent.pdf"), 1)


class TestGetAcroformFieldDetails:
    def test_text_field(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        details = get_acroform_field_details(pdf, "name")
        assert details["type"] == "Text"
        assert details["alternate_name"] == "Full Name"
        assert "rectangle" in details
        assert "annotation_flags" in details

    def test_checkbox_field(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        details = get_acroform_field_details(pdf, "agree")
        assert details["type"] == "CheckBox"
        assert set(details["allowed_values"]) == {"Off", "Yes"}

    def test_combobox_field(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        details = get_acroform_field_details(pdf, "color")
        assert details["type"] == "ComboBox"
        assert details["allowed_values"] == ("Red", "Green", "Blue")
        assert details["is_combobox"] is True

    def test_radio_group_reports_shared_value_and_all_buttons(self, tmp_path):
        pdf = make_radio_group_pdf(tmp_path / "radio.pdf", selected="B")

        details = get_acroform_field_details(pdf, "choice")
        assert details["type"] == "RadioButton"
        assert details["value"] == "B"
        assert set(details["allowed_values"]) == {"A", "B"}
        assert len(details["radio_buttons"]) == 2
        # No single-annotation `rectangle`/`annotation_flags` for a multi-widget group.
        assert "rectangle" not in details

    def test_unknown_field_raises_tool_error(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        with pytest.raises(ToolError, match="No field named"):
            get_acroform_field_details(pdf, "nope")

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            get_acroform_field_details(str(tmp_path / "nonexistent.pdf"), "name")

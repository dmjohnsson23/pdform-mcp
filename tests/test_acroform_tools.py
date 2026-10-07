"""Tests for PyMuPDF-based AcroForm field inspection tools."""

import pytest
import pymupdf
from pikepdf import Pdf, Dictionary, Array, Name, String

from mcp.server.mcpserver.exceptions import ToolError
from pdform_mcp.tools import list_acroform_fields, list_acroform_fields_on_page, get_acroform_field_details, add_acroform_widget, fill_acroform_fields
from pdform_mcp.models import TextWidget, CheckBoxWidget, RadioButtonWidget, ComboBoxWidget, ListBoxWidget


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

    PyMuPDF will be fixed in the next release and we can remove dependency on PikePDF.
    See <https://github.com/pymupdf/PyMuPDF/issues/5165>.
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
        assert len(details["radio_buttons"]) == 2
        assert {b["value"] for b in details["radio_buttons"]} == {"A", "B"}
        # No single-annotation `rectangle`/`annotation_flags` for a multi-widget group.
        assert "rectangle" not in details

    def test_unknown_field_raises_tool_error(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        with pytest.raises(ToolError, match="No field named"):
            get_acroform_field_details(pdf, "nope")

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            get_acroform_field_details(str(tmp_path / "nonexistent.pdf"), "name")


class TestAddAcroformWidget:
    def test_adds_widget_to_page(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")
        widget = TextWidget(name="extra", rect=[50, 200, 200, 220])

        result = add_acroform_widget(pdf, 2, widget)

        assert "new xref" in result
        page2 = {f["fully_qualified_name"] for f in list_acroform_fields_on_page(pdf, 2)}
        assert page2 == {"color", "extra"}

    def test_writes_to_output_path(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")
        out = str(tmp_path / "out.pdf")

        add_acroform_widget(pdf, 1, TextWidget(name="extra", rect=[50, 200, 200, 220]), out)

        assert "extra" in {f["fully_qualified_name"] for f in list_acroform_fields(out)}
        assert "extra" not in {f["fully_qualified_name"] for f in list_acroform_fields(pdf)}

    @pytest.mark.parametrize("page", [0, -1, 3, 99])
    def test_invalid_page_raises_tool_error(self, tmp_path, page):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        with pytest.raises(ToolError, match="out of range"):
            add_acroform_widget(pdf, page, TextWidget(name="extra", rect=[0, 0, 10, 10]))

    def test_file_not_found_raises_tool_error(self, tmp_path):
        with pytest.raises(ToolError, match="not found"):
            add_acroform_widget(str(tmp_path / "missing.pdf"), 1, TextWidget(name="x", rect=[0, 0, 10, 10]))


class TestAddAcroformWidgetTypes:
    def _details(self, pdf, name):
        return get_acroform_field_details(pdf, name)

    def test_checkbox(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        add_acroform_widget(pdf, 1, CheckBoxWidget(name="newcheck", rect=[50, 300, 70, 320], is_required=True))

        d = self._details(pdf, "newcheck")
        assert d["type"] == "CheckBox"
        assert d["is_required"] is True
        assert d["checked"] is False

    def test_checkbox_can_be_checked_after_creation(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")
        add_acroform_widget(pdf, 1, CheckBoxWidget(name="newcheck", rect=[50, 300, 70, 320]))

        fill_acroform_fields(pdf, {"newcheck": True})

        assert self._details(pdf, "newcheck")["checked"] is True

    def test_radio_button(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        add_acroform_widget(pdf, 1, RadioButtonWidget(name="grp", rect=[50, 350, 70, 370]))

        assert self._details(pdf, "grp")["type"] == "RadioButton"

    @pytest.mark.xfail(
        strict=True,
        reason="PyMuPDF 1.28.2 add_widget does not create a /Parent//Kids radio group for same-named radio buttons, despite its documentation. Will be fixed in next PyMuPdf release, see <https://github.com/pymupdf/PyMuPDF/issues/5165>.",
    )
    def test_same_named_radio_buttons_form_one_group(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        add_acroform_widget(pdf, 1, RadioButtonWidget(name="grp", rect=[50, 350, 70, 370]))
        add_acroform_widget(pdf, 1, RadioButtonWidget(name="grp", rect=[80, 350, 100, 370]))

        details = self._details(pdf, "grp")
        assert len(details["radio_buttons"]) == 2
        assert details["xref"] != details["radio_buttons"][0]["xref"]

    def test_combobox(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        add_acroform_widget(
            pdf, 1,
            ComboBoxWidget(name="newcombo", rect=[50, 400, 200, 420], choices=["X", "Y"], editable=True),
        )

        fill_acroform_fields(pdf, {"newcombo": "Y"})

        d = self._details(pdf, "newcombo")
        assert d["type"] == "ComboBox"
        assert d["allowed_values"] == ("X", "Y")
        assert d["value"] == "Y"
        assert d["allow_custom_values"] is True

    def test_listbox(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        add_acroform_widget(
            pdf, 1,
            ListBoxWidget(name="newlist", rect=[50, 450, 200, 520], choices=["A", "B", "C"], multiselect=True),
        )

        d = self._details(pdf, "newlist")
        assert d["type"] == "ListBox"
        assert d["allowed_values"] == ("A", "B", "C")
        assert d["is_multiselect"] is True

    def test_text_options(self, tmp_path):
        pdf = make_widget_pdf(tmp_path / "form.pdf")

        add_acroform_widget(
            pdf, 1,
            TextWidget(name="opts", rect=[50, 550, 200, 570], multiline=True, password=True, max_length=10),
        )

        fill_acroform_fields(pdf, {"opts": "hi"})

        d = self._details(pdf, "opts")
        assert d["value"] == "hi"
        assert d["is_multiline"] is True
        assert d["is_password"] is True
        assert d["max_length"] == 10

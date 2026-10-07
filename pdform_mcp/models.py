"""Pydantic models for pdf-mcp tools."""

from typing import Optional, Union, Literal, List, Annotated
from pydantic import BaseModel, Field
import pymupdf


class PageSource(BaseModel):
    """Represents a source PDF file with an optional page range for extraction."""

    file: str = Field(description="Path to the PDF file to take pages from.")
    page_range: Optional[str] = Field(
        default=None,
        description="QPDF page range: '1-5', '1,3,5', 'z' (last), 'r1-r3' (last 3), "
                    "'7-3' (reversed), '1-20:even', '1-10,x3-4'. Omit for all pages."
    )


class TextWidget(BaseModel):
    """A text input widget."""
    type: Literal["text"] = "text"
    name: str = Field(description="Fully qualified field name")
    rect: List[float] = Field(description="Widget rectangle [x0, y0, x1, y1]")
    multiline: bool = Field(default=False, description="Allow multiple lines")
    password: bool = Field(default=False, description="Mask input as password")
    is_required: bool = Field(default=False, description="Field is required")
    max_length: Optional[int] = Field(default=None, description="Maximum character length")

    def to_widget(self) -> pymupdf.Widget:
        """Convert to pymupdf.Widget object ready for add_widget()."""
        widget = pymupdf.Widget()
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.field_name = self.name
        widget.rect = pymupdf.Rect(self.rect)
        if self.multiline:
            widget.field_flags |= pymupdf.PDF_TX_FIELD_IS_MULTILINE
        if self.password:
            widget.field_flags |= pymupdf.PDF_TX_FIELD_IS_PASSWORD
        if self.is_required:
            widget.field_flags |= pymupdf.PDF_FIELD_IS_REQUIRED
        if self.max_length:
            widget.text_maxlen = self.max_length
        return widget


class CheckBoxWidget(BaseModel):
    """A checkbox widget."""
    type: Literal["checkbox"] = "checkbox"
    name: str = Field(description="Fully qualified field name")
    rect: List[float] = Field(description="Widget rectangle [x0, y0, x1, y1]")
    is_required: bool = Field(default=False, description="Field is required")

    def to_widget(self) -> pymupdf.Widget:
        """Convert to pymupdf.Widget object ready for add_widget()."""
        widget = pymupdf.Widget()
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
        widget.field_name = self.name
        widget.rect = pymupdf.Rect(self.rect)
        if self.is_required:
            widget.field_flags |= pymupdf.PDF_FIELD_IS_REQUIRED
        return widget


class RadioButtonWidget(BaseModel):
    """A single radio button in a group."""
    type: Literal["radio"] = "radio"
    name: str = Field(description="Fully qualified field name (shared by group)")
    rect: List[float] = Field(description="Widget rectangle [x0, y0, x1, y1]")
    is_required: bool = Field(default=False, description="Field is required")

    def to_widget(self) -> pymupdf.Widget:
        """Convert to pymupdf.Widget object ready for add_widget()."""
        widget = pymupdf.Widget()
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON
        widget.field_name = self.name
        widget.field_value = False  # PyMuPDF raises "bad xref" when adding a radio widget that is not explicitly off
        widget.rect = pymupdf.Rect(self.rect)
        if self.is_required:
            widget.field_flags |= pymupdf.PDF_FIELD_IS_REQUIRED
        return widget


class ComboBoxWidget(BaseModel):
    """A dropdown (combo box) widget."""
    type: Literal["combobox"] = "combobox"
    name: str = Field(description="Fully qualified field name")
    rect: List[float] = Field(description="Widget rectangle [x0, y0, x1, y1]")
    choices: List[str] = Field(description="Available options")
    editable: bool = Field(default=False, description="Allow custom values")
    is_required: bool = Field(default=False, description="Field is required")

    def to_widget(self) -> pymupdf.Widget:
        """Convert to pymupdf.Widget object ready for add_widget()."""
        widget = pymupdf.Widget()
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_COMBOBOX
        widget.field_name = self.name
        widget.rect = pymupdf.Rect(self.rect)
        widget.choice_values = self.choices
        if self.editable:
            widget.field_flags |= pymupdf.PDF_CH_FIELD_IS_EDIT
        if self.is_required:
            widget.field_flags |= pymupdf.PDF_FIELD_IS_REQUIRED
        return widget


class ListBoxWidget(BaseModel):
    """A list box (selection) widget."""
    type: Literal["listbox"] = "listbox"
    name: str = Field(description="Fully qualified field name")
    rect: List[float] = Field(description="Widget rectangle [x0, y0, x1, y1]")
    choices: List[str] = Field(description="Available options")
    multiselect: bool = Field(default=False, description="Allow multiple selections")
    is_required: bool = Field(default=False, description="Field is required")

    def to_widget(self) -> pymupdf.Widget:
        """Convert to pymupdf.Widget object ready for add_widget()."""
        widget = pymupdf.Widget()
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_LISTBOX
        widget.field_name = self.name
        widget.rect = pymupdf.Rect(self.rect)
        widget.choice_values = self.choices
        if self.multiselect:
            widget.field_flags |= pymupdf.PDF_CH_FIELD_IS_MULTI_SELECT
        if self.is_required:
            widget.field_flags |= pymupdf.PDF_FIELD_IS_REQUIRED
        return widget


PDFWidget = Annotated[
    Union[TextWidget, CheckBoxWidget, RadioButtonWidget, ComboBoxWidget, ListBoxWidget],
    Field(discriminator="type")
]

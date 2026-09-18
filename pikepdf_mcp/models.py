"""Pydantic models for pikepdf-mcp tools."""

from typing import Optional
from pydantic import BaseModel, Field


class PageSource(BaseModel):
    """Represents a source PDF file with an optional page range for extraction."""

    file: str = Field(description="Path to the PDF file to take pages from.")
    page_range: Optional[str] = Field(
        default=None,
        description="QPDF page range: '1-5', '1,3,5', 'z' (last), 'r1-r3' (last 3), "
                    "'7-3' (reversed), '1-20:even', '1-10,x3-4'. Omit for all pages."
    )

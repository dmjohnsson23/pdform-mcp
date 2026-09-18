"""Tools for validating PDF files."""

from typing import Annotated, Sequence

from pikepdf import Pdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError


def validate_pdf(
    path: Annotated[str, Field(description='The PDF to check.')]
) -> Sequence[str]:
    """
    Check a PDF, returning a list of any identified issues.
    """
    try:
        pdf = Pdf.open(path)
        return pdf.check_pdf_syntax()
    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to validate PDF: {str(e)}")

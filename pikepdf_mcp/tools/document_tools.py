"""Tools for getting general information about a PDF document."""

from typing import Annotated, Optional, Sequence

from pikepdf import Pdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError


def get_document_details(
    path: Annotated[str, Field(description="Path to the PDF file to read.")],
) -> dict:
    """Get general information about a PDF document, such as page count, version, and metadata."""
    try:
        with Pdf.open(path) as pdf:
            docinfo = pdf.docinfo if "/Info" in pdf.trailer else None

            def _info(key: str) -> Optional[str]:
                if docinfo is None or key not in docinfo:
                    return None
                return str(docinfo[key])

            return {
                "page_count": len(pdf.pages),
                "pdf_version": pdf.pdf_version,
                "extension_level": pdf.extension_level,
                "is_encrypted": pdf.is_encrypted,
                "is_linearized": pdf.is_linearized,
                "has_acroform": "/AcroForm" in pdf.Root,
                "attachment_count": len(pdf.attachments),
                "title": _info("/Title"),
                "author": _info("/Author"),
                "subject": _info("/Subject"),
                "keywords": _info("/Keywords"),
                "creator": _info("/Creator"),
                "producer": _info("/Producer"),
                "creation_date": _info("/CreationDate"),
                "modification_date": _info("/ModDate"),
            }
    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read document details: {str(e)}")


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


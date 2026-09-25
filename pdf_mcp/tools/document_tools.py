"""Tools for getting general information about a PDF document."""

from typing import Annotated, Optional, Sequence

import pymupdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError


def get_document_details(
    path: Annotated[str, Field(description="Path to the PDF file to read.")],
) -> dict:
    """Get general information about a PDF document, such as page count, version, and metadata."""
    try:
        with pymupdf.open(path) as pdf:
            docinfo = pdf.metadata
            def _info(key: str) -> Optional[str]:
                if docinfo is None or key not in docinfo:
                    return None
                return str(docinfo[key])
            return {
                "page_count": pdf.page_count,
                "is_encrypted": pdf.is_encrypted,
                "is_linearized": pdf.is_fast_webaccess,
                "has_acroform": pdf.is_form_pdf,
                "encryption": _info("encryption"),
                "format": _info("format"),
                "title": _info("title"),
                "author": _info("author"),
                "subject": _info("subject"),
                "keywords": _info("keywords"),
                "creator": _info("creator"),
                "producer": _info("producer"),
                "creation_date": _info("creationDate"),
                "modification_date": _info("modDate"),
            }
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to read form data from PDF: {str(e)}")

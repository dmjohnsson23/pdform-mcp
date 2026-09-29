import pymupdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError
from typing import Annotated, Union, Optional
from mcp.server.mcpserver import Image


def render(
    path: Annotated[str, Field(description='The PDF to read.')],
    page: Annotated[int, Field(description='The page number to render, indexed from 1.')],
    clip: Annotated[Optional[tuple[int,int,int,int]], Field(description='An optional area to clip rendering to.')]=None,
) -> Image:
    """
    Read one specific indirect object from the PDF by xref.

    The object will be returned in native PDF syntax.
    """
    try:
        with pymupdf.open(path) as pdf:
            if page < 1 or page > pdf.page_count:
                raise ToolError(f"Invalid page number {page} for {path} (out of range 1-{pdf.page_count})")
            image = pdf[page - 1].get_pixmap(clip=clip)
            return Image(data=image.tobytes('png'), format='png')
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to render PDF: {str(e)}")
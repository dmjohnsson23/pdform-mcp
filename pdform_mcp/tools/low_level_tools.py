import pymupdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError
from typing import Annotated, Union, Optional


def low_level_read_object(
    path: Annotated[str, Field(description='The PDF to read.')],
    xref: Annotated[Optional[int], Field(description='The xref of the object to read. Set to null to use the PDF root, or -1 for the trailer.')],
) -> str:
    """
    Read one specific indirect object from the PDF by xref.

    The object will be returned in native PDF syntax.
    """
    try:
        with pymupdf.open(path) as pdf:
            if xref is None:
                xref = pdf.pdf_catalog()
            return pdf.xref_object(xref)
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read object from PDF: {str(e)}")

    
def low_level_read_stream(
    path: Annotated[str, Field(description='The PDF to read.')],
    xref: Annotated[int, Field(description='The xref of the object to read from.')],
) -> Optional[bytes]:
    """
    Read the decompressed stream of one specific indirect object from the PDF by xref.
    """
    try:
        with pymupdf.open(path) as pdf:
            return pdf.xref_stream(xref)
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read stream from PDF: {str(e)}")

    
def low_level_read_object_value(
    path: Annotated[str, Field(description='The PDF to read.')],
    xref: Annotated[Optional[int], Field(description='The xref of the object to read from. Set to null to use the PDF root, or -1 for the trailer.')],
    key: Annotated[str, Field(description='The key for the value to get (without leading "/"). You may use a path-like notation ("/" separated) to access a value of a nested dictionary.',)],
) -> tuple[str,str]:
    """
    Read a value one specific indirect object from the PDF by xref and key.

    The value will be returned as `[type, value]` where `type` is a string indicating the detected PDF type, and `value` is a string containing the value in native PDF syntax.
    """
    try:
        with pymupdf.open(path) as pdf:
            if xref is None:
                xref = pdf.pdf_catalog()
            return pdf.xref_get_key(xref, key)
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read object value from PDF: {str(e)}")


def low_level_set_object_value(
    path: Annotated[str, Field(description='The PDF to read.')],
    xref: Annotated[Optional[int], Field(description='The xref of the object to write to. Set to null to use the PDF root, or -1 for the trailer.')],
    key: Annotated[str, Field(description='The key for the value to set (without leading "/"). You may use a path-like notation ("/" separated) to modify a value of a nested dictionary. Intermediate paths will be created.',)],
    value: Annotated[str, Field(description='The value to set, in native PDF syntax.')],
) -> str:
    """
    Set a value of one specific indirect object in the PDF by xref and key.
    """
    try:
        with pymupdf.open(path) as pdf:
            if xref is None:
                xref = pdf.pdf_catalog()
            pdf.xref_set_key(xref, key, value)
            return "Value set successfully"
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to write object value PDF: {str(e)}")


def low_level_smart_set_object_value(
    path: Annotated[str, Field(description='The PDF to read.')],
    xref: Annotated[Optional[int], Field(description='The xref of the object to write to. Set to null to use the PDF root, or -1 for the trailer.')],
    key: Annotated[str, Field(description='The key for the value to set (without leading "/"). You may use a path-like notation ("/" separated) to modify a value of a nested dictionary.',)],
    value: Annotated[Union[list,str,int,float,bool,None], Field(description='The value to set.')],
) -> str:
    """
    An alternative to `low_level_set_object_value` that converts to PDF syntax on your behalf, rather than requiring you to do so.

    This method cannot set names, xrefs, or dictionaries as values; only types which can be expressed as JSON primitives and arrays.
    """
    try:
        with pymupdf.open(path) as pdf:
            if xref is None:
                xref = pdf.pdf_catalog()
            pdf.xref_set_key(xref, key, _json_to_pdf(value))
            return "Value set successfully"
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to write object value PDF: {str(e)}")


def _json_to_pdf(value:Union[list,str,int,float,bool,None])->str:
    if isinstance(value, list):
        return f"[{' '.join([_json_to_pdf(item) for item in value])}]"
    if isinstance(value, str):
        return pymupdf.get_pdf_str(value)
    if value is None:
        return 'null'
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    return str(value)
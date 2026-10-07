import pymupdf
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError
from pdform_mcp.utils import open_pdf_rw
from pdform_mcp.utils.regex_helpers import regex_registry
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


def low_level_write_object(
    path: Annotated[str, Field(description='The PDF to modify.')],
    xref: Annotated[Optional[int], Field(description='The xref of the object to write to. Set to null to use the PDF root, or -1 for the trailer.')],
    object: Annotated[str, Field(description='The object dictionary value to write, in native PDF syntax.')],
) -> str:
    """
    Overwrite one specific indirect object in the PDF by xref.
    """
    try:
        with open_pdf_rw(path) as pdf:
            if xref is None:
                xref = pdf.pdf_catalog()
            pdf.update_object(xref, object)
        return "Value set successfully"
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to write object value PDF: {str(e)}")


def low_level_write_object_as_json(
    path: Annotated[str, Field(description='The PDF to modify.')],
    xref: Annotated[Optional[int], Field(description='The xref of the object to write to. Set to null to use the PDF root, or -1 for the trailer.')],
    object: Annotated[dict, Field(description='The object dictionary to write, in JSON syntax.')],
) -> str:
    """
    An alternative to `low_level_write_object` that converts to PDF syntax on your behalf, rather than requiring you to do so.

    * JSON objects translate to PDF dictionaries
    * JSON arrays translate to PDF arrays
    * Numbers, booleans, and `null` also directly translate to the PDF equivalent
    * Unicode string are represented as JSON strings beginning with "u:" followed by the remaining string content, which will be encoded in PDF format for you.
    * Binary strings are represented as JSON strings beginning with "b:" and followed by a string of hexadecimal digits.
    * PDF names are represented as JSON strings beginning with "/". If the string is not already a valid PDF name, special characters after the slash will be escaped.
    * Indirect object references are represented as JSON strings beginning with "xref:" followed by one or more digits representing the object xref.

    Example:

    ```json
    {
        "/Number": 123,
        "/Bool": true,
        "/Null": null,
        "/String": "u:This is some random unicode!",
        "/Binary": "b:DEADBEEF",
        "/Reference": "xref:123",
        "/Dictionary": {
            "/Array": [1, 2, 3, 4],
            "/Name": "/Yep"
        }
    }
    ```
    """
    try:
        with open_pdf_rw(path) as pdf:
            if xref is None:
                xref = pdf.pdf_catalog()
            pdf.update_object(xref, _json_to_pdf(object))
        return "Value set successfully"
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to write object value PDF: {str(e)}")


def low_level_set_object_value(
    path: Annotated[str, Field(description='The PDF to modify.')],
    xref: Annotated[Optional[int], Field(description='The xref of the object to write to. Set to null to use the PDF root, or -1 for the trailer.')],
    key: Annotated[str, Field(description='The key for the value to set (without leading "/"). You may use a path-like notation ("/" separated) to modify a value of a nested dictionary. Intermediate paths will be created.',)],
    value: Annotated[str, Field(description='The value to set, in native PDF syntax.')],
) -> str:
    """
    Set a value of one specific indirect object in the PDF by xref and key.
    """
    try:
        with open_pdf_rw(path) as pdf:
            if xref is None:
                xref = pdf.pdf_catalog()
            pdf.xref_set_key(xref, key, value)
        return "Value set successfully"
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to write object value PDF: {str(e)}")


def low_level_set_object_value_as_json(
    path: Annotated[str, Field(description='The PDF to modify.')],
    xref: Annotated[Optional[int], Field(description='The xref of the object to write to. Set to null to use the PDF root, or -1 for the trailer.')],
    key: Annotated[str, Field(description='The key for the value to set (without leading "/"). You may use a path-like notation ("/" separated) to modify a value of a nested dictionary.',)],
    value: Annotated[Union[dict,list,str,int,float,bool,None], Field(description='The value to set.')],
) -> str:
    """
    Variant of `low_level_set_object_value` that allows specifying the value in the same 
    convenient JSON format as `low_level_write_object_as_json`.
    """
    try:
        with open_pdf_rw(path) as pdf:
            if xref is None:
                xref = pdf.pdf_catalog()
            pdf.xref_set_key(xref, key, _json_to_pdf(value))
        return "Value set successfully"
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to write object value PDF: {str(e)}")


def low_level_create_indirect_object(
    path: Annotated[str, Field(description='The PDF to modify.')],
    value: Annotated[str, Field(description='The value to set, in PDF syntax.')] = '<<>>',
    stream: Annotated[Optional[bytes], Field(description='The raw bytes to set as the stream, if the new object should be stream..')] = None,
) -> str:
    """
    Create a new indirect object in the PDF, returning the new object's xref
    """
    try:
        with open_pdf_rw(path) as pdf:
            xref = pdf.get_new_xref()
            pdf.update_object(xref, value)
            if stream is not None:
                pdf.update_stream(xref, stream)
        return f"Indirect object created at xref {xref}"
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to write object value PDF: {str(e)}")


def low_level_create_indirect_object_as_json(
    path: Annotated[str, Field(description='The PDF to modify.')],
    object: Annotated[dict, Field(description='The object dictionary to write, in JSON syntax.')],
    stream: Annotated[Optional[bytes], Field(description='The raw bytes to set as the stream, if the new object should be stream..')] = None,
) -> str:
    """
    Variant of `low_level_create_indirect_object` that allows specifying the object in the same 
    convenient JSON format as `low_level_write_object_as_json`.
    """
    try:
        with open_pdf_rw(path) as pdf:
            xref = pdf.get_new_xref()
            pdf.update_object(xref, _json_to_pdf(object))
            if stream is not None:
                pdf.update_stream(xref, stream)
        return f"Indirect object created at xref {xref}"
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to write object value PDF: {str(e)}")


def low_level_write_stream(
    path: Annotated[str, Field(description='The PDF to modify.')],
    xref: Annotated[int, Field(description='The xref of the object to write to.')],
    stream: Annotated[bytes, Field(description='The raw bytes to set as the stream.')],
) -> str:
    """
    Write an object's stream by xref. This will overwrite any existing stream, or create a new
    stream if one does not exist on the specified object.

    The object must already exist; use `low_level_create_indirect_object` instead to create a new object.
    """
    try:
        with open_pdf_rw(path) as pdf:
            pdf.update_stream(xref, stream)
        return f"Stream written successfully to xref {xref}"
    except pymupdf.FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to write object value PDF: {str(e)}")


def _json_to_pdf(value:Union[dict,list,str,int,float,bool,None])->str:
    if isinstance(value, list):
        # PDF Array
        return f"[{' '.join([_json_to_pdf(item) for item in value])}]"
    if isinstance(value, dict):
        # PDF Dictionary
        return f"<<{'\n\t'.join(
            ' '.join((_json_to_pdf_name(k), _json_to_pdf(v)))
            for k, v in value.items()
        )}>>"
    if isinstance(value, str):
        if value.startswith('/'):
            # PDF name
            return _json_to_pdf_name(value)
        if value.startswith('u:'):
            # Unicode string
            return pymupdf.get_pdf_str(value[2:])
        if value.startswith('xref:') and value[5:].isdigit():
            # Xref
            return f"{value[5:].strip()} 0 R" # TODO generation number might not always be 0; how to get?
        if regex_registry[r'b:[0-9a-fA-F]*'].fullmatch(value):
            # Hexadecimal string
            return f"<{value[2:]}>"
        raise ValueError(f'Value cannot be converted to PDF syntax: {repr(value)}')
    # null, booleans, and numbers
    if value is None:
        return 'null'
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    return str(value)


def _json_to_pdf_name(value):
    if not (isinstance(value, str) and value.startswith('/')):
        raise ValueError(f"Not a PDF name: {repr(value)}")
    if regex_registry[r'(?:[^\x21-\x7E]|[()<>\[\]/%{}]|#(?![0-9a-zA-Z]{2}))'].search(value[1:]):
        # Contains illegal characters; fix
        return f'/{regex_registry[r'(?:[^\x21-\x7E]|[()<>\[\]/%{}#])'].sub(
            lambda m: ''.join(f'#{byte:02X}' for byte in m.group().encode('utf-8')),
            value[1:],
        )}'
    else:
        return value
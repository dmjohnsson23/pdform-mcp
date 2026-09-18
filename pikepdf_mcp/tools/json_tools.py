"""Tools for working with PDF JSON representations."""

from typing import Annotated, Literal
import json
from io import BytesIO, TextIOWrapper

from pikepdf import Pdf, JSONStreamData
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError


def describe_qpdf_json_format():
    """Get basic documentation and example data for the QPDF JSON format."""
    return """
    PDF objects are represented within the "qpdf" entry of a qpdf JSON file. The "qpdf" entry is a 
    two-element array. The first element is a dictionary containing header-like information about 
    the file such as the PDF version. The second element is a dictionary containing all the objects 
    in the PDF file. We refer to this as the objects dictionary.

    The first element contains the following keys:

    * jsonversion: this will always be 2.
    * pdfversion: the PDF version (e.g. "1.7", "2.0")
    * pushedinheritedpageresources: indicates QPDF pushed inherited resources down to the page level before converting to JSON.
    * calledgetallpages: indicates whether QPDF called getAllPages prior to writing the JSON output.
    * maxobjectid: the object ID of the highest numbered object in the file.

    You should avoid changing the values of this header dictionary.

    The second element is the objects dictionary. Each key in the objects dictionary is either 
    "trailer" or a string of the form "obj:O G R" where O and G are the object and generation 
    numbers and R is the literal string R. This is the PDF syntax for the indirect object reference 
    prepended by `obj:`. The value, representing the object itself, is a JSON object whose structure 
    is described below.

    Stream objects are represented as a JSON object with the single key "stream". The stream object
    has a key called "dict" whose value is the stream dictionary as an object value. The stream data
    itself data can optionally be included in the JSON in one of three ways:

    * none: Stream data is not represented; no other keys are present specified in stream dictionaries.
    * inline: The stream data appears as a base64-encoded string as the value of the "data" key.
    * file: The stream data is written to a file, and the path to the file is stored in the "datafile" key. A relative path is interpreted as relative to the current working directory.

    Non-stream objects are represented as a dictionary with the single key "value". Within the value property:

    * Objects of type Boolean or null are represented as JSON objects of the same type.
    * Objects that are numeric are represented as numeric in the JSON without regard to precision.
    * Name objects are represented as JSON strings that start with / and are followed by the PDF name in canonical form with all PDF syntax resolved.
    * Indirect object references are represented as JSON strings that look like a PDF indirect object reference and have the form "O G R" where O and G are the object and generation numbers and R is the literal string R.
    * PDF strings are represented as JSON strings in one of two ways:
      - "u:utf8-encoded-string": this format is used when the PDF string can be unambiguously represented as a Unicode string and contains no unprintable characters.
      - "b:hex-string": this format is used to represent any binary string value that can't be represented as a Unicode string.
    * PDF arrays are represented as JSON arrays of objects as described above.
    * PDF dictionaries are represented as JSON objects whose keys are the string representations of names and whose values are representations of PDF objects.

    An complete example of a QPDF JSON document using inline streams might look like this:

    ```json
    {
        "qpdf": [
            {
                "jsonversion": 2,
                "pdfversion": "1.3",
                "pushedinheritedpageresources": false,
                "calledgetallpages": false,
                "maxobjectid": 6
            },
            {
                "obj:1 0 R": {
                    "value": {
                        "/Pages": "3 0 R",
                        "/Type": "/Catalog"
                    }
                },
                "obj:2 0 R": {
                    "value": {
                        "/Author": "u:Digits of π",
                        "/CreationDate": "u:D:20220731155308-05'00'",
                        "/Creator": "u:A person typing in Emacs",
                        "/Keywords": "u:potato, example",
                        "/ModDate": "u:D:20220731155308-05'00'",
                        "/Producer": "u:qpdf",
                        "/Subject": "u:Example",
                        "/Title": "u:Something potato-related"
                    }
                },
                "obj:3 0 R": {
                    "value": {
                        "/Count": 1,
                        "/Kids": [
                            "4 0 R"
                        ],
                        "/Type": "/Pages"
                    }
                },
                "obj:4 0 R": {
                    "value": {
                        "/Contents": "5 0 R",
                        "/MediaBox": [
                            0,
                            0,
                            612,
                            792
                        ],
                        "/Parent": "3 0 R",
                        "/Resources": {
                            "/Font": {
                                "/F1": "6 0 R"
                            }
                        },
                        "/Type": "/Page"
                    }
                },
                "obj:5 0 R": {
                    "stream": {
                        "data": "eJxzCuFSUNB3M1QwMlEISQOyzY2AyEAhJAXI1gjIL0ksyddUCMnicg3hAgDLAQnI",
                        "dict": {
                            "/Filter": "/FlateDecode"
                        }
                    }
                },
                "obj:6 0 R": {
                    "value": {
                        "/BaseFont": "/Helvetica",
                        "/Encoding": "/WinAnsiEncoding",
                        "/Subtype": "/Type1",
                        "/Type": "/Font"
                    }
                },
                "trailer": {
                    "value": {
                        "/ID": [
                            "b:98b5a26966fba4d3a769b715b2558da6",
                            "b:6bea23330e0b9ff0ddb47b6757fb002e"
                        ],
                        "/Info": "2 0 R",
                        "/Root": "1 0 R",
                        "/Size": 7
                    }
                }
            }
        ]
    }
    ```
    """


def read_pdf_as_json(
    path: Annotated[str, Field(description='The PDF to read.')],
    include_stream_data: Annotated[
        Literal['none', 'inline', 'file'],
        Field(description="Indicates if stream data should be included in the PDF and, if so, the manner in which it will be included.")
    ] = 'none',
) -> dict:
    """
    Get a JSON representation of a PDF using the QPDF JSON format.
    """
    try:
        pdf = Pdf.open(path)
        stream = BytesIO()
        pdf.write_qpdf_json(stream, json_stream_data=getattr(JSONStreamData, include_stream_data))
        stream.seek(0)
        return json.load(stream)
    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read PDF as JSON: {str(e)}")

        
def read_pdf_object_as_json(
    path: Annotated[str, Field(description='The PDF to read.')],
    objgen: Annotated[tuple[int,int], Field(description='The objgen of the object to read.')],
) -> dict:
    """
    Get a JSON representation of a single indirect object from within a PDF using the QPDF JSON format.

    This returns only the JSON-format object dictionary of the object itself, such as would appear 
    under the "value" property in the complete JSON.
    """
    try:
        pdf = Pdf.open(path)
        object = pdf.get_object(objgen)
        return json.loads(object.to_json(True))
    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to read PDF as JSON: {str(e)}")


def write_pdf_from_json(
    path: Annotated[str, Field(description='The PDF to write.')],
    pdf_json: Annotated[dict, Field(description='A complete QPDF JSON representation of the PDF')],
) -> str:
    """
    Write a PDF using a JSON representation of the PDF, using the QPDF JSON format.

    This tool can be used to create new PDFs, or to fully re-write an existing PDF. The JSON must
    be a complete representation of a PDF.
    """
    try:
        stream = BytesIO()
        json.dump(pdf_json, TextIOWrapper(stream))
        stream.seek(0)
        pdf = Pdf.from_qpdf_json(stream)
        pdf.save(path)
        return f"Successfully wrote PDF to {path}"
    except Exception as e:
        raise ToolError(f"Failed to write PDF from JSON: {str(e)}")


def update_pdf_from_json(
    path: Annotated[str, Field(description='The PDF to update.')],
    pdf_json: Annotated[dict, Field(description='A partial QPDF JSON that will be overlaid on top of the existing structure.')],
) -> str:
    """
    Update an existing PDF using a partial JSON representation of the PDF, using the QPDF JSON format.

    This tool overlays the objects present in the JSON onto the open Pdf, leaving objects that the
    JSON does not mention unchanged.
    """
    try:
        stream = BytesIO()
        json.dump(pdf_json, TextIOWrapper(stream))
        stream.seek(0)
        pdf = Pdf.open(path)
        pdf.update_from_qpdf_json(stream)
        pdf.save(path)
        return f"Successfully updated PDF at {path}"
    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to update PDF from JSON: {str(e)}")

    
def update_pdf_object_from_json(
    path: Annotated[str, Field(description='The PDF to update.')],
    objgen: Annotated[tuple[int,int], Field(description='The objgen of the object to update.')],
    object_json: Annotated[dict, Field(description='A QPDF JSON-format object dictionary to update.')],
) -> str:
    """
    Update one specific object in an existing PDF.

    This tool functions similarly to `update_pdf_from_json`, but has the advantage of not requiring 
    the QPDF header dictionary or other boilerplate.
    """
    try:
        pdf = Pdf.open(path)
        stream = BytesIO()
        stream.seek(0)
        header_dict = json.load(stream)["qpdf"][0]
        objects_dict = {f"obj:{objgen[0]} {objgen[1]} R": {'value': object_json}}
        stream = BytesIO()
        json.dump({'qpdf':[header_dict, objects_dict]}, TextIOWrapper(stream))
        stream.seek(0)
        pdf.update_from_qpdf_json(stream)
        pdf.save(path)
        return f"Successfully updated PDF at {path}"
    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {path}")
    except Exception as e:
        raise ToolError(f"Failed to update PDF from JSON: {str(e)}")

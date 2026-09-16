from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pikepdf import Pdf, JSONStreamData, JobBuilder
from pydantic import BaseModel, Field
from io import BytesIO
import json
from typing import Literal, Sequence, Optional, Annotated

mcp = MCPServer("pikepdf")

@mcp.tool()
def describe_qpdf_json_format():
    """Get basic documentation and example data for the QPDF JSON format."""
    return """
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

@mcp.tool()
def read_pdf_as_json(
    path: Annotated[str, Field(description='The PDF to write.')], 
    include_stream_data: Annotated[Literal['none','inline','file'], Field(description="Indicates if stream data should be included in the PDF and, if so, the manner in which it will be included.")]='none',
    ) -> dict:
    """
    Get a JSON representation of a PDF using the QPDF JSON format.
    """
    pdf = Pdf.open(path)
    stream = BytesIO()
    pdf.write_qpdf_json(stream, json_stream_data=getattr(JSONStreamData, include_stream_data))
    stream.seek(0)
    return json.load(stream)


@mcp.tool()
def write_pdf_from_json(
    path: Annotated[str, Field(description='The PDF to write.')], 
    pdf_json: Annotated[dict, Field(description='A complete QPDF JSON representation of the PDF')],
    ):
    """
    Write a PDF using a JSON representation of the PDF, using the QPDF JSON format.

    This tool can be used to create new PDFs, or to fully re-write an existing PDF. The JSON must 
    be a complete representation of a PDF.
    """
    stream = BytesIO()
    json.dump(pdf_json, stream)
    stream.seek(0)
    pdf = Pdf.from_qpdf_json(stream)
    pdf.save(path)


@mcp.tool()
def update_pdf_from_json(
    path: Annotated[str, Field(description='The PDF to update.')], 
    pdf_json: Annotated[dict, Field(description='A partial QPDF JSON containing the updates to be made')],
    ):
    """
    Update an existing PDF using a partial JSON representation of the PDF, using the QPDF JSON format.
    
    This tool overlays the objects present in the JSON onto the open Pdf, leaving objects that the 
    JSON does not mention unchanged.
    """
    stream = BytesIO()
    json.dump(pdf_json, stream)
    stream.seek(0)
    pdf = Pdf.from_qpdf_json(stream)
    pdf.save(path)


def _input_output_helper(input_path:Optional[str], output_path:Optional[str]):
    job = JobBuilder()
    if input_path is not None:
        job.input(input_path)
    if output_path is None:
        job.replace_input()
    else:
        job.output(output_path)
    return job


class PageSpec(BaseModel):
    file: str = Field(default=".", description='The file path to take pages from. Use "." to take from the primary input PDF.')
    page_range: Optional[str] = Field(description="The page range to take, e.g. '1-5' or 'z-1' (reversed). Omit to use all pages.")

    
@mcp.tool()
def merge_or_extract_pages(
    input_path:Annotated[Optional[str], Field(description="The primary (default) source PDF to take pages from.")], 
    pages:Annotated[Sequence[PageSpec], Field(description="Pages to use to construct the output PDF.")], 
    output_path:Annotated[Optional[str], Field(description="The PDF to output to. Omit to overwrite the input PDF")]=None,
    ):
    """
    Take a subset of pages from one or more source PDFs and create a new PDF using those pages.

    Returns an exit code.
    """
    job = _input_output_helper(input_path, output_path)
    for page in pages:
        job.add_pages(page.file, page.page_range)
    return job.run().exit_code


@mcp.tool()
def validate_pdf(
    path: Annotated[str, Field(description='The PDF to check.')]
    )->Sequence[str]:
    """
    Check a PDF, returning a list of any identified issues.
    """
    pdf = Pdf.open(path)
    return pdf.check_pdf_syntax()
    




if __name__ == "__main__":
    mcp.run()
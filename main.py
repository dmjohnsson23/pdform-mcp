from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pikepdf import Pdf, JSONStreamData, JobBuilder
from pydantic import BaseModel, Field
from io import BytesIO, TextIOWrapper
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
    path: Annotated[str, Field(description='The PDF to read.')],
    include_stream_data: Annotated[Literal['none','inline','file'], Field(description="Indicates if stream data should be included in the PDF and, if so, the manner in which it will be included.")]='none',
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


@mcp.tool()
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


@mcp.tool()
def update_pdf_from_json(
    path: Annotated[str, Field(description='The PDF to update.')],
    pdf_json: Annotated[dict, Field(description='A partial QPDF JSON containing the updates to be made')],
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


def _parse_page_range(page_range: Optional[str], total_pages: int) -> list[int]:
    """
    Parse a QPDF-style page range string into a list of 0-indexed page numbers.

    Follows QPDF page range specification:
    - Plain numbers (1-indexed): "1" = first page, "5" = fifth page
    - r-prefix counts from end: "r1" = last page, "r2" = second-to-last
    - z = last page (same as r1)
    - Ranges with dash: "1-5" = pages 1-5, "5-1" = pages 5,4,3,2,1 (reversed)
    - Comma-separated: "1,3,5" = pages 1, 3, and 5
    - :odd/:even filters: "1-10:even" = even positions from range
    - x-prefix excludes: "1-10,x3-4" = pages 1,2,5,6,7,8,9,10

    Examples:
        "1-5" -> [0, 1, 2, 3, 4]
        "r3-r1" -> last three pages
        "z-1" -> all pages reversed
        "1-20:even" -> [1, 3, 5, 7, 9, 11, 13, 15, 17, 19] (even positions)
        "1-10,x3-4" -> [0, 1, 4, 5, 6, 7, 8, 9]
        "5,7-9,12:odd" -> [4, 7, 11] (odd positions from [5,7,8,9,12])
    """
    if page_range is None or page_range == "":
        return list(range(total_pages))

    # Check if there's a top-level filter (applies to entire expression)
    filter_type = None
    if ':' in page_range:
        # Check if the colon is part of a top-level filter
        # It's top-level if it appears after the last comma or if there are no commas
        last_colon_idx = page_range.rfind(':')
        last_comma_idx = page_range.rfind(',')

        # If colon comes after last comma, it's a top-level filter
        if last_colon_idx > last_comma_idx:
            main_part, filter_str = page_range.rsplit(':', 1)
            filter_str = filter_str.strip().lower()
            if filter_str in ('odd', 'even'):
                filter_type = filter_str
                page_range = main_part
            elif filter_str:  # Non-empty but invalid filter
                raise ValueError(f"Invalid filter: '{filter_str}'. Must be 'odd' or 'even'")

    def resolve_page_num(s: str) -> int:
        """Convert page reference to 1-indexed page number."""
        s = s.strip()
        if s == 'z':
            return total_pages
        elif s.startswith('r'):
            # r1 = last, r2 = second-to-last, etc.
            offset = int(s[1:])
            return total_pages - offset + 1
        else:
            return int(s)

    def parse_simple_part(part: str) -> list[int]:
        """Parse a single range part without filters."""
        part = part.strip()

        # Parse the range or single page
        if '-' in part:
            # Range like "1-5" or "r3-r1"
            start_str, end_str = part.split('-', 1)
            start = resolve_page_num(start_str)
            end = resolve_page_num(end_str)

            # Generate range (forward or backward)
            if start <= end:
                return list(range(start, end + 1))
            else:
                return list(range(start, end - 1, -1))
        else:
            # Single page
            page_num = resolve_page_num(part)
            return [page_num]

    # Split by commas and process each part
    parts = page_range.split(',')
    pages = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith('x'):
            # Exclusion range - remove these pages from the result
            exclusion_part = part[1:]
            exclusion_pages = parse_simple_part(exclusion_part)
            # Remove exclusion pages from our list
            for page in exclusion_pages:
                while page in pages:
                    pages.remove(page)
        else:
            # Regular range - add to result
            pages.extend(parse_simple_part(part))

    # Apply top-level :odd or :even filter if present
    if filter_type:
        # Note: odd/even refers to POSITIONS (1-indexed), not page numbers
        if filter_type == 'odd':
            pages = [pages[i] for i in range(0, len(pages), 2)]
        else:  # even
            pages = [pages[i] for i in range(1, len(pages), 2)]

    # Validate and convert to 0-indexed
    result = []
    for page in pages:
        if page < 1 or page > total_pages:
            raise ValueError(f"Page {page} out of range (1-{total_pages})")
        result.append(page - 1)

    return result


@mcp.tool()
def extract_pages_from_pdf(
    input_path: Annotated[str, Field(description="Path to the source PDF file.")],
    page_range: Annotated[Optional[str], Field(description="QPDF page range: '1-5' (range), '1,3,5' (specific), 'z' (last), 'r1' (last), 'r2' (second-to-last), '7-3' (reversed), '1-20:even' (even positions), '1-10,x3-4' (exclude 3-4). Omit for all pages.")]=None,
    output_path: Annotated[Optional[str], Field(description="Path for the output PDF. If omitted, overwrites the input file.")]=None,
) -> str:
    """
    Extract specific pages from a PDF file and create a new PDF with only those pages.

    Uses QPDF page range syntax:
    - Numbers are 1-indexed: '1' = first page, '5' = fifth page
    - 'z' = last page, 'r1' = last page, 'r2' = second-to-last, etc.
    - Ranges: '1-5' = pages 1-5, '5-1' = pages 5,4,3,2,1 (reversed)
    - Comma-separated: '1,3,5,7-9' = pages 1, 3, 5, 7, 8, 9
    - Filters: '1-20:even' = even positions, '1-20:odd' = odd positions
    - Exclusions: '1-10,x3-4' = pages 1,2,5,6,7,8,9,10 (excludes 3-4)
    """
    try:
        # Open source PDF
        with Pdf.open(input_path) as src_pdf:
            total_pages = len(src_pdf.pages)

            # Parse page range
            page_indices = _parse_page_range(page_range, total_pages)

            # Validate page indices
            invalid_pages = [i for i in page_indices if i < 0 or i >= total_pages]
            if invalid_pages:
                raise ToolError(f"Invalid page indices (out of range 1-{total_pages}): {[i+1 for i in invalid_pages]}")

            # Create new PDF with selected pages
            dst_pdf = Pdf.new()
            for page_idx in page_indices:
                dst_pdf.pages.append(src_pdf.pages[page_idx])

            # Save to output
            output = output_path if output_path else input_path
            dst_pdf.save(output)

            return f"Successfully extracted {len(page_indices)} page(s) from {input_path} to {output}"

    except FileNotFoundError:
        raise ToolError(f"PDF file not found: {input_path}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to extract pages: {str(e)}")


class PageSource(BaseModel):
    file: str = Field(description="Path to the PDF file to take pages from.")
    page_range: Optional[str] = Field(default=None, description="QPDF page range: '1-5', '1,3,5', 'z' (last), 'r1-r3' (last 3), '7-3' (reversed), '1-20:even', '1-10,x3-4'. Omit for all pages.")


@mcp.tool()
def merge_pdfs(
    sources: Annotated[Sequence[PageSource], Field(description="List of PDF sources with optional QPDF page ranges to merge.")],
    output_path: Annotated[str, Field(description="Path for the merged output PDF.")],
) -> str:
    """
    Merge pages from multiple PDF files into a single PDF.

    Pages are combined in the order specified. Each source can specify a QPDF-style page range.
    See extract_pages_from_pdf documentation for complete page range syntax.
    """
    try:
        # Create new PDF for the merged result
        merged_pdf = Pdf.new()
        total_pages_added = 0

        for source in sources:
            # Open source PDF
            with Pdf.open(source.file) as src_pdf:
                total_pages = len(src_pdf.pages)

                # Parse page range
                page_indices = _parse_page_range(source.page_range, total_pages)

                # Validate page indices
                invalid_pages = [i for i in page_indices if i < 0 or i >= total_pages]
                if invalid_pages:
                    raise ToolError(
                        f"Invalid page indices in {source.file} (out of range 1-{total_pages}): "
                        f"{[i+1 for i in invalid_pages]}"
                    )

                # Add pages to merged PDF
                for page_idx in page_indices:
                    merged_pdf.pages.append(src_pdf.pages[page_idx])

                total_pages_added += len(page_indices)

        # Save merged PDF
        merged_pdf.save(output_path)

        return f"Successfully merged {len(sources)} PDF(s) ({total_pages_added} total pages) into {output_path}"

    except FileNotFoundError as e:
        raise ToolError(f"PDF file not found: {str(e)}")
    except ValueError as e:
        raise ToolError(f"Invalid page range format: {str(e)}")
    except Exception as e:
        raise ToolError(f"Failed to merge PDFs: {str(e)}")


@mcp.tool()
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
    




if __name__ == "__main__":
    mcp.run()
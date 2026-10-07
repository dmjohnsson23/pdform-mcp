from contextlib import contextmanager
from typing import Optional, Generator
import pymupdf

@contextmanager
def open_pdf_rw(input_path:str, output_path:Optional[str]=None)->Generator[pymupdf.Document, None, None]:
    """
    Opens a PDF in PyMuPdf for editing. Saves the PDF on closing the context manager.
    """
    with pymupdf.open(input_path) as src_pdf:
        yield src_pdf
        data = src_pdf.tobytes()
    output = output_path if output_path else input_path
    with open(output, "wb") as f:
        f.write(data)
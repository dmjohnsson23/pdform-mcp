# PDForm MCP

This is an MCP server intended to enable LLMs to work with PDFs on a deep level. This has a focus on enabling LLMs to understand form-fillable PDFs (hence the name) but is not necessarily limited to that capacity.

Uses [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/index.html) under the hood for all operations.

Current capabilities:

* List and describe acroform fields
* Read document metadata
* Read and write low-level PDF dictionaries
* Merge PDFs
* Extract pages from PDFs
* Read page metadata
* Screenshot the PDF (for visual inspection by multi-modal models)
* Understand the layout of the PDF (text, images, drawings, etc...)
* Extract text from the PDF
* Locate text (such as input labels) on the page

## Installation

### Using `pipx` (Recommended for Linux)

Dependencies: [pipx](https://pipx.pypa.io/latest/how-to/install-pipx.html)

This option runs the MCP server in a virtual environment rather than installing directly to your system Python environment, avoiding potential dependency clashes with other software you may have installed.

```shell
claude mcp add pdform-mcp -- pipx run pdform-mcp
```

or

```shell
pipx install pdform-mcp
claude mcp add pdform-mcp -- pdform-mcp
```

The first option downloads and runs the MCP in an ephemeral virtual environment without installing, the second downloads and installs the tool to a dedicated permanent virtual environment.

### Using plain `pip` (Recommended for Windows)

Dependencies: [Python 3.12+](https://www.python.org/)

This method is potentially unsafe, as it installs directly to your system Python environment, but this is less of a problem on Windows as most Windows software does not rely on Python. This method will not at work at all on some Linux distributions which forbid installation of packages to the system Python environment (e.g. Ubuntu).

```shell
pip install pdform-mcp
claude mcp add pdform-mcp -- pdform-mcp
```

Note: If you are on Windows, for this to work you will have to set up your PATH so that `pip` and any tools it installs are visible to your shell. 
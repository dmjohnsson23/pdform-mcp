"""PDF MCP server - PDF manipulation tools for Claude."""

from pdform_mcp.server import mcp

__all__ = ["mcp", "main"]


def main() -> None:
    mcp.run()

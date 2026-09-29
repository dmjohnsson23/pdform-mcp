from pdform_mcp import mcp

# Note: This file used for development runs to get MCP inspector. Run:
# uv run mcp dev main.py
# This is not used in actual deployments, see pdform_mcp/__main__.py for real entrypoint.

if __name__ == "__main__":
    mcp.run()
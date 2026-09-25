#!/bin/bash
cd "$(dirname "$0")"
exec uv run python -m pikepdf_mcp

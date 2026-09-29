#!/bin/bash
cd "$(dirname "$0")"
exec uv run python -m pdform_mcp

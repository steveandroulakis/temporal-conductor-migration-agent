#!/bin/bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required (https://github.com/astral-sh/uv)" >&2
  exit 1
fi

uv venv
uv sync --all-extras
uv pip list | grep -E "(temporalio|mypy)"

python3 -m py_compile schema_approval/*.py

cat <<'INSTRUCTIONS'

Environment ready.

Next steps:
1. Start the Temporal worker: uv run worker
2. Start the workflow execution: uv run starter
3. Monitor progress in Temporal Web UI: http://localhost:8233

INSTRUCTIONS

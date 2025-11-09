# Schema Approval – Temporal Migration

Migrated from Conductor workflow: `conductor-definition/EXAMPLE_review_approval.json`

This repository now contains a complete Temporal Python SDK project that models the
multi-stage schema review process originally defined in Netflix Conductor. The new
implementation follows the migration process documented in `conductor-migration/`
and preserves the original control flow: looping until approval, parallel primary
reviews, conditional secondary and tertiary reviews, and final completion tasks.

## Overview

The `SchemaApprovalWorkflow` orchestrates the following steps:

1. Upload the proposed schema revision.
2. Run the Review1.a and Review1.b activities in parallel.
3. If both reviewers approve, collect a secondary approval (Review2) that may skip
   the tertiary review.
4. Optionally execute a tertiary review (Review3).
5. Complete the review and exit the loop when all reviewers approve. Otherwise the
   workflow repeats until the configured approval threshold is met.

All activities are implemented in `schema_approval/activities.py`. The workflow logic
resides in `schema_approval/workflow.py`, while `schema_approval/worker.py` hosts the
worker process and `schema_approval/starter.py` demonstrates how to start a workflow
execution with sample data.

## Prerequisites

- Python 3.11+
- [Temporal CLI](https://docs.temporal.io/dev-guide/python/hello-world/#run-the-temporal-server)
  or Temporal Server running locally at `localhost:7233`
- [uv](https://github.com/astral-sh/uv) package manager (required by `AGENTS.md`)

Verify tooling:

```bash
uv --version
python3 --version
```

## Setup

The provided setup script installs dependencies and prepares console entry points.

```bash
./setup.sh
```

The script will:

1. Create a virtual environment managed by `uv`.
2. Install runtime and development dependencies (`temporalio`, `mypy`).
3. Print next steps for starting the worker and workflow starter.

## Running the Workflow

1. **Start the worker** (in a dedicated terminal):
   ```bash
   uv run worker
   ```

2. **Execute the workflow** (in a separate terminal):
   ```bash
   uv run starter
   ```

3. **Observe results** in the terminal output and via the Temporal Web UI:
   - http://localhost:8233/namespaces/default/workflows

The starter submits an `inventory-schema` document and requires two successful
iterations before the workflow can complete. Adjust the sample input in
`schema_approval/starter.py` as needed for experimentation.

## Configuration

- **Task Queue**: `schema-approval-task-queue` (defined in `schema_approval/workflow.py`).
- **Console Scripts**: Configured in `pyproject.toml` so `uv run worker` and
  `uv run starter` work after `uv sync` or `./setup.sh`.
- **Environment Variables**: Not required. Update connection details in
  `worker.py` and `starter.py` if your Temporal service runs elsewhere.

## Project Structure

```
schema_approval/
  __init__.py
  activities.py
  shared.py
  starter.py
  worker.py
  workflow.py
conductor-analysis.json
CONDUCTOR_COMPARISON.md
CONDUCTOR_MIGRATION_NOTES.md
setup.sh
pyproject.toml
README.md
```

## Migration Notes

- `CONDUCTOR_COMPARISON.md` documents the Conductor-to-Temporal mapping for each
  task, including the DO_WHILE loop, fork/join, and nested switches.
- `CONDUCTOR_MIGRATION_NOTES.md` records assumptions and behavioral adjustments
  taken during the migration.
- `conductor-analysis.json` captures the structured analysis from Phase 1 of the
  migration guide.

## Troubleshooting

- Ensure the Temporal service is reachable at `localhost:7233` before starting
  the worker or starter.
- Verify dependencies are installed with `uv pip list | grep temporalio`.
- Re-run `./setup.sh` if console scripts stop working after dependency changes.
- Use `python3 -m py_compile schema_approval/*.py` to confirm Python syntax is valid.

## Additional Resources

- Migration process documentation: `conductor-migration/README.md`
- Temporal Python SDK samples: https://github.com/temporalio/samples-python
- Conductor primitives reference: `conductor-migration/conductor-primitives-reference.md`

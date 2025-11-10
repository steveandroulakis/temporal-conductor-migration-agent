# Schema Approval Temporal Workflow

This project contains a Temporal Python implementation of the `schema_approval` workflow
originally defined with Netflix Conductor. The code follows the migration
requirements documented in [`conductor-migration/`](./conductor-migration/) and
recreates the same control flow, including the human approval loop, using the
Temporal Python SDK.

## Overview

* **Workflow goal** – manage iterative review of a schema definition until it is
  approved.
* **Key features** – `DO_WHILE` approval loop, parallel reviewer notifications,
  conditional escalation, and human-in-the-loop decisions delivered via Temporal
  workflow updates.
* **Temporal task queue** – `schema-approval-task-queue`.

## Project Layout

```
schema_approval/
  __init__.py
  activities.py
  shared.py
  starter.py
  worker.py
  workflow.py
pyproject.toml
README.md
```

* `shared.py` – dataclasses shared by workflows, activities, workers, and clients.
* `activities.py` – upload, notification, auditing, and completion activities.
* `workflow.py` – the Temporal workflow implementation with update and query handlers.
* `worker.py` – worker entry point registered as a console script (`uv run worker`).
* `starter.py` – helper script that starts the workflow and drives review updates.

## Mapping from Conductor to Temporal

| Conductor primitive | Temporal translation |
| ------------------- | -------------------- |
| `DO_WHILE` loop | `while` loop in workflow with iteration counter |
| `SIMPLE` tasks (`upload_schema`, `ReviewX`, `CompleteReview`) | Activities (`upload_schema`, `notify_reviewer`, `record_decision`, `complete_review`) |
| `FORK_JOIN` (`Review1.a` / `Review1.b`) | `asyncio.gather` awaiting multiple `_await_decision` coroutines |
| `JOIN` (`notification_join`) | implicit in `asyncio.gather` waiting for both reviewers |
| `SWITCH` tasks (`Review1Check`, `Review2Check`, `Review3Check`) | `if` / `else` branches based on collected `ReviewDecision` values |
| Human approval inputs (`${user_action.output.approved}`) | Workflow update handler `submit_review_decision` that validates and records reviewer updates |

## Prerequisites

* Python **3.11+**
* [uv](https://docs.astral.sh/uv/) package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
* Temporal server running at `localhost:7233` (for local testing you can use
  [Temporalite](https://docs.temporal.io/temporalite)).

## Installation

```bash
uv sync
```

This command installs the project as a package, exposes the console scripts, and
fetches the Temporal Python SDK dependency.

## Running the Sample

1. **Start the Temporal worker**
   ```bash
   uv run worker
   ```

2. **Run one of the starter scenarios**
   ```bash
   uv run starter --scenario single-pass
   ```

   The starter creates a workflow run and supplies human review decisions through
   the `submit_review_decision` update. Available scenarios:

   * `single-pass` – all reviewers approve during the first iteration.
   * `escalation` – first iteration fails (no final approval), second iteration
     escalates to the executive reviewer before approval is granted.

The starter prints the `SchemaApprovalResult` returned by the workflow, including
how many iterations were required and the decision summaries.

## Interacting Manually

The workflow exposes:

* **Update** – `submit_review_decision(ReviewDecision)` records a reviewer’s decision
  and immediately validates that a matching review task is pending.
* **Queries** – `pending_reviews()` returns currently waiting review IDs,
  `iteration()` reports the current iteration number.

To submit decisions manually (for example from a Python REPL):

```python
import asyncio
from temporalio.client import Client
from schema_approval.shared import ReviewDecision

async def main() -> None:
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id="<your-workflow-id>")
    await handle.execute_update(
        "submit_review_decision",
        ReviewDecision(review_id="review1.a:iter-1", approved=True),
    )

asyncio.run(main())
```

## Validation and Quality Checks

* **Syntax** – `python -m py_compile schema_approval/*.py`
* **Type checking** – `uv run mypy schema_approval/`
* **Linting** – `uv run ruff check schema_approval/`

These commands ensure the migrated workflow matches the quality criteria defined
in `conductor-migration/conductor-quality-assurance.md`.

## Troubleshooting

* If the worker fails with a sandbox error, verify that `workflow.py` imports
  activities by symbol (`from .activities import ...`) instead of importing the
  entire module.
* Update submissions must reference pending review IDs. Use the `pending_reviews`
  query to list active review tasks when scripting manual approval flows.

For additional guidance consult:

* [`conductor-migration/conductor-primitives-reference.md`](./conductor-migration/conductor-primitives-reference.md)
* [`conductor-migration/conductor-human-interaction.md`](./conductor-migration/conductor-human-interaction.md)
* [`conductor-migration/conductor-troubleshooting.md`](./conductor-migration/conductor-troubleshooting.md)

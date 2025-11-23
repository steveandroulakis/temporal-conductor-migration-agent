# Schema Approval - Temporal Migration

Migrated from Netflix Conductor workflow definition to Temporal Python SDK.

**Original Conductor Workflow**: `conductor-definition/EXAMPLE_review_approval.json`
**Migration Date**: 2025-11-23
**Complexity**: high (Max nesting depth: 5)

## Overview

This project implements the **schema_approval** workflow using Temporal's Python SDK. The workflow was automatically migrated from a Conductor JSON definition.

### Workflow Description

Schema approval workflow with multi-stage review process. This workflow orchestrates a sophisticated approval process with multiple review stages, parallel execution, and human decision points. The workflow repeats until final approval is granted, implementing a retry-until-approved pattern.

### Control Flow

This workflow implements:
- 1 DO_WHILE loop (repeat until approved)
- 1 parallel execution block (FORK_JOIN) with 2 branches
- 3 conditional branches (SWITCH tasks for approval gates)
- Human interaction with 3 approval points
- Maximum nesting depth of 5 levels

**Control Flow Structure**:
```
DO_WHILE (repeat until approved)
  ├─ upload_schema (SIMPLE)
  ├─ FORK_JOIN (parallel execution)
  │   ├─ Review1.a (SIMPLE)
  │   └─ Review1.b (SIMPLE)
  ├─ SWITCH Review1Check (human approval #1)
  │   ├─ YES → Review2 (SIMPLE)
  │   │   └─ SWITCH Review2Check (human approval #2)
  │   │       ├─ YES → CompleteReview (skip Review3 path)
  │   │       └─ NO → Review3 (SIMPLE)
  │   │           └─ SWITCH Review3Check (human approval #3)
  │   │               ├─ YES → CompleteReview (full review path)
  │   │               └─ NO → Continue loop
  │   └─ NO → Continue loop
```

## Prerequisites

### Required Software

1. **Python 3.11+**
   ```bash
   python3 --version  # Should show 3.11 or higher
   ```

2. **UV Package Manager**
   ```bash
   # macOS
   brew install uv

   # Linux/macOS (curl)
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Temporal CLI and Dev Server**
   ```bash
   # macOS
   brew install temporal

   # Linux/Windows: Download from https://temporal.io/download
   ```

### Temporal Server

Start the Temporal dev server:
```bash
temporal server start-dev
```

The dev server provides:
- Temporal server (localhost:7233)
- Web UI (http://localhost:8233)
- In-memory persistence

## Quick Start

### 1. Install Dependencies

Run the automated setup script:
```bash
chmod +x setup.sh  # Make executable
./setup.sh
```

Or manually:
```bash
uv venv
uv add temporalio
uv add --dev mypy ruff
uv sync --all-extras
```

### 2. Start the Worker

In a terminal window:
```bash
uv run worker
```

You should see:
```
Worker ready — polling task queue: schema-approval-task-queue
```

Keep this terminal running.

### 3. Execute the Workflow

In a new terminal window:
```bash
uv run starter
```

The starter will:
- Connect to Temporal
- Start the workflow with example input
- Display the workflow URL
- Wait for completion (requires human approvals)
- Show the result

### 4. Monitor in Web UI

Open the workflow in your browser:
```
http://localhost:8233
```

Navigate to your workflow to see:
- Workflow execution history
- Activity results
- Current status
- Pending human interactions

## Project Structure

```
schema_approval_temporal/
├── schema_approval_temporal/      # Main package directory
│   ├── __init__.py               # Package marker
│   ├── shared.py                 # Data models (dataclasses)
│   ├── activities.py             # Activity implementations
│   ├── workflow.py               # Workflow definition
│   ├── worker.py                 # Worker registration
│   └── starter.py                # Workflow starter
├── pyproject.toml                # Project configuration
├── setup.sh                      # Automated setup script
├── README.md                     # This file
├── CONDUCTOR_COMPARISON.md       # Conductor vs Temporal mapping
├── CONDUCTOR_MIGRATION_NOTES.md  # Migration decisions
└── VALIDATION_REPORT.md          # Code validation results
```

### Module Overview

- **shared.py**: Dataclass definitions for workflow inputs, outputs, and activity data
- **activities.py**: 7 activities implementing business logic (upload, reviews, completion)
- **workflow.py**: Workflow orchestration with complex control flow (5-level nesting)
- **worker.py**: Worker process that executes workflows and activities
- **starter.py**: Client for starting workflow executions

## Human Interaction

This workflow includes human interaction points for approvals at three stages:

### Review1 Approval (After Parallel Reviews)
- **Type**: Approval gate after Review1.a and Review1.b complete in parallel
- **Mechanism**: Workflow Update (`submit_review1_approval`)
- **Decision**: YES (proceed to Review2) or NO (restart loop)

To send Review1 approval:
```python
from temporalio.client import Client
from schema_approval_temporal.shared import ApprovalDecision

client = await Client.connect("localhost:7233")
handle = client.get_workflow_handle_for(
    SchemaApprovalWorkflow.run,
    workflow_id="your-workflow-id"
)

# Send approval decision
await handle.execute_update(
    "submit_review1_approval",
    ApprovalDecision(
        reviewer_id="reviewer-1a",
        approved=True,
        decision="YES",
        stage="Review1Check",
        comments="Both Review1.a and Review1.b passed"
    )
)
```

### Review2 Approval (Skip Review3 Decision)
- **Type**: Approval gate deciding whether Review3 is needed
- **Mechanism**: Workflow Update (`submit_review2_approval`)
- **Decision**: YES (skip Review3, complete) or NO (proceed to Review3)

To send Review2 approval:
```python
await handle.execute_update(
    "submit_review2_approval",
    ApprovalDecision(
        reviewer_id="reviewer-2",
        approved=True,
        decision="YES",  # or "NO" to require Review3
        stage="Review2Check",
        skip_review3=True,  # Expedited approval path
        comments="Review2 passed - no need for Review3"
    )
)
```

### Review3 Approval (Final Approval)
- **Type**: Final approval gate after Review3 completes
- **Mechanism**: Workflow Update (`submit_review3_approval`)
- **Decision**: YES (final approval) or NO (restart loop)

To send Review3 approval:
```python
await handle.execute_update(
    "submit_review3_approval",
    ApprovalDecision(
        reviewer_id="reviewer-3",
        approved=True,
        decision="YES",
        stage="Review3Check",
        comments="Final review complete - approved"
    )
)
```

### Query Approval Status

You can query the current approval status without modifying the workflow:

```python
status = await handle.query("get_approval_status")
print(f"Current status: {status}")
# Returns: {
#   "status": "awaiting_review1_approval",
#   "iteration": 1,
#   "current_stage": "awaiting_review1_approval",
#   "approved": False,
#   "review1_decision": None,
#   "review2_decision": None,
#   "review3_decision": None
# }
```

## Configuration

### Workflow Timeouts

The workflow has the following timeout configuration:
- **Execution timeout**: 24 hours (configurable in starter.py)
- **Activity timeouts**:
  - upload_schema: 30 seconds
  - review_1a, review_1b: 20 seconds each
  - review_2, review_3: 30 seconds each
  - complete_review (both paths): 20 seconds
- **Approval wait timeouts**: 24 hours per approval gate

To adjust timeouts, edit the timeout parameters in `schema_approval_temporal/workflow.py`:
```python
start_to_close_timeout=timedelta(seconds=30)  # Modify as needed
```

Or adjust approval wait times:
```python
await workflow.wait_condition(
    lambda: self._review1_approval is not None,
    timeout=timedelta(hours=24),  # Modify as needed
)
```

### Task Queue

The worker and starter use task queue: **schema-approval-task-queue**

To change the task queue:
1. Update `worker.py`: `task_queue="new-queue-name"`
2. Update `starter.py`: `task_queue="new-queue-name"`

### Workflow Input

To customize workflow input, edit `schema_approval_temporal/starter.py`:
```python
workflow_input = WorkflowInput(
    schema_id="example-schema-001",
    schema_content={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        }
    },
    submitter_id="user-123",
    priority=1,
    metadata={
        "department": "engineering",
        "project": "data-platform"
    }
)
```

### Max Loop Iterations

The workflow has a maximum iteration limit to prevent infinite loops:
```python
max_iterations = 10  # In workflow.py
```

To change this limit, edit the `max_iterations` variable in `schema_approval_temporal/workflow.py`.

## Troubleshooting

### Worker Won't Start

**Error**: `Cannot connect to Temporal server`

**Solution**: Ensure Temporal dev server is running:
```bash
temporal server start-dev
```

---

**Error**: `No module named 'temporalio'`

**Solution**: Install dependencies:
```bash
uv sync --all-extras
```

---

**Error**: `console script not found: worker`

**Solution**: Ensure `[tool.uv]` section with `package = true` is in `pyproject.toml`, then:
```bash
uv sync --all-extras
```

### Workflow Fails to Start

**Error**: `Activity upload_schema not found`

**Solution**: Ensure worker is running before starting workflow.

---

**Error**: `Workflow execution timeout`

**Solution**: Increase timeout in starter.py:
```python
execution_timeout=timedelta(hours=48)  # Increase as needed
```

---

**Error**: `Approval timeout on iteration X`

**Solution**: The workflow timed out waiting for human approval (default 24 hours). Submit the required approval via Update, or increase the timeout in workflow.py:
```python
await workflow.wait_condition(
    lambda: self._review1_approval is not None,
    timeout=timedelta(hours=48),  # Increase as needed
)
```

### Approval Submission Issues

**Error**: `Review1 approval already submitted`

**Solution**: Each approval can only be submitted once per iteration. If the workflow loops, approvals are reset for the next iteration.

---

**Error**: `Unauthorized reviewer: user-xyz`

**Solution**: Update the authorized reviewers list in `workflow.py`:
```python
self._authorized_reviewers = {
    "reviewer-1a",
    "reviewer-1b",
    "reviewer-2",
    "reviewer-3",
    "user-xyz",  # Add new reviewer
}
```

### Type Checking Issues

To run type checking:
```bash
mypy schema_approval_temporal --strict --ignore-missing-imports
```

If errors occur, see `VALIDATION_REPORT.md` for guidance.

## Development

### Running Tests

Tests can be added in a `tests/` directory using pytest:
```bash
uv add --dev pytest
pytest tests/
```

### Code Quality

This project follows strict Python standards:
- **Type hints**: All functions have complete type annotations (mypy --strict)
- **Docstrings**: Comprehensive documentation for all public APIs
- **Code style**: PEP 8 compliant

Run linting:
```bash
uv add --dev ruff
ruff check schema_approval_temporal/
```

### Customizing Activity Implementations

All activities in `activities.py` contain placeholder implementations marked with TODO comments. Replace these with actual business logic:

```python
# TODO: Implement actual schema upload logic
# Replace with your upload logic:
# - Validate schema content
# - Store schema in repository/database
# - Generate upload ID
# - Track iteration for audit trail
```

## Migration Notes

This project was automatically migrated from Conductor. See:
- **CONDUCTOR_COMPARISON.md** - Side-by-side Conductor vs Temporal examples
- **CONDUCTOR_MIGRATION_NOTES.md** - Migration decisions and recommendations

### Key Differences from Conductor

- **Control Flow**: Conductor JSON primitives (DO_WHILE, FORK_JOIN, SWITCH) translated to Python (while loop, asyncio.gather, if/elif)
- **Data Passing**: Conductor expressions `${workflow.variables.approved}` → Python `self._approved`
- **Human Interaction**: Conductor SWITCH tasks with `${user_action.output.approved}` → Temporal Updates with validation
- **Error Handling**: Conductor retry configs → Temporal RetryPolicy objects
- **Activities**: Conductor SIMPLE tasks → Temporal @activity.defn functions
- **Loop Exit**: Conductor workflow variable `approved` → Temporal instance variable `self._approved`

### Complexity Highlights

This workflow is classified as **high complexity** due to:
- 5-level nesting depth (deepest in CompleteReview_2)
- DO_WHILE loop with potential for many iterations
- 3 separate human approval gates
- Parallel execution combined with nested conditionals
- Complex approval flow with multiple exit paths

## Additional Resources

- [Temporal Python SDK Documentation](https://docs.temporal.io/develop/python)
- [Temporal Python SDK API Reference](https://python.temporal.io/)
- [Temporal Learning Portal](https://learn.temporal.io/)
- [Conductor to Temporal Migration Guide](./conductor-migration/)

## Support

For migration-specific questions:
- Review `CONDUCTOR_MIGRATION_NOTES.md` for decisions made during migration
- Check `VALIDATION_REPORT.md` for code quality notes
- Consult the Conductor migration documentation in `conductor-migration/`

---

**Generated by Conductor to Temporal Migration Tool**
**Migration Date**: 2025-11-23

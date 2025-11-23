# Schema Approval Workflow - Temporal Migration

Migrated from Netflix Conductor workflow definition to Temporal Python SDK.

**Original Conductor Workflow**: `conductor-definition/EXAMPLE_review_approval.json`
**Migration Date**: November 23, 2025
**Complexity**: HIGH (Max nesting depth: 5)

## Overview

This project implements the **schema_approval** workflow using Temporal's Python SDK. The workflow was automatically migrated from a Conductor JSON definition.

### Workflow Description

Multi-stage schema approval workflow with human review checkpoints. This workflow implements a DO_WHILE loop containing a complex approval process with parallel reviews, nested conditional checks, and multiple human interaction points. The workflow repeats until final approval is achieved.

### Control Flow

This workflow implements:
- **1 DO_WHILE loop** containing entire approval process (max 10 iterations)
- **1 parallel execution block** (FORK_JOIN with 2 branches: Review1.a, Review1.b)
- **3 conditional branches** (SWITCH tasks: Review1Check, Review2Check, Review3Check)
- **3 human interaction points** (approval decisions via workflow Updates)
- **Maximum nesting depth**: 5 levels (CompleteReview_2 task)

The approval process has three stages:
1. **Review1**: Two parallel reviews (Review1.a and Review1.b)
2. **Review2**: Second-stage review (conditional on Review1 approval)
3. **Review3**: Final-stage review (conditional on Review2 decision)

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
- Wait for completion
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
temporal-conductor-migration-agent/
├── schema_approval_temporal/          # Main package directory
│   ├── __init__.py                    # Package marker
│   ├── shared.py                      # Data models (dataclasses)
│   ├── activities.py                  # Activity implementations
│   ├── workflow.py                    # Workflow definition
│   ├── worker.py                      # Worker registration
│   ├── starter.py                     # Workflow starter
│   └── interact.py                    # Workflow interaction client (Updates/Queries)
├── conductor-definition/              # Original Conductor workflow
│   └── EXAMPLE_review_approval.json
├── pyproject.toml                     # Project configuration
├── setup.sh                           # Automated setup script
├── PROJECT_README.md                  # This file
├── CONDUCTOR_COMPARISON.md            # Conductor vs Temporal mapping
├── CONDUCTOR_MIGRATION_NOTES.md       # Migration decisions
├── VALIDATION_REPORT.md               # Code validation results
└── WORKFLOW_EXECUTION_REPORT.md       # Execution test results
```

### Module Overview

- **shared.py**: Dataclass definitions for workflow inputs, outputs, and activity data
- **activities.py**: 6 activities implementing business logic (schema upload, reviews, completion)
- **workflow.py**: Workflow orchestration with complex control flow logic
- **worker.py**: Worker process that executes workflows and activities
- **starter.py**: Client for starting workflow executions
- **interact.py**: Client for interacting with running workflows (Updates, Queries)

## Interacting with Running Workflows

**IMPORTANT**: This workflow has **3 Update handlers** and **1 Query handler**. You **must** use the `interact.py` client to interact with running workflows.

The `interact.py` script provides a command-line interface for:
- **Updates**: Send validated approval decisions that return immediate feedback
- **Queries**: Check workflow status without modifying state

### Using the Interaction Client

**Get workflow ID** from starter output or Web UI, then:

```bash
# Send an Update
uv run interact update <workflow-id> <update-name> '<json-args>'

# Execute a Query
uv run interact query <workflow-id> <query-name>

# See all available commands
uv run interact
```

### Available Interactions

#### Update: `submit_review1_approval`
**Purpose**: Submit approval decision after Review1.a and Review1.b complete
**Input**: `ApprovalDecision` with fields:
- `reviewer_id` (string): Identifier of the reviewer
- `approved` (boolean): Approval decision (true/false)
- `comments` (string, optional): Reviewer comments

**Example**:
```bash
uv run interact update schema-approval-abc123 submit_review1_approval '{
  "reviewer_id": "reviewer1@example.com",
  "approved": true,
  "comments": "Schema structure looks good"
}'
```

**Python equivalent**:
```python
from temporalio.client import Client
from schema_approval_temporal.shared import ApprovalDecision

client = await Client.connect("localhost:7233")
handle = client.get_workflow_handle("schema-approval-abc123")

result = await handle.execute_update(
    SchemaApprovalWorkflow.submit_review1_approval,
    ApprovalDecision(
        reviewer_id="reviewer1@example.com",
        approved=True,
        comments="Schema structure looks good"
    )
)
print(f"Result: {result.status} - {result.message}")
```

#### Update: `submit_review2_approval`
**Purpose**: Submit approval decision after Review2, determine if Review3 is needed
**Input**: `ApprovalDecision` with fields:
- `reviewer_id` (string): Identifier of the reviewer
- `approved` (boolean): Approval decision (true/false)
- `skip_review3` (boolean): Whether to skip Review3 (true) or require it (false)
- `comments` (string, optional): Reviewer comments

**Example (skip Review3)**:
```bash
uv run interact update schema-approval-abc123 submit_review2_approval '{
  "reviewer_id": "reviewer2@example.com",
  "approved": true,
  "skip_review3": true,
  "comments": "Approved - no need for Review3"
}'
```

**Example (require Review3)**:
```bash
uv run interact update schema-approval-abc123 submit_review2_approval '{
  "reviewer_id": "reviewer2@example.com",
  "approved": true,
  "skip_review3": false,
  "comments": "Approved but requires Review3"
}'
```

#### Update: `submit_review3_approval`
**Purpose**: Submit final approval decision after Review3
**Input**: `ApprovalDecision` with fields:
- `reviewer_id` (string): Identifier of the reviewer
- `approved` (boolean): Final approval decision (true/false)
- `comments` (string, optional): Reviewer comments

**Example**:
```bash
uv run interact update schema-approval-abc123 submit_review3_approval '{
  "reviewer_id": "reviewer3@example.com",
  "approved": true,
  "comments": "Final approval granted"
}'
```

#### Query: `get_status`
**Purpose**: Query current workflow status and review progress
**Returns**: Dictionary with current stage, iteration, approval status, and per-review status

**Example**:
```bash
uv run interact query schema-approval-abc123 get_status
```

**Output includes**:
- Current stage (review1_check, review2_check, review3_check, completed)
- Iteration number
- Overall approval status
- Per-review status (completed, approval received, approved)
- Next action guidance

### Complete Workflow Example

```bash
# Terminal 1: Start Temporal dev server
temporal server start-dev

# Terminal 2: Start worker
uv run worker

# Terminal 3: Start workflow
uv run starter
# Note the workflow ID from output: schema-approval-abc123

# Terminal 4: Monitor in Web UI
open http://localhost:8233/namespaces/default/workflows/schema-approval-abc123

# Terminal 5: Interact with workflow
# Step 1: Check initial status
uv run interact query schema-approval-abc123 get_status
# Shows: current_stage = review1_check, waiting for Review1 approval

# Step 2: Submit Review1 approval (both Review1.a and Review1.b are complete)
uv run interact update schema-approval-abc123 submit_review1_approval '{
  "reviewer_id": "reviewer1@example.com",
  "approved": true,
  "comments": "Parallel reviews passed"
}'
# Workflow progresses to Review2

# Step 3: Check status again
uv run interact query schema-approval-abc123 get_status
# Shows: current_stage = review2_check, waiting for Review2 approval

# Step 4: Submit Review2 approval (choose whether Review3 is needed)
# Option A: Skip Review3 (expedited approval)
uv run interact update schema-approval-abc123 submit_review2_approval '{
  "reviewer_id": "reviewer2@example.com",
  "approved": true,
  "skip_review3": true,
  "comments": "Approved - no additional review needed"
}'
# Workflow completes via CompleteReview_1

# Option B: Require Review3 (full approval path)
uv run interact update schema-approval-abc123 submit_review2_approval '{
  "reviewer_id": "reviewer2@example.com",
  "approved": true,
  "skip_review3": false,
  "comments": "Approved but needs final review"
}'
# Workflow progresses to Review3

# Step 5: If Review3 is required, submit final approval
uv run interact update schema-approval-abc123 submit_review3_approval '{
  "reviewer_id": "reviewer3@example.com",
  "approved": true,
  "comments": "Final comprehensive approval"
}'
# Workflow completes via CompleteReview_2

# Step 6: Verify completion
uv run interact query schema-approval-abc123 get_status
# Shows: current_stage = completed, approved = true
```

## Configuration

### Workflow Timeouts

The workflow has the following timeout configuration:
- **Execution timeout**: Not specified (defaults to unlimited)
- **Activity timeouts**:
  - `upload_schema`: 30 seconds
  - `review_1a`: 5 minutes
  - `review_1b`: 5 minutes
  - `review_2`: 10 minutes
  - `review_3`: 15 minutes
  - `complete_review`: 30 seconds
- **Human approval timeouts**: 24 hours per review stage

To adjust timeouts, edit the timeout parameters in `schema_approval_temporal/workflow.py`:
```python
start_to_close_timeout=timedelta(seconds=30)  # Modify as needed
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
    submission_id="custom-submission-id",
    schema_data={"your": "schema"},
    submitter_email="user@example.com",
    priority=1
)
```

### Loop Iterations

The DO_WHILE loop has a maximum of 10 iterations to prevent infinite loops. To adjust:

Edit `schema_approval_temporal/workflow.py`:
```python
max_iterations = 10  # Change to desired value
```

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

**Error**: `Activity X not found`

**Solution**: Ensure worker is running before starting workflow.

---

**Error**: `Workflow execution timeout`

**Solution**: The workflow waits for human approvals. Ensure you submit approval decisions via `interact.py`:
```bash
uv run interact query <workflow-id> get_status  # Check current stage
uv run interact update <workflow-id> submit_review1_approval '{"reviewer_id": "...", "approved": true}'
```

---

**Error**: `Cannot submit Review2 approval at stage: review1_check`

**Solution**: You're trying to submit an approval for the wrong stage. Check current stage with:
```bash
uv run interact query <workflow-id> get_status
```

Then submit the approval for the current stage (review1_check, review2_check, or review3_check).

### Type Checking Issues

To run type checking:
```bash
mypy schema_approval_temporal --strict --ignore-missing-imports
```

If errors occur, see `VALIDATION_REPORT.md` for guidance.

### Workflow Loops Forever

**Issue**: Workflow continues looping without completing

**Causes**:
1. Approval decisions not being submitted
2. Approval decisions rejected (approved=false)
3. Maximum iterations (10) not yet reached

**Solution**:
- Check workflow status: `uv run interact query <workflow-id> get_status`
- Submit approvals with `approved: true` at each stage
- Monitor Web UI at http://localhost:8233 for current state

## Development

### Activity Business Logic

Activities in `schema_approval_temporal/activities.py` contain placeholder implementations marked with TODO comments. These need to be filled in with actual business logic:

1. **upload_schema**: Implement schema storage, registry integration, notifications
2. **review_1a/review_1b**: Implement review validation logic, reviewer assignment
3. **review_2**: Implement architectural review logic
4. **review_3**: Implement final comprehensive review logic
5. **complete_review**: Implement finalization (notifications, status updates, audit trail)

### Running Tests

Tests can be added in a `tests/` directory using pytest:
```bash
uv add --dev pytest
pytest tests/
```

### Code Quality

This project follows strict Python standards:
- **Type hints**: All functions have complete type annotations
- **Docstrings**: Comprehensive documentation for all public APIs
- **Code style**: PEP 8 compliant

Run linting:
```bash
uv add --dev ruff
ruff check schema_approval_temporal/
```

## Migration Notes

This project was automatically migrated from Conductor. See:
- **CONDUCTOR_COMPARISON.md** - Side-by-side Conductor vs Temporal examples
- **CONDUCTOR_MIGRATION_NOTES.md** - Migration decisions and recommendations
- **VALIDATION_REPORT.md** - Code validation results
- **WORKFLOW_EXECUTION_REPORT.md** - Execution test results

### Key Differences from Conductor

1. **Control Flow**: Conductor JSON primitives (DO_WHILE, FORK_JOIN, SWITCH) translated to Python (while, asyncio.gather, if/elif)
2. **Data Passing**: Conductor expressions `${workflow.variables.X}` → Python `self._X`
3. **Human Interaction**: Conductor SWITCH with `${user_action.output.approved}` → Temporal Updates with validation
4. **Error Handling**: Conductor retry configs → Temporal RetryPolicy objects
5. **Activities**: Conductor SIMPLE tasks → Temporal @activity.defn functions
6. **Loop Exit**: Conductor `workflow.variables.approved` → Temporal `self._approved` flag

## Additional Resources

- [Temporal Python SDK Documentation](https://docs.temporal.io/develop/python)
- [Temporal Python SDK API Reference](https://python.temporal.io/)
- [Temporal Learning Portal](https://learn.temporal.io/)
- [Conductor to Temporal Migration Guide](./conductor-migration/)

## Support

For migration-specific questions:
- Review `CONDUCTOR_MIGRATION_NOTES.md` for decisions made during migration
- Check `VALIDATION_REPORT.md` for code quality notes
- Check `WORKFLOW_EXECUTION_REPORT.md` for execution test results
- Consult the Conductor migration documentation in `conductor-migration/`

---

**Generated by Conductor to Temporal Migration Tool**
**Migration Date**: November 23, 2025
**Migration Agent**: documentation-generator (Agent 7)

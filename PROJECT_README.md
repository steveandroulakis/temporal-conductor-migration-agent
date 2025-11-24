# FetchUsers - Temporal Migration

Migrated from Netflix Conductor workflow definition to Temporal Python SDK.

**Original Conductor Workflow**: `conductor-definition/OSS_HTTP_workflow_example.json`
**Migration Date**: 2025-11-23
**Complexity**: low (Max nesting depth: 0)

## Overview

This project implements the **fetch_users** workflow using Temporal's Python SDK. The workflow was automatically migrated from a Conductor JSON definition.

### Workflow Description

Fetch users and filter based on name. This workflow fetches user data from the JSONPlaceholder API and filters it to only include users whose name starts with the letter 'C'.

### Control Flow

This workflow implements:
- Simple sequential workflow with only 2 tasks
- No conditional branching
- No loops or iterations
- No parallel execution
- Straightforward data pipeline: fetch → transform → output

**Tasks**:
1. **fetch_users** (HTTP) - Fetches user data from JSONPlaceholder API via HTTP GET request
2. **jq_filter_users** (JSON_JQ_TRANSFORM) - Filters user list to only include users whose name starts with 'C' using JQ transformation

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
uv add temporalio httpx
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
Worker ready — polling task queue: fetch-users-task-queue
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

Example output:
```
Starting workflow: fetch_users-c3574b8f-6370-4d4d-a2f7-8cd7f08e43f5
Workflow URL: http://localhost:8233/namespaces/default/workflows/fetch_users-...

Workflow completed successfully!
Result: 3 users found

Filtered Users:
  - Clementine Bauch (ID: 3)
  - Chelsey Dietrich (ID: 5)
  - Clementina DuBuque (ID: 10)
```

### 4. Monitor in Web UI

Open the workflow in your browser:
```
http://localhost:8233
```

Navigate to your workflow to see:
- Workflow execution history
- Activity results
- Current status
- Event timeline

## Project Structure

```
fetch_users_temporal/
├── fetch_users_temporal/          # Main package directory
│   ├── __init__.py                # Package marker
│   ├── shared.py                  # Data models (dataclasses)
│   ├── activities.py              # Activity implementations
│   ├── workflow.py                # Workflow definition
│   ├── worker.py                  # Worker registration
│   ├── starter.py                 # Workflow starter
│   └── interact.py                # Workflow interaction client (Queries)
├── pyproject.toml                 # Project configuration
├── setup.sh                       # Automated setup script
├── PROJECT_README.md              # This file
├── CONDUCTOR_COMPARISON.md        # Conductor vs Temporal mapping
├── CONDUCTOR_MIGRATION_NOTES.md   # Migration decisions
├── VALIDATION_REPORT.md           # Code validation results
└── WORKFLOW_EXECUTION_REPORT.md   # Execution validation results
```

### Module Overview

- **shared.py**: Dataclass definitions for workflow inputs, outputs, and activity data (6 dataclasses)
- **activities.py**: 2 activities implementing business logic (HTTP calls, JSON filtering)
- **workflow.py**: Workflow orchestration with sequential control flow logic
- **worker.py**: Worker process that executes workflows and activities
- **starter.py**: Client for starting workflow executions
- **interact.py**: Client for querying running workflows

## Querying Workflows

This workflow provides a Query handler for checking workflow status without modifying state.

### Using the Interaction Client

Get workflow ID from starter output or Web UI, then:

```bash
# Execute a Query
uv run interact query <workflow-id> get_status

# Example
uv run interact query fetch_users-c3574b8f-6370-4d4d-a2f7-8cd7f08e43f5 get_status
```

### Available Queries

#### Query: `get_status`
**Purpose**: Query current workflow status and description
**Returns**: Dictionary with workflow type and description

**Example**:
```bash
uv run interact query fetch_users-abc123 get_status
```

**Python equivalent**:
```python
from temporalio.client import Client
from fetch_users_temporal.workflow import FetchUsersWorkflow

client = await Client.connect("localhost:7233")
handle = client.get_workflow_handle("fetch_users-abc123")

result = await handle.query(FetchUsersWorkflow.get_status)
print(f"Status: {result}")
```

## Configuration

### Workflow Timeouts

The workflow has the following timeout configuration:
- **Execution timeout**: 1 hour (configurable in starter.py)
- **Activity timeouts**:
  - `fetch_users`: 60 seconds (HTTP network operation)
  - `jq_filter_users`: 10 seconds (in-memory data processing)

To adjust timeouts, edit the timeout parameters in `fetch_users_temporal/workflow.py`:
```python
start_to_close_timeout=timedelta(seconds=30)  # Modify as needed
```

### Task Queue

The worker and starter use task queue: **fetch-users-task-queue**

To change the task queue:
1. Update `worker.py`: `task_queue="new-queue-name"`
2. Update `starter.py`: `task_queue="new-queue-name"`

### Workflow Input

This workflow has no input parameters in the original Conductor definition. The workflow operates with default values:
- HTTP endpoint: https://jsonplaceholder.typicode.com/users
- Filter pattern: Names starting with 'C' (regex: `^C`)

To customize these values, edit `fetch_users_temporal/activities.py`:
```python
# Customize HTTP endpoint
async def fetch_users(
    uri: str = "https://your-api.com/users",  # Change default
    method: str = "GET",
) -> Dict[str, Any]:
    ...

# Customize filter pattern
async def jq_filter_users(
    users: List[Dict[str, Any]],
    name_pattern: str = "^A"  # Change pattern (e.g., names starting with 'A')
) -> List[Dict[str, Any]]:
    ...
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

**Error**: `Activity fetch_users not found`

**Solution**: Ensure worker is running before starting workflow.

---

**Error**: `Workflow execution timeout`

**Solution**: Increase timeout in starter.py:
```python
execution_timeout=timedelta(hours=2)  # Increase as needed
```

### HTTP Activity Issues

**Error**: `httpx.TimeoutException`

**Solution**: The JSONPlaceholder API may be slow or unreachable. Check your internet connection or increase timeout in activities.py:
```python
response = await client.request(
    method=method,
    url=uri,
    timeout=120.0  # Increase from 60.0
)
```

---

**Error**: `httpx.HTTPError: 404 Not Found`

**Solution**: Verify the API endpoint is correct. The default endpoint should work, but if customized, ensure it returns a JSON array of user objects.

### Type Checking Issues

To run type checking:
```bash
mypy fetch_users_temporal --strict --ignore-missing-imports
```

If errors occur, see `VALIDATION_REPORT.md` for guidance.

## Development

### Running Tests

Tests can be added in a `tests/` directory using pytest:
```bash
uv add --dev pytest
pytest tests/
```

Example test structure:
```python
# tests/test_activities.py
import pytest
from fetch_users_temporal.activities import jq_filter_users

@pytest.mark.asyncio
async def test_filter_users():
    users = [
        {"name": "Alice", "id": 1},
        {"name": "Charlie", "id": 2},
        {"name": "Bob", "id": 3},
    ]
    result = await jq_filter_users(users, "^C")
    assert len(result) == 1
    assert result[0]["name"] == "Charlie"
```

### Code Quality

This project follows strict Python standards:
- **Type hints**: All functions have complete type annotations
- **Docstrings**: Comprehensive documentation for all public APIs
- **Code style**: PEP 8 compliant

Run linting:
```bash
uv add --dev ruff
ruff check fetch_users_temporal/
```

Format code:
```bash
ruff format fetch_users_temporal/
```

## Migration Notes

This project was automatically migrated from Conductor. See:
- **CONDUCTOR_COMPARISON.md** - Side-by-side Conductor vs Temporal examples
- **CONDUCTOR_MIGRATION_NOTES.md** - Migration decisions and recommendations

### Key Differences from Conductor

- **Control Flow**: Conductor JSON primitives (HTTP, JSON_JQ_TRANSFORM) translated to Python activities and sequential async/await
- **Data Passing**: Conductor expressions `${fetch_users_ref.output.response.body}` → Python `fetch_result["body"]`
- **Error Handling**: Conductor retry configs → Temporal RetryPolicy objects with exponential backoff
- **Activities**:
  - Conductor HTTP task → Temporal activity with httpx.AsyncClient()
  - Conductor JSON_JQ_TRANSFORM → Temporal activity with Python regex filtering
- **Type Safety**: JSON strings → strongly-typed Python dataclasses

## Performance

Based on execution validation:
- **Workflow Duration**: ~100ms (typical)
- **HTTP Activity**: ~80ms (network latency to JSONPlaceholder API)
- **Filter Activity**: ~5ms (in-memory processing)
- **Total Events**: 17 events in workflow history
- **State Transitions**: 11

## Additional Resources

- [Temporal Python SDK Documentation](https://docs.temporal.io/develop/python)
- [Temporal Python SDK API Reference](https://python.temporal.io/)
- [Temporal Learning Portal](https://learn.temporal.io/)
- [Conductor to Temporal Migration Guide](./conductor-migration/)

## Support

For migration-specific questions:
- Review `CONDUCTOR_MIGRATION_NOTES.md` for decisions made during migration
- Check `VALIDATION_REPORT.md` for code quality notes
- Check `WORKFLOW_EXECUTION_REPORT.md` for execution validation
- Consult the Conductor migration documentation in `conductor-migration/`

---

**Generated by Conductor to Temporal Migration Tool**
**Migration Date**: 2025-11-23
**Validation Status**: All validations PASSED
**Execution Status**: Workflow executed successfully

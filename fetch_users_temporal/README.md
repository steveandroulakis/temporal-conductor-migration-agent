# fetch_users_temporal Module Documentation

This module contains the Temporal workflow implementation for **fetch_users**.

## Module Structure

### shared.py
Data models (dataclasses) for workflow and activity inputs/outputs.

**Exports**:
- `WorkflowInput` - Workflow input parameters (empty for this workflow)
- `WorkflowOutput` - Workflow output containing filtered users list
- `HttpTaskInput` - Input parameters for HTTP activity
- `HttpTaskOutput` - HTTP response data structure
- `FilterUsersInput` - Input for user filtering activity
- `FilterUsersOutput` - Output from user filtering activity

### activities.py
Activity implementations for external operations and data transformations.

**Exports**:
- `fetch_users` - HTTP GET activity that fetches user data from JSONPlaceholder API
  - Returns: Dict with status_code, body, and headers
  - Timeout: 60 seconds
  - Retry: 5 attempts with exponential backoff
- `jq_filter_users` - Filtering activity that filters users by name pattern
  - Input: List of user dicts, regex pattern
  - Returns: Filtered list of users
  - Timeout: 10 seconds
  - Retry: 2 attempts

### workflow.py
Workflow orchestration and control flow.

**Exports**:
- `FetchUsersWorkflow` - Main workflow class
  - Fetches users from API
  - Filters by name pattern (default: starts with 'C')
  - Returns WorkflowOutput with filtered users
- Query handler: `get_status()` - Returns workflow type and description

### worker.py
Worker registration and execution.

**Entry Point**: `worker:main`

Registers the workflow and all activities, then polls the task queue `fetch-users-task-queue` for work.

Usage:
```bash
uv run worker
```

### starter.py
Workflow starter client.

**Entry Point**: `starter:main`

Starts a new workflow execution with default input parameters and waits for completion.

Usage:
```bash
uv run starter
```

### interact.py
Workflow interaction client for queries.

**Entry Point**: `interact:main`

Provides command-line interface for querying running workflows.

Usage:
```bash
uv run interact query <workflow-id> get_status
```

## Usage

See the main project PROJECT_README.md for complete setup and usage instructions.

## Development

When modifying this module:

1. **Maintain strict type hints**: All functions must pass `mypy --strict`
   ```bash
   mypy fetch_users_temporal --strict --ignore-missing-imports
   ```

2. **Update docstrings**: Keep documentation comprehensive and accurate

3. **Run validation**: Ensure code quality before committing
   ```bash
   python3 -m py_compile fetch_users_temporal/*.py
   ruff check fetch_users_temporal/
   ```

4. **Test with worker and starter**: Verify changes work end-to-end
   ```bash
   # Terminal 1
   uv run worker
   
   # Terminal 2
   uv run starter
   ```

## Architecture Notes

### Workflow Sandbox Compliance

The workflow module uses safe import patterns:
```python
# CORRECT: Import activities by name
from .activities import (
    fetch_users,
    jq_filter_users,
)
```

This prevents non-deterministic imports (httpx, re) from violating the workflow sandbox.

### Data Flow

```
WorkflowInput (empty)
    ↓
fetch_users activity
    ↓
HTTP response (List of users)
    ↓
jq_filter_users activity
    ↓
Filtered users (names starting with 'C')
    ↓
WorkflowOutput (users field)
```

### Error Handling

- **HTTP activity**: Retries on network errors (5 attempts, exponential backoff)
- **Filter activity**: Minimal retries (2 attempts) since it's pure computation
- **Workflow**: Propagates activity failures after retry exhaustion

## Migration Notes

**Migrated from Conductor workflow**: `conductor-definition/OSS_HTTP_workflow_example.json`

**Translation patterns used**:
- Conductor HTTP task → httpx-based async activity
- Conductor JSON_JQ_TRANSFORM → Python regex filtering activity
- Conductor sequential tasks → async/await chain
- Conductor JSONPath expressions → Python dict/variable access

See `CONDUCTOR_COMPARISON.md` for detailed side-by-side translation examples.

---

**Generated**: 2025-11-23
**Complexity**: Low (2 tasks, sequential execution)
**Production Ready**: Yes (pending business logic customization)

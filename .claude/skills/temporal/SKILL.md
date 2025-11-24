---
name: temporal
description: "Manage Temporal workflows: server lifecycle, worker processes, workflow execution, monitoring, and troubleshooting for Python SDK with temporal server start-dev."
version: 1.0.0
---

# Temporal Skill

Manage Temporal workflows using local development server. This skill provides tools and conventions for server lifecycle, worker management, workflow execution, monitoring, and troubleshooting.

**Target SDK**: Python only
**Server Type**: `temporal server start-dev` (local development)

## Quickstart

```bash
# Ensure server is running
./tools/ensure-server.sh

# Ensure worker is running (smart restart if code changed)
./tools/ensure-worker.sh

# Start a workflow (from your project)
uv run starter

# Monitor in Web UI
# Visit: http://localhost:8233
```

After starting a worker, ALWAYS tell the user how to monitor logs:

```bash
# To monitor worker logs:
tail -f $CLAUDE_TEMPORAL_LOG_DIR/worker-$(basename "$(pwd)").log

# Or check worker health:
./tools/monitor-worker-health.sh
```

## Environment Variables Convention

All tools use standardized environment variables:

```bash
# Core paths (auto-created by tools)
export CLAUDE_TEMPORAL_PID_DIR="${TMPDIR:-/tmp}/claude-temporal-pids"
export CLAUDE_TEMPORAL_LOG_DIR="${TMPDIR:-/tmp}/claude-temporal-logs"

# Project context (auto-detected)
export CLAUDE_TEMPORAL_PROJECT_DIR="$(pwd)"
export CLAUDE_TEMPORAL_PROJECT_NAME="$(basename "$(pwd)")"
export CLAUDE_TEMPORAL_NAMESPACE="${CLAUDE_TEMPORAL_NAMESPACE:-default}"

# Worker configuration (customizable)
export TEMPORAL_WORKER_CMD="${TEMPORAL_WORKER_CMD:-uv run worker}"
export TEMPORAL_CLI="${TEMPORAL_CLI:-temporal}"

# Server configuration (customizable)
export TEMPORAL_ADDRESS="${TEMPORAL_ADDRESS:-localhost:7233}"
export TEMPORAL_UI_ADDRESS="${TEMPORAL_UI_ADDRESS:-http://localhost:8233}"
```

## Naming Conventions

- **Project name**: Current directory basename, e.g., `my-project`
- **PID files**: `$CLAUDE_TEMPORAL_PID_DIR/worker-{project}.pid`
- **Log files**: `$CLAUDE_TEMPORAL_LOG_DIR/worker-{project}.log`
- **Server PID**: `$CLAUDE_TEMPORAL_PID_DIR/server.pid`
- **Workflow IDs**: Use descriptive slugs, e.g., `order-processing-abc123`

## Server Management

### Ensuring Server is Running

```bash
./tools/ensure-server.sh
```

This script:
1. Checks if `temporal` CLI is installed
2. Tests connectivity to port 7233
3. If not running: starts `temporal server start-dev` in background
4. Saves PID to `$CLAUDE_TEMPORAL_PID_DIR/server.pid`
5. Waits for server readiness

### Server Status

```bash
# Check if server is running
temporal operator namespace list

# Or check server PID
cat $CLAUDE_TEMPORAL_PID_DIR/server.pid
```

### Stopping Server

```bash
# Kill server (included in kill-all-workers.sh --include-server)
kill $(cat $CLAUDE_TEMPORAL_PID_DIR/server.pid)
```

## Worker Management

### Smart Restart Pattern

Workers use a **smart restart** pattern to handle code changes:

```bash
./tools/ensure-worker.sh
```

**Behavior**:
1. Checks if worker PID exists for current project
2. If exists: gracefully kills existing worker (5s timeout, then force)
3. Starts new worker process
4. Saves PID to `$CLAUDE_TEMPORAL_PID_DIR/worker-{project}.pid`
5. Redirects logs to `$CLAUDE_TEMPORAL_LOG_DIR/worker-{project}.log`
6. Waits for "Worker started" message in logs (30s timeout)

**Output**:
```
⏳ Stopping existing worker...
✓ Worker stopped
🚀 Starting worker...
⏳ Waiting for worker to be ready...
✓ Worker ready (PID: 12345)

To monitor worker logs:
  tail -f /tmp/claude-temporal-logs/worker-my-project.log
```

### Worker Startup Requirements

**CRITICAL**: Your Python worker MUST log startup confirmation for tools to work:

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# After worker starts
logger.info("Worker started")  # <- wait-for-worker-ready.sh looks for this
```

### Custom Worker Command

Override default `uv run worker`:

```bash
export TEMPORAL_WORKER_CMD="uv run python -m myproject.worker"
./tools/ensure-worker.sh
```

### Killing Workers

```bash
# Kill worker for current project
./tools/kill-worker.sh

# Kill all workers across all projects
./tools/kill-all-workers.sh

# Kill all workers AND server
./tools/kill-all-workers.sh --include-server

# Kill specific project worker
./tools/kill-all-workers.sh -p my-project
```

**Graceful shutdown**: Workers get 5 seconds to shutdown gracefully (SIGTERM), then forced (SIGKILL).

### Listing Workers

```bash
./tools/list-workers.sh
```

**Output**:
```
PROJECT       PID    STATUS   UPTIME   COMMAND
my-project    12345  running  5m 23s   uv run worker
other-proj    12346  dead     -        -
server        12340  running  1h 15m   temporal server start-dev
```

### Monitoring Worker Health

```bash
./tools/monitor-worker-health.sh
```

**Output**:
```
Worker Status: HEALTHY
PID: 12345
Uptime: 15m 32s
Last log entry: [timestamp] Processing activity task
```

## Workflow Execution

### Starting Workflows

From your project directory:

```bash
# Using your starter script
uv run starter

# Or directly with temporal CLI
temporal workflow start \
  --type MyWorkflow \
  --task-queue my-task-queue \
  --workflow-id my-workflow-$(date +%s)
```

**Best practice**: Generate unique workflow IDs using timestamps or UUIDs.

### Tracking Workflow IDs

Always capture workflow IDs for monitoring:

```python
# In your starter script
workflow_id = f"order-{order_id}-{int(time.time())}"
result = await client.start_workflow(
    MyWorkflow.run,
    id=workflow_id,
    task_queue="my-task-queue"
)
print(f"Started workflow: {workflow_id}")  # <- Capture this
```

### Web UI Access

Visit the Temporal Web UI to see all workflows:
```
http://localhost:8233
```

## Workflow Monitoring

### Polling for Status

```bash
./tools/wait-for-workflow-status.sh \
  --workflow-id my-workflow-123 \
  --status COMPLETED \
  --timeout 300
```

**Exit codes**:
- `0`: Status matched
- `1`: Timeout

**Supported statuses**: `RUNNING`, `COMPLETED`, `FAILED`, `CANCELED`, `TERMINATED`, `TIMED_OUT`

### Checking Workflow Status

```bash
# Get workflow details
temporal workflow describe --workflow-id my-workflow-123

# Get workflow execution history
temporal workflow show --workflow-id my-workflow-123
```

### Getting Workflow Results

```bash
# Get workflow result with formatted output
./tools/get-workflow-result.sh --workflow-id my-workflow-123

# Get raw JSON result only
./tools/get-workflow-result.sh --workflow-id my-workflow-123 --raw

# Or use temporal CLI directly
temporal workflow show --workflow-id my-workflow-123 --fields long
```

**Output includes**:
- Workflow status (COMPLETED, FAILED, CANCELED, TERMINATED, etc.)
- Result payload for completed workflows
- Failure messages for failed workflows
- Termination reasons
- Links to Web UI and analysis commands

### Listing Recent Workflows

```bash
# List all workflows from last 5 minutes (default)
./tools/list-recent-workflows.sh

# List failed workflows from last 10 minutes
./tools/list-recent-workflows.sh --minutes 10 --status FAILED

# List completed workflows of specific type from last 2 minutes
./tools/list-recent-workflows.sh --minutes 2 --status COMPLETED --workflow-type MyWorkflow
```

**Use cases**:
- Check for recently terminated child workflows
- Find workflows that failed with interesting errors
- Monitor recent completions to verify success messages
- Track workflow execution patterns over time

## Workflow Interaction

### Sending Signals

```bash
temporal workflow signal \
  --workflow-id my-workflow-123 \
  --name approve \
  --input '{"approved": true}'
```

### Sending Updates

```bash
temporal workflow update \
  --workflow-id my-workflow-123 \
  --name update_status \
  --input '{"status": "processing"}'
```

### Querying Workflow State

```bash
temporal workflow query \
  --workflow-id my-workflow-123 \
  --name get_status
```

## Troubleshooting

### Finding Stalled Workflows

```bash
./tools/find-stalled-workflows.sh
```

**Output**:
```
WORKFLOW_ID               ERROR_TYPE                      ATTEMPTS
workflow-abc-123          WorkflowTaskFailed              5
workflow-def-456          ActivityTaskFailed              3
```

This detects workflows with systematic issues like:
- Repeated workflow task failures
- Missing workflow/activity registrations
- Worker not registered errors

### Analyzing Workflow Errors

```bash
./tools/analyze-workflow-error.sh --workflow-id workflow-abc-123
```

**Output**:
```
Error Type: WorkflowTaskFailed
Reason: Workflow type not registered
Stack Trace: [truncated]
Recommendation: Worker missing workflow registration.
  - Check worker.py includes this workflow
  - Restart worker: ./tools/ensure-worker.sh
```

### Error Routing

Tools automatically route errors to correct fixes:

| Error Type | Cause | Action |
|------------|-------|--------|
| WorkflowTaskFailed | Worker missing workflow/activity | Restart worker with updated code |
| ActivityTaskFailed | Activity code error | Check activity logs, fix code |
| WorkflowExecutionFailed | Business logic error | Check workflow logic |
| Timeout | Workflow/activity took too long | Review timeout settings |

### Common Issues

**"Workflow type not registered"**
```bash
# Worker missing workflow registration
# Fix: Update worker.py to include workflow, then:
./tools/ensure-worker.sh
```

**"Worker not receiving tasks"**
```bash
# Check worker health
./tools/monitor-worker-health.sh

# Check worker logs
tail -f $CLAUDE_TEMPORAL_LOG_DIR/worker-$(basename "$(pwd)").log

# Restart worker
./tools/ensure-worker.sh
```

**"Workflow stuck in running state"**
```bash
# Check for stalled workflows
./tools/find-stalled-workflows.sh

# Analyze specific workflow
./tools/analyze-workflow-error.sh --workflow-id <id>
```

## Cleanup Operations

### Canceling Workflows

```bash
# Cancel single workflow
temporal workflow cancel --workflow-id my-workflow-123

# Bulk cancel by pattern
./tools/bulk-cancel-workflows.sh --pattern "test-.*"

# Cancel all stalled workflows
./tools/find-stalled-workflows.sh | awk '{print $1}' > stalled.txt
./tools/bulk-cancel-workflows.sh --workflow-ids stalled.txt
```

### Cleaning Up Processes

```bash
# Kill all workers and server
./tools/kill-all-workers.sh --include-server

# Clean up PID files
rm -rf $CLAUDE_TEMPORAL_PID_DIR/*

# Clean up log files
rm -rf $CLAUDE_TEMPORAL_LOG_DIR/*
```

## Helper Tools Reference

### ensure-server.sh
Ensure Temporal server is installed and running.

**Exit codes**:
- `0`: Server ready
- `1`: CLI not installed
- `2`: Server failed to start

### ensure-worker.sh
Ensure exactly one worker is running with fresh code.

**Exit codes**:
- `0`: Worker started and ready
- `1`: Worker failed to start
- `2`: Worker started but readiness timeout

### kill-worker.sh
Kill worker for current project (graceful → force).

**Exit codes**:
- `0`: Worker killed successfully
- `1`: No worker running

### wait-for-worker-ready.sh
Poll worker logs for startup confirmation.

**Parameters**:
- `--log-file <path>`: Log file to monitor
- `--pattern <regex>`: Pattern to match (default: "Worker started")
- `--timeout <seconds>`: Max wait time (default: 30)

### wait-for-workflow-status.sh
Poll workflow for specific status.

**Parameters**:
- `--workflow-id <id>`: Workflow ID to monitor
- `--status <status>`: Status to wait for
- `--timeout <seconds>`: Max wait time (default: 300)

### find-stalled-workflows.sh
Detect workflows with systematic issues.

### analyze-workflow-error.sh
Parse workflow history to extract error details.

**Parameters**:
- `--workflow-id <id>`: Workflow to analyze

### bulk-cancel-workflows.sh
Cancel multiple workflows.

**Parameters**:
- `--workflow-ids <file>`: File with workflow IDs (one per line)
- `--pattern <regex>`: Cancel workflows matching pattern

### list-workers.sh
List all tracked workers and their status.

### kill-all-workers.sh
Kill all tracked workers.

**Options**:
- `-p <project>`: Kill only specific project worker
- `--include-server`: Also kill temporal dev server

### monitor-worker-health.sh
Check if worker process is healthy.

### list-recent-workflows.sh
List recently completed/terminated workflows within a time window.

**Parameters**:
- `--minutes <N>`: Look back N minutes (default: 5)
- `--status <status>`: Filter by status (COMPLETED, FAILED, CANCELED, TERMINATED, TIMED_OUT)
- `--workflow-type <type>`: Filter by workflow type

**Exit codes**:
- `0`: Successfully listed workflows
- `1`: CLI error or invalid parameters

### get-workflow-result.sh
Get the result/output from a completed workflow execution.

**Parameters**:
- `--workflow-id <id>`: Workflow ID to query (required)
- `--run-id <id>`: Specific run ID (optional)
- `--raw`: Output raw JSON result only

**Exit codes**:
- `0`: Successfully retrieved result
- `1`: Workflow not found, still running, or CLI error

## Best Practices

1. **Always use ensure-worker.sh** when code changes to get fresh worker
2. **Capture workflow IDs** in logs for troubleshooting
3. **Monitor worker logs** during development: `tail -f $CLAUDE_TEMPORAL_LOG_DIR/worker-*.log`
4. **Use Web UI** for visual workflow inspection: http://localhost:8233
5. **Add "Worker started" log** in Python worker for readiness detection
6. **Use descriptive workflow IDs** with timestamps/UUIDs for uniqueness
7. **Check stalled workflows** periodically with `find-stalled-workflows.sh`
8. **Route errors correctly** using `analyze-workflow-error.sh` recommendations
9. **Check recent workflows** after major changes with `list-recent-workflows.sh` to spot patterns
10. **Verify workflow results** with `get-workflow-result.sh` to catch unexpected outputs

## Workflow Development Cycle

Typical development workflow:

```bash
# 1. Start server (once per session)
./tools/ensure-server.sh

# 2. Make code changes to workflow/activity
# ... edit your code ...

# 3. Restart worker with new code
./tools/ensure-worker.sh

# 4. Start workflow
uv run starter

# 5. Monitor in Web UI or wait for completion
./tools/wait-for-workflow-status.sh --workflow-id <id> --status COMPLETED

# 6. Verify workflow result
./tools/get-workflow-result.sh --workflow-id <id>

# 7. Check recent workflows to spot patterns
./tools/list-recent-workflows.sh --minutes 2

# 8. If issues, troubleshoot
./tools/analyze-workflow-error.sh --workflow-id <id>

# 9. Repeat from step 2
```

## Integration with Python Projects

### Project Structure

```
my-temporal-project/
├── pyproject.toml           # uv project config
├── worker.py                # Worker entry point
├── starter.py               # Workflow starter
├── workflows/
│   └── my_workflow.py       # Workflow definitions
└── activities/
    └── my_activity.py       # Activity definitions
```

### Worker Entry Point (worker.py)

```python
import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker
from workflows.my_workflow import MyWorkflow
from activities.my_activity import my_activity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="my-task-queue",
        workflows=[MyWorkflow],
        activities=[my_activity],
    )

    logger.info("Worker started")  # <- REQUIRED for ensure-worker.sh
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Starter Script (starter.py)

```python
import asyncio
import time
from temporalio.client import Client
from workflows.my_workflow import MyWorkflow

async def main():
    client = await Client.connect("localhost:7233")

    workflow_id = f"my-workflow-{int(time.time())}"

    result = await client.execute_workflow(
        MyWorkflow.run,
        id=workflow_id,
        task_queue="my-task-queue",
    )

    print(f"Workflow {workflow_id} completed: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Security Considerations

- All PID and log files are stored in temp directories (`/tmp`)
- Server runs in dev mode (not for production)
- Workers run with current user permissions
- No authentication/authorization in dev server
- Clean up PIDs/logs when done with project

## Troubleshooting the Tools

### "temporal command not found"
```bash
# Install temporal CLI
# macOS:
brew install temporal

# Linux:
# Download from https://github.com/temporalio/cli/releases
```

### "Cannot connect to server"
```bash
# Check if server is running
./tools/ensure-server.sh

# Check server logs
cat $CLAUDE_TEMPORAL_LOG_DIR/server.log
```

### "Worker readiness timeout"
```bash
# Check if worker.py has "Worker started" log
grep "Worker started" worker.py

# Check worker logs
tail -f $CLAUDE_TEMPORAL_LOG_DIR/worker-$(basename "$(pwd)").log
```

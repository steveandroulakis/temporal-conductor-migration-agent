Temporal Workflow Operations Guide
A focused guide for running and managing Temporal workflows in development, covering server management, worker lifecycle, and workflow interaction.

1) Prerequisites: Temporal CLI Installation
1.1 Verify Installation
The Temporal CLI is REQUIRED for all development work. Check if it's installed:
bashtemporal --version
Expected output: temporal version 1.0.0 (or similar)
1.2 Install Temporal CLI (if missing)
If the command fails, install now:
macOS:
bashbrew install temporal
Linux (amd64):
bashcurl -sSf https://temporal.download/cli.sh | sh
Linux (arm64):
Download from: https://temporal.download/cli/archive/latest?platform=linux&arch=arm64
Windows (amd64):
Download from: https://temporal.download/cli/archive/latest?platform=windows&arch=amd64
Windows (arm64):
Download from: https://temporal.download/cli/archive/latest?platform=windows&arch=arm64
1.3 Verify Installation Succeeded
After installation, confirm the CLI works:
bashtemporal --version || {
    echo "❌ ERROR: Temporal CLI installation failed"
    echo "Please install manually and verify before proceeding"
    exit 1
}

2) Managing the Temporal Dev Server
2.1 Check if Server is Running
bashtemporal operator namespace describe default >/dev/null 2>&1 && echo "✓ Server is running" || echo "✗ Server is not running"
2.2 Start the Dev Server
Manual start (foreground):
bashtemporal server start-dev
Background start:
bashtemporal server start-dev &
Auto-start if not running:
bashif temporal operator namespace describe default >/dev/null 2>&1; then
    echo "✓ Temporal dev server is already running"
else
    echo "⚠️  Starting Temporal dev server..."
    temporal server start-dev &
    sleep 5
    
    # Verify startup
    if temporal operator namespace describe default >/dev/null 2>&1; then
        echo "✓ Temporal dev server started successfully"
        echo "📊 Web UI available at: http://localhost:8233"
    else
        echo "❌ ERROR: Failed to start Temporal dev server"
        exit 1
    fi
fi
```

### 2.3 Access the Web UI

Once running, access the Temporal Web UI at:
```
http://localhost:8233
2.4 Stop the Dev Server
bashpkill -f "temporal server start-dev"

3) Worker Management
3.1 Start a Worker
bash# Start worker in background and save PID
uv run worker.py > worker.log 2>&1 &
WORKER_PID=$!
echo $WORKER_PID > worker.pid

# Wait for startup
sleep 3

# Verify worker is running
ps -p $WORKER_PID > /dev/null || {
    echo "❌ ERROR: Worker failed to start"
    tail -n 50 worker.log
    exit 1
}

echo "✓ Worker started (PID: $WORKER_PID)"
3.2 Check Worker Status
bash# Check if worker process is alive
if [ -f worker.pid ]; then
    WORKER_PID=$(cat worker.pid)
    if ps -p $WORKER_PID > /dev/null; then
        echo "✓ Worker is running (PID: $WORKER_PID)"
    else
        echo "✗ Worker is not running"
    fi
else
    echo "✗ No worker PID file found"
fi
3.3 View Worker Logs
bash# View recent logs
tail -f worker.log

# View all logs
cat worker.log

# View last 50 lines
tail -n 50 worker.log
3.4 Stop a Worker
Graceful shutdown (preferred):
bashif [ -f worker.pid ]; then
    kill $(cat worker.pid)
    wait $(cat worker.pid) 2>/dev/null || true
    rm -f worker.pid
    echo "✓ Worker stopped"
else
    echo "✗ No worker PID file found"
fi
Force kill all workers:
bashpkill -f "worker.py"
rm -f worker.pid
3.5 Restart a Worker
bash# Stop existing worker
[ -f worker.pid ] && kill $(cat worker.pid) || true
rm -f worker.pid
pkill -f "worker.py" || true

# Start fresh worker
uv run worker.py > worker.log 2>&1 &
echo $! > worker.pid
sleep 3

# Verify
ps -p $(cat worker.pid) >/dev/null || {
    echo "❌ Worker failed to restart"
    tail -n 50 worker.log
    exit 1
}

echo "✓ Worker restarted successfully"

4) Executing Workflows
4.1 Run a Workflow
bash# Basic execution
uv run starter.py "YourInput"

# With error handling
uv run starter.py "YourInput" || {
    echo "❌ Workflow execution failed"
    exit 1
}
4.2 Validate Execution with Temporal CLI
List recent workflows:
bashtemporal workflow list --namespace default
List as JSON (for parsing):
bashtemporal workflow list --namespace default --output json
Show specific workflow details:
bash# Replace with your actual workflow ID
temporal workflow show --workflow-id "hello-activity-workflow-CodeAgent"
Show workflow as JSON:
bashtemporal workflow show --workflow-id "your-workflow-id" --output json
Query specific workflow:
bashtemporal workflow list --query "WorkflowId = 'your-workflow-id'"
4.3 Check Workflow Completion
bash# Check if workflow completed successfully
if temporal workflow list --query "WorkflowId = 'your-workflow-id'" | grep -q "COMPLETED"; then
    echo "✓ Workflow completed successfully"
else
    echo "✗ Workflow did not complete"
    temporal workflow show --workflow-id "your-workflow-id"
fi

5) Interacting with Running Workflows
5.1 Send a Signal
Using Python snippet:
bashuv run - <<'PY'
import asyncio
from temporalio.client import Client

async def main():
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle("your-workflow-id")
    await handle.signal("signal_name", "signal_argument")
    print("✓ Signal sent")

asyncio.run(main())
PY
5.2 Query a Workflow
Using Python snippet:
bashuv run - <<'PY'
import asyncio
from temporalio.client import Client

async def main():
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle("your-workflow-id")
    result = await handle.query("query_name")
    print(f"Query result: {result}")

asyncio.run(main())
PY
5.3 Cancel a Workflow
bashtemporal workflow cancel --workflow-id "your-workflow-id"
5.4 Terminate a Workflow
bashtemporal workflow terminate --workflow-id "your-workflow-id" --reason "Manual termination"

6) Complete Operational Flow
6.1 One-Command E2E Execution Script
bash#!/usr/bin/env bash
set -euo pipefail

# Verify Temporal CLI
if ! command -v temporal &> /dev/null; then
    echo "❌ ERROR: Temporal CLI not installed"
    exit 1
fi

# Start server if needed
if ! temporal operator namespace describe default >/dev/null 2>&1; then
    echo "⚠️  Starting Temporal dev server..."
    temporal server start-dev &
    sleep 5
fi

# Start worker
echo "Starting worker..."
uv run worker.py > worker.log 2>&1 &
WORKER_PID=$!
echo $WORKER_PID > worker.pid
sleep 3

# Verify worker started
ps -p $WORKER_PID >/dev/null || {
    echo "❌ Worker failed to start"
    tail -n 50 worker.log
    exit 1
}

# Execute workflow
echo "Running workflow..."
uv run starter.py "TestInput"

# Validate execution
echo "Validating..."
sleep 2
temporal workflow show --workflow-id "hello-activity-workflow-TestInput"

if temporal workflow list --query "WorkflowId = 'hello-activity-workflow-TestInput'" | grep -q "COMPLETED"; then
    echo "✓ Validation successful"
else
    echo "❌ Validation failed"
    exit 1
fi

# Clean shutdown
echo "Shutting down worker..."
kill "$WORKER_PID"
wait "$WORKER_PID" 2>/dev/null || true
rm -f worker.pid

echo "✓ E2E execution complete"

7) Troubleshooting Operations
7.1 Worker Won't Start
Check if Temporal server is running:
bashtemporal operator namespace describe default
Check worker logs:
bashtail -n 100 worker.log
Verify dependencies:
bashuv pip list | grep temporalio
7.2 Workflow Appears Hung
List workflow to check status:
bashtemporal workflow list --namespace default
Show detailed workflow history:
bashtemporal workflow show --workflow-id "your-workflow-id"
Common causes:

Worker not running: Check worker.log and verify PID is alive
Workflow task failed: Check worker logs for exceptions - workflow will retry after code fix
Waiting for input: Workflow may be legitimately waiting for a signal or timer

7.3 Port Already in Use
If port 7233 or 8233 is already in use:
bash# Find process using port
lsof -i :7233
lsof -i :8233

# Kill existing Temporal server
pkill -f "temporal server start-dev"
7.4 Clean Slate Restart
bash# Stop everything
pkill -f "temporal server start-dev"
pkill -f "worker.py"
rm -f worker.pid

# Wait a moment
sleep 2

# Start fresh
temporal server start-dev &
sleep 5

# Start worker
uv run worker.py > worker.log 2>&1 &
echo $! > worker.pid

8) Quick Reference Commands
Server Operations
bash# Check server status
temporal operator namespace describe default

# Start server (background)
temporal server start-dev &

# Stop server
pkill -f "temporal server start-dev"

# Web UI
open http://localhost:8233
Worker Operations
bash# Start worker
uv run worker.py > worker.log 2>&1 & echo $! > worker.pid

# Check worker status
ps -p $(cat worker.pid) 2>/dev/null && echo "Running" || echo "Stopped"

# View logs
tail -f worker.log

# Stop worker
kill $(cat worker.pid); rm -f worker.pid
Workflow Operations
bash# Execute workflow
uv run starter.py "input"

# List workflows
temporal workflow list --namespace default

# Show workflow details
temporal workflow show --workflow-id "workflow-id"

# Cancel workflow
temporal workflow cancel --workflow-id "workflow-id"

9) Success Checklist
Before considering operations complete, verify:

 Temporal dev server is reachable on localhost:7233
 Worker started successfully and wrote worker.pid
 Worker is actively polling (check worker.log for "polling" message)
 Workflow execution completed (verify with temporal workflow show)
 Workflow status shows COMPLETED in CLI output
 Worker shutdown cleanly and PID file removed
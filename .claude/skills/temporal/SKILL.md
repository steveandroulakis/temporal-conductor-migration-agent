---
name: temporal
description: "Manage Temporal workflows: server lifecycle, worker processes, workflow execution, monitoring, and troubleshooting for Python SDK with temporal server start-dev."
version: 1.0.0
---

# **Temporal Skill**

Manage Temporal workflows using local development server. This skill focuses on the **execution, validation, and troubleshooting** lifecycle of workflows.

Target SDK: Python only  
Server Type: temporal server start-dev (local development)

## **1. Start Environment & Run Workflows**

Before running any workflow code, you must ensure the server is up and your worker is running the **latest version** of your code.

### **Step A: Ensure Server**

./tools/ensure-server.sh

*Checks if temporal is installed and starts the dev server if needed.*

### **Step B: Start/Restart Worker (Crucial)**

**Rule:** Never run old workers. Stale workers with outdated code cause non-determinism errors.

./tools/ensure-worker.sh

*Automatically finds and kills old workers for this project, then starts a new one with fresh code.*

### **Step C: Execute Workflow**

Run your starter script to initiate the workflow.

uv run starter  
# Always capture the Workflow ID printed by your starter script!

## **2. Validation: Check Status & Results**

Do not assume a workflow succeeded just because it didn't throw an exception immediately. You must validate the execution on the server.

### **Check Recent Executions**

Poll recently executed workflows to see if they completed, failed, or timed out.

# Check last 5 minutes of activity  
./tools/list-recent-workflows.sh

### **Verify Results (The Source of Truth)**

Workflows may "Complete" successfully but return an error message as the result. Always inspect the final output.

./tools/get-workflow-result.sh --workflow-id <workflow-id>

## **3. Troubleshooting: Stalls & Failures**

If a workflow is not completing, use this decision matrix to resolve the issue.

### **Scenario A: The Workflow is Stalled**

Symptoms: Workflow is RUNNING but making no progress.  
Cause: Workflow Task Errors (bugs in workflow code) or infinite retries (downstream service failures) will stall execution.  
**Diagnosis:**

# 1. Find which workflows are stalled  
./tools/find-stalled-workflows.sh

# 2. Analyze the specific error causing the stall  
./tools/analyze-workflow-error.sh --workflow-id <workflow-id>

### **Scenario B: Handling the Error**

Once you identify the error via analyze-workflow-error.sh, choose the correct fix path:

#### **Path 1: Non-Determinism Errors**

*Error indicates workflow logic changed (e.g., history mismatch).*

1. **Terminate** the affected workflow (it cannot be saved).  
   temporal workflow terminate --workflow-id <workflow-id>

2. **Fix** the code logic.  
3. **Restart** the worker: ./tools/ensure-worker.sh  
4. **Start** a new workflow execution.

#### **Path 2: Standard Bugs (Code Errors)**

*Error is a standard Python exception/bug.*

1. **Fix** the root cause in your code.  
2. **Restart** the worker: ./tools/ensure-worker.sh  
3. **Do NOT terminate** the workflow. The new worker will pick up the history and continue successfully from where it left off.

#### **Path 3: Stuck on Retries**

*Workflow is healthy, but an Activity is failing repeatedly.*

1. Check external systems/API connectivity.  
2. If code is wrong, fix code -> ./tools/ensure-worker.sh.  
3. Workflow will retry the activity with the new code automatically.

## **4. Logs & Deep Dives**

If the CLI tools don't reveal the issue, check the raw logs or the Web UI.

### **Worker Logs**

# Tail the logs for the current project worker  
tail -f $CLAUDE_TEMPORAL_LOG_DIR/worker-$(basename "$(pwd)").log

*Tip: Look for "Worker started" to confirm initialization.*

### **Web UI**

Visual inspection of the Event History is often the fastest way to understand complex branching.

http://localhost:8233

## **5. Cleanup**

When finished with a task or switching contexts, ensure you don't leave orphan processes.

# Kill workers for the current project  
./tools/kill-worker.sh

# Kill ALL workers (cleanup entire environment)  
./tools/kill-all-workers.sh

## **Tool Reference**

### **Lifecycle Tools**

* ensure-server.sh: Starts local dev server if not running.  
* ensure-worker.sh: **Smart Restart.** Kills old project workers, starts new one, waits for readiness.  
* kill-worker.sh: Kills current project's worker.  
* kill-all-workers.sh: cleanup tool. Use --include-server to stop everything.

### **Monitoring Tools**

* list-recent-workflows.sh: Shows workflows from last N minutes (--minutes 10).  
* find-stalled-workflows.sh: Detects workflows with high failure attempts.  
* monitor-worker-health.sh: Verifies worker PID and log activity.  
* wait-for-workflow-status.sh: Blocks until workflow reaches status (useful for scripts).

### **Debugging Tools**

* analyze-workflow-error.sh: Extracts stack traces and failure reasons from history.  
* get-workflow-result.sh: Retrieves final output of completed workflows.  
* bulk-cancel-workflows.sh: Mass cancellation tool (--pattern "test-.*").

### **Environment Variables**

* CLAUDE_TEMPORAL_LOG_DIR: /tmp/claude-temporal-logs  
* CLAUDE_TEMPORAL_PID_DIR: /tmp/claude-temporal-pids  
* TEMPORAL_UI_ADDRESS: http://localhost:8233
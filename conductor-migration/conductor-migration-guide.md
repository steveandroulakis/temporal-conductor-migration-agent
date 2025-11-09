# Conductor to Temporal: Migration Guide

> **Part of the [Conductor to Temporal Migration Guide](./README.md)**

This document provides comprehensive, step-by-step instructions for migrating Netflix Conductor JSON workflow definitions to production-ready Temporal Python projects.

---

## Migration Phases Overview

The migration process consists of 8 sequential phases. Each phase builds on the previous one and includes verification steps.

| Phase | Name | Purpose | Key Outputs |
|-------|------|---------|-------------|
| **1** | Analyze Conductor JSON | Parse and understand workflow structure | conductor-analysis.json |
| **2** | Create Project Structure | Set up Python project skeleton | Project directory, pyproject.toml, shared.py |
| **3** | Generate Activities | Translate tasks to activities | activities.py with @activity.defn functions |
| **4** | Generate Workflow | Translate control flow to Python | workflow.py with @workflow.defn class |
| **5** | Generate Worker | Create worker registration | worker.py |
| **6** | Generate Starter | Create workflow execution client | starter.py |
| **7** | Setup and Validation | Install dependencies and validate | mypy passes |
| **8** | Documentation | Create comprehensive docs | README.md, comparison docs |

**Estimated Time**: 30-60 minutes depending on workflow complexity

---

## Prerequisites

### Required Tools

1. **Python 3.11+**
   ```bash
   python3 --version | grep -q 'Python 3\\.1[1-9]\\|Python 3\\.[2-9][0-9]'
   ```

2. **UV (Python package manager)**
   ```bash
   # macOS
   brew install uv
   # or
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **jq (JSON processor)**
   ```bash
   # macOS
   brew install jq

   # Linux
   apt-get install jq  # or equivalent for your distro
   ```

4. **Valid Conductor JSON workflow file**
   ```bash
   # Validate your Conductor JSON
   jq empty your-workflow.json
   ```

---

## Generated Project Structure

The migration produces a complete Python project:

```
{project_name}/
  __init__.py              # Package marker
  shared.py                # Dataclasses for workflow/activity I/O
  activities.py            # Activity implementations (@activity.defn)
  workflow.py              # Workflow definition (@workflow.defn)
  worker.py                # Worker registration and execution
  starter.py               # Workflow starter client
  pyproject.toml           # Dependencies and project metadata
  setup.sh                 # Automated setup script
  README.md                # Setup and usage instructions
  CONDUCTOR_COMPARISON.md  # Side-by-side Conductor vs Temporal examples
  CONDUCTOR_MIGRATION_NOTES.md  # Migration-specific notes
  .gitignore               # Python gitignore
```

### Key Dependencies

- `temporalio>=1.5.0` - Temporal Python SDK
- `httpx>=0.26.0` - HTTP client for HTTP activities
- `mypy>=1.7.0` - Type checking

---

## Phase 1: Analysis & Setup

### Phase 1.1: Analyze Conductor JSON

#### Objectives
- Parse the Conductor workflow JSON file
- Extract workflow metadata (name, version, description, inputs, outputs)
- Analyze all tasks and their types
- Map control flow patterns (sequential, parallel, conditional, loops)
- Analyze data flow and dependencies
- Generate structured analysis file

#### Tasks

1. **Load Conductor JSON file**
   ```bash
   jq . your-conductor-workflow.json
   ```

2. **Extract workflow metadata**
   - Workflow name and version
   - Input parameters array
   - Output parameters (if defined)
   - Timeout configuration
   - Description

3. **Analyze each task** in the workflow:
   - Task name and type (SIMPLE, HTTP, SWITCH, etc.)
   - Input parameters (including JSONPath expressions)
   - Output parameters
   - Task-specific configuration
   - Dependencies on other tasks

4. **Map control flow patterns**
   - Sequential task chains
   - Parallel execution blocks (FORK_JOIN + JOIN)
   - Conditional branches (SWITCH with decisionCases)
   - Loops (DO_WHILE with loopCondition)
   - Dynamic parallel execution (DYNAMIC_FORK)
   - Sub-workflow calls (SUB_WORKFLOW)

5. **Identify human interaction patterns**
   - **HUMAN_TASK** tasks (require signal/update implementation)
   - **WAIT** tasks waiting for external events
   - External data references like `${user_action.output.*}` or `${approval.output.decision}`
   - DO_WHILE loops checking for approval/human input
   - Document which tasks need human interaction → See [Human Interaction guide](./conductor-human-interaction.md)

6. **Analyze data flow**
   - Which tasks use workflow inputs
   - Which tasks depend on other task outputs
   - Variable usage and dependencies
   - JSONPath expressions to translate

7. **Generate analysis file**: `conductor-analysis.json`
   ```json
   {
     "analysis_date": "ISO 8601 timestamp",
     "conductor_file": "path/to/conductor.json",
     "workflow_metadata": { ... },
     "project_config": {
       "project_name": "derived_name",
       "project_name_snake": "derived_name",
       "task_queue": "derived-task-queue"
     },
     "tasks": [ ... ],
     "control_flow_patterns": { ... },
     "data_flow": { ... },
     "external_interactions": { ... },
     "translation_notes": [ ... ]
   }
   ```

#### Verification
```bash
test -f conductor-analysis.json
jq empty conductor-analysis.json
jq -e '.workflow_metadata.name' conductor-analysis.json
jq -e '.tasks | length > 0' conductor-analysis.json
```

#### Common Issues
- **Invalid JSON**: Ensure Conductor file is valid JSON
- **Missing fields**: Some Conductor workflows omit optional fields (handle gracefully)
- **Complex JSONPath**: Document complex expressions for manual review

---

### Phase 1.2: Create Project Structure

#### Objectives
- Create Python project directory structure
- Generate basic dataclasses for workflow I/O
- Set up pyproject.toml with dependencies
- Create README.md skeleton
- Create .gitignore

#### Tasks

1. **Read analysis file**
   ```bash
   jq -r '.project_config.project_name_snake' conductor-analysis.json
   ```

2. **Create project directory**
   ```bash
   mkdir {project_name}
   cd {project_name}
   ```

3. **Create package files**
   - `__init__.py` (package marker, can be empty)
   - `shared.py` with basic dataclasses:
     ```python
     from dataclasses import dataclass
     from typing import Optional, List, Dict, Any

     @dataclass
     class WorkflowInput:
         """Input parameters for the workflow."""
         # Fields based on Conductor input_parameters
         param1: str
         param2: int
         # ... etc

     @dataclass
     class WorkflowOutput:
         """Output from the workflow."""
         # Fields based on Conductor output or final task results
         result: Any
     ```

4. **Create pyproject.toml**
   ```toml
   [project]
   name = "{project_name}"
   version = "0.1.0"
   description = "Temporal workflow migrated from Conductor"
   requires-python = ">=3.11"
   dependencies = [
       "temporalio>=1.5.0",
       "httpx>=0.26.0",
   ]

   [project.optional-dependencies]
   dev = [
       "mypy>=1.7.0",
   ]

   [project.scripts]
   worker = "{project_name}.worker:main"
   starter = "{project_name}.starter:main"

   [build-system]
   requires = ["setuptools>=68.0"]
   build-backend = "setuptools.build_meta"
   ```

   > **Note:** The `[project.scripts]` section creates console commands. After running `uv sync`, you can run `uv run worker` or `uv run starter` instead of the longer module syntax.

5. **Create .gitignore**
   ```
   __pycache__/
   *.py[cod]
   *$py.class
   .mypy_cache/
   *.egg-info/
   dist/
   build/
   .venv/
   venv/
   worker.pid
   worker.log
   ```

6. **Create README.md skeleton**
   ```markdown
   # {Workflow Name} - Temporal Migration

   Migrated from Conductor workflow: `{conductor_file}`

   ## Prerequisites
   - Python 3.11+
   - Temporal dev server

   ## Setup
   See setup instructions below...
   ```

#### Verification
```bash
test -d {project_name}
test -f {project_name}/shared.py
test -f {project_name}/pyproject.toml
python3 -m py_compile {project_name}/shared.py
```

---

## Phase 2: Code Generation

### Phase 2.1: Generate Activities

#### Objectives
- Translate Conductor tasks to Temporal activities
- Generate activity functions with proper decorators
- Handle HTTP tasks with httpx
- Create activity input/output dataclasses
- Add comprehensive docstrings

#### Tasks

1. **Identify tasks that become activities**
   - SIMPLE tasks → `@activity.defn` functions
   - HTTP tasks → `@activity.defn` with httpx
   - Custom task types → `@activity.defn` functions
   - **Skip these** (handled in workflow logic):
     - INLINE tasks (inline Python code)
     - SET_VARIABLE tasks (variable assignment)
     - WAIT tasks (signals)
     - Control flow tasks (SWITCH, DO_WHILE, FORK_JOIN, JOIN)

2. **Create activities.py**
   ```python
   from dataclasses import dataclass
   from typing import Optional, List, Dict, Any
   import httpx
   from temporalio import activity

   @activity.defn
   async def simple_task_activity(input_param: str) -> Dict[str, Any]:
       """
       Activity migrated from Conductor SIMPLE task: {task_name}

       Args:
           input_param: Description of parameter

       Returns:
           Dict containing task results
       """
       activity.logger.info(f"Running activity with parameter: {input_param}")
       # TODO: Implement actual activity logic
       return {"status": "success", "result": input_param}

   @activity.defn
   async def http_task_activity(uri: str, method: str = "GET",
                                 headers: Optional[Dict[str, str]] = None,
                                 body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
       """
       HTTP activity migrated from Conductor HTTP task: {task_name}

       Args:
           uri: HTTP endpoint URL
           method: HTTP method (GET, POST, etc.)
           headers: Optional HTTP headers
           body: Optional request body

       Returns:
           Dict containing HTTP response
       """
       activity.logger.info(f"{method} {uri}")
       async with httpx.AsyncClient() as client:
           response = await client.request(
               method, uri, headers=headers or {}, json=body
           )
           return {
               "status_code": response.status_code,
               "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
           }
   ```

3. **Update shared.py** with activity-specific dataclasses if needed

4. **Extract configuration from Conductor tasks**
   - Document timeout requirements
   - Note retry policies needed
   - Identify special task configurations

#### Verification
```bash
test -f {project_name}/activities.py
python3 -m py_compile {project_name}/activities.py
grep -q '@activity.defn' {project_name}/activities.py
```

#### Common Issues
- **HTTP authentication**: Document if HTTP tasks require auth headers
- **Complex input transformations**: May need custom dataclasses
- **External dependencies**: Document third-party services called

---

### Phase 2.2: Generate Workflow

#### Objectives
- Create workflow class with @workflow.defn
- Translate Conductor control flow to Python
- Implement activity execution with proper timeouts
- Handle data passing between tasks
- Configure retry policies

#### Tasks

1. **Create workflow.py**

   > ⚠️ **CRITICAL: WORKFLOW SANDBOX VIOLATION WARNING**
   >
   > **DO NOT** import activity modules that contain non-deterministic code (httpx, random, datetime.now(), file I/O, database connections, etc.).
   >
   > **ONLY import specific activity functions by name**. If your `activities.py` imports external libraries like httpx, boto3, or any I/O libraries, importing the entire module (`from . import activities`) will violate the workflow sandbox and cause validation errors at runtime.
   >
   > **Correct pattern**: `from .activities import activity1, activity2, activity3`
   > **Incorrect pattern**: `from . import activities` ❌ (if activities.py has non-deterministic imports)

   ```python
   import asyncio
   from datetime import timedelta
   from dataclasses import dataclass
   from typing import Optional, List, Dict, Any
   from temporalio import workflow
   from temporalio.common import RetryPolicy  # NOTE: Import from .common, NOT .workflow

   with workflow.unsafe.imports_passed_through():
       from .shared import WorkflowInput, WorkflowOutput
       # Import specific activity functions, NOT the entire module
       # Replace with actual activity function names from your activities.py
       from .activities import simple_task_activity, http_task_activity

   @workflow.defn
   class MyWorkflow:
       """
       Temporal workflow migrated from Conductor workflow: {workflow_name}

       Original Conductor file: {conductor_file}
       """

       @workflow.run
       async def run(self, input: WorkflowInput) -> WorkflowOutput:
           """
           Execute the workflow.

           Args:
               input: Workflow input parameters

           Returns:
               WorkflowOutput containing workflow results
           """
           workflow.logger.info(f"Starting workflow with input: {input}")

           # Translate Conductor tasks to activity executions
           # See control flow patterns in architecture guide

           return WorkflowOutput(result="success")
   ```

2. **Translate control flow patterns** (see [Architecture Guide](./conductor-architecture.md) and [Primitives Reference](./conductor-primitives-reference.md)):
   - **Sequential**: Chain activities with await
   - **Parallel (FORK_JOIN)**: Use `asyncio.gather()`
   - **Conditional (SWITCH)**: Use `if/elif/else`
   - **Loops (DO_WHILE)**: Use `while` loop
   - **Dynamic parallel (DYNAMIC_FORK)**: List comprehension + `asyncio.gather()`
   - **Sub-workflows (SUB_WORKFLOW)**: Use `workflow.execute_child_workflow()`

   For detailed examples of each primitive with complete JSON and Python code, see the [Primitives Reference](./conductor-primitives-reference.md).

3. **Implement WAIT tasks** with signals:
   ```python
   def __init__(self):
       self.received_data = None

   @workflow.signal
   async def receive_data(self, data: Dict[str, Any]):
       """Signal handler for external data."""
       self.received_data = data

   # In run method:
   await workflow.wait_condition(lambda: self.received_data is not None)
   ```

   **For human approvals or interactive workflows**: If your Conductor workflow has `HUMAN_TASK` or waits for human input (references like `${user_action.output.*}`), use **Updates** instead of Signals for better validation and request-response semantics. See the complete [Human Interaction Patterns guide](./conductor-human-interaction.md) for detailed examples of:
   - When to use Updates vs Signals
   - Approval workflows with validation
   - Multiple reviewer patterns
   - Timeout and escalation handling

4. **Configure activity execution**

   Since you imported specific activity functions (not the module), reference them directly:
   ```python
   # Using imported activity function directly
   result = await workflow.execute_activity(
       simple_task_activity,  # Function imported at top of file
       args=[input.param],
       start_to_close_timeout=timedelta(seconds=300),
       retry_policy=RetryPolicy(
           maximum_attempts=3,
           initial_interval=timedelta(seconds=10),
           backoff_coefficient=2.0,
           maximum_interval=timedelta(seconds=100)
       )
   )
   ```

   Alternatively, use string names (more flexible but less type-safe):
   ```python
   # Using string name
   result = await workflow.execute_activity(
       "simple_task_activity",
       args=[input.param],
       start_to_close_timeout=timedelta(seconds=300),
       retry_policy=RetryPolicy(
           maximum_attempts=3,
           initial_interval=timedelta(seconds=10),
           backoff_coefficient=2.0,
           maximum_interval=timedelta(seconds=100)
       )
   )
   ```

5. **Translate data passing**
   - Conductor `${workflow.input.field}` → `input.field`
   - Conductor `${task_name.output.field}` → `task_name_result.field`
   - Conductor `${workflow.variables.var}` → `var` (local variable)

#### Verification
```bash
test -f {project_name}/workflow.py
python3 -m py_compile {project_name}/workflow.py
grep -q '@workflow.defn' {project_name}/workflow.py
grep -q '@workflow.run' {project_name}/workflow.py

# CRITICAL: Verify workflow sandbox compliance (detects import violations)
python3 -c "import sys; sys.path.insert(0, '.'); from {project_name}.workflow import MyWorkflow; print('✓ Workflow sandbox compliance verified')" || {
    echo "❌ Workflow sandbox violation detected! Check imports in workflow.py"
    exit 1
}
```

#### Common Issues
- **Nested control flow**: Carefully preserve execution order
- **Complex data transformations**: May need helper functions
- **Timeouts**: Ensure activity timeouts are appropriate for task duration

---

### Phase 2.3: Generate Worker

#### Objectives
- Create worker registration script
- Register workflows and activities
- Configure task queue
- Add proper logging

#### Tasks

1. **Create worker.py**
   ```python
   """Worker process that hosts the workflow."""
   import asyncio
   import logging
   import os
   from concurrent.futures import ThreadPoolExecutor
   from temporalio.client import Client
   from temporalio.worker import Worker

   from .workflow import MyWorkflow
   from . import activities

   async def run_worker() -> None:
       """Run Temporal worker."""
       logging.basicConfig(level=logging.INFO)
       logger = logging.getLogger(__name__)

       # Write PID for process management
       with open("worker.pid", "w") as f:
           f.write(str(os.getpid()))

       logger.info("Worker starting")

       # Connect to Temporal server
       client = await Client.connect("localhost:7233")

       # Create worker
       async with Worker(
           client,
           task_queue="{task_queue}",
           workflows=[MyWorkflow],
           activities=[
               activities.activity1,
               activities.activity2,
               # List all activities
           ],
           activity_executor=ThreadPoolExecutor(5)
       ):
           logger.info("Worker ready — polling: {task_queue}")
           try:
               while True:
                   await asyncio.sleep(1)
           except KeyboardInterrupt:
               logger.info("Worker shutting down…")

   def main() -> None:
       """Console script entry point."""
       asyncio.run(run_worker())

   if __name__ == "__main__":
       main()
   ```

   > **Important:** The `main()` function must be synchronous (not async) to work as a console script entry point. It wraps the async function with `asyncio.run()`. If `main()` is async, you'll get "coroutine was never awaited" runtime warnings when running via console scripts.

   **Running the worker:**
   ```bash
   # Option 1: Run as module
   uv run python -m {project_name}.worker

   # Option 2: Use console script (requires [project.scripts] in pyproject.toml)
   uv run worker
   ```

2. **List all activities** from Phase 3 analysis

3. **Configure task queue** from conductor-analysis.json

#### Verification
```bash
test -f {project_name}/worker.py
python3 -m py_compile {project_name}/worker.py
grep -q 'Worker(' {project_name}/worker.py
```

---

### Phase 2.4: Generate Starter

#### Objectives
- Create workflow starter client
- Generate example input data
- Add workflow execution code
- Display results and workflow URL

#### Tasks

1. **Create starter.py**
   ```python
   """Utility for starting the workflow."""
   import asyncio
   import uuid
   import logging
   from datetime import timedelta
   from temporalio.client import Client

   from .workflow import MyWorkflow
   from .shared import WorkflowInput

   async def run_starter() -> None:
       """Start workflow execution."""
       logging.basicConfig(level=logging.INFO)
       logger = logging.getLogger(__name__)

       # Connect to Temporal server
       client = await Client.connect("localhost:7233")

       # Create workflow input with example data
       workflow_input = WorkflowInput(
           param1="example_value",
           param2=123,
           # TODO: Customize input values
       )

       # Generate unique workflow ID
       workflow_id = f"{workflow_name}-{uuid.uuid4()}"

       logger.info(f"Starting workflow: {workflow_id}")

       # Start workflow
       handle = await client.start_workflow(
           MyWorkflow.run,
           workflow_input,
           id=workflow_id,
           task_queue="{task_queue}",
           execution_timeout=timedelta(hours=1)
       )

       print(f"Started workflow: {handle.id}")
       print(f"Workflow URL: http://localhost:8233/namespaces/default/workflows/{handle.id}")

       # Wait for workflow to complete
       result = await handle.result()
       print(f"Workflow result: {result}")

   def main() -> None:
       """Console script entry point."""
       asyncio.run(run_starter())

   if __name__ == "__main__":
       main()
   ```

   > **Important:** The `main()` function must be synchronous (not async) to work as a console script entry point. It wraps the async function with `asyncio.run()`. If `main()` is async, you'll get "coroutine was never awaited" runtime warnings when running via console scripts.

   **Running the starter:**
   ```bash
   # Option 1: Run as module
   uv run python -m {project_name}.starter

   # Option 2: Use console script (requires [project.scripts] in pyproject.toml)
   uv run starter
   ```

2. **Generate example input data** based on Conductor input_parameters

3. **Add comments** about customizing input values

#### Verification
```bash
test -f {project_name}/starter.py
python3 -m py_compile {project_name}/starter.py
grep -q 'start_workflow(' {project_name}/starter.py
```

---

## Phase 3: Setup and Validation

#### Objectives
- Install project dependencies
- Run syntax validation
- Run type checking with mypy strict
- Create automated setup script

#### Tasks

1. **Install dependencies**
   ```bash
   cd {project_name}
   uv venv
   uv add temporalio httpx
   uv add mypy

   # CRITICAL: Sync all dependencies including dev extras
   uv sync --all-extras

   # Verify all required packages are installed
   uv pip list | grep -E "(temporalio|mypy)" || {
       echo "❌ Missing required dependencies"
       exit 1
   }
   ```

2. **Run syntax validation**
   ```bash
   python3 -m py_compile {project_name}/*.py
   ```

3. **Run mypy type checking**
   ```bash
   mypy {project_name} --strict --ignore-missing-imports
   ```
   Fix any type errors until mypy passes

4. **Create setup.sh**
   ```bash
   #!/bin/bash
   set -e

   echo "Setting up project..."

   # Unset Temporal environment variables
   unset TEMPORAL_CLI_ADDRESS TEMPORAL_CLI_NAMESPACE TEMPORAL_CLI_TLS_CERT \
         TEMPORAL_CLI_TLS_KEY TEMPORAL_CERT_PATH TEMPORAL_KEY_PATH \
         TEMPORAL_NAMESPACE TEMPORAL_ADDRESS TEMPORAL_API_KEY \
         TEMPORAL_HOST_PORT TEMPORAL_TLS_CERT TEMPORAL_TLS_KEY

   # Check Python version
   python3 --version | grep -q 'Python 3\\.1[1-9]\\|Python 3\\.[2-9][0-9]' || {
       echo "Error: Python 3.11+ required"
       exit 1
   }

   # Install dependencies
   echo "Installing dependencies..."
   uv venv
   uv add temporalio httpx
   uv add --dev mypy

   # Sync all dependencies including dev extras
   echo "Syncing all dependencies..."
   uv sync --all-extras

   # Verify dependencies installed
   echo "Verifying dependencies..."
   uv pip list | grep -E "(temporalio|mypy)" || {
       echo "Error: Required dependencies missing"
       exit 1
   }

   # Run type checking
   echo "Running type checking..."
   mypy {project_name} --strict --ignore-missing-imports

   echo "Setup complete!"
   echo ""
   echo "Next steps:"
   echo "1. Start worker: uv run python -m {project_name}.worker"
   echo "2. Execute workflow: uv run python -m {project_name}.starter"
   echo ""
   echo "Or if you added [project.scripts] to pyproject.toml:"
   echo "1. Start worker: uv run worker"
   echo "2. Execute workflow: uv run starter"
   ```

5. **Make executable**
   ```bash
   chmod +x setup.sh
   ```

6. **Create CONDUCTOR_MIGRATION_NOTES.md**
   Document any:
   - Conductor features that couldn't be translated
   - Manual implementation steps required
   - Behavioral differences
   - Assumptions made during translation

#### Verification
```bash
cd {project_name}
python3 -c 'import sys; sys.path.insert(0, "."); import workflow, activities, shared, worker, starter'
test -f setup.sh
test -x setup.sh
```

---

## Phase 4: Documentation and Finalization

#### Objectives
- Update README with comprehensive instructions
- Create Conductor comparison documentation
- Add inline code comments
- Generate migration summary report
- Finalize git status

#### Tasks

1. **Update README.md**
   ```markdown
   # {Workflow Name} - Temporal Migration

   Migrated from Conductor workflow: `{conductor_file}`

   ## Overview
   [Brief description of what the workflow does]

   ## Prerequisites
   - Python 3.11+
   - Temporal dev server
   - UV package manager

   ## Setup

   1. Install dependencies:
      ```bash
      ./setup.sh
      ```

   ## Running the Workflow

   1. Start the worker (in separate terminal):
      ```bash
      uv run python -m {project_name}.worker
      # Or: uv run worker (if using [project.scripts])
      ```

   2. Execute the workflow:
      ```bash
      uv run python -m {project_name}.starter
      # Or: uv run starter (if using [project.scripts])
      ```

   3. View workflow in Temporal Web UI:
      http://localhost:8233

   ## Project Structure

   - `shared.py` - Data models (dataclasses)
   - `activities.py` - Activity implementations
   - `workflow.py` - Workflow definition
   - `worker.py` - Worker registration
   - `starter.py` - Workflow starter

   ## Migration Notes

   See `CONDUCTOR_COMPARISON.md` for Conductor vs Temporal mapping details.
   See `CONDUCTOR_MIGRATION_NOTES.md` for migration-specific notes.

   ## Troubleshooting

   [Add common issues and solutions]
   ```

2. **Create CONDUCTOR_COMPARISON.md**
   Side-by-side examples of:
   - Each task type translation
   - Control flow pattern mappings
   - Data passing differences
   - Example from actual migrated workflow

3. **Add inline code comments**
   - Document complex control flow
   - Reference original Conductor task names
   - Explain data transformations

---

## Related Documentation

- [Architecture Guide](./conductor-architecture.md) - Conductor vs Temporal concepts and mappings
- [Primitives Reference](./conductor-primitives-reference.md) - Detailed primitive-by-primitive mapping with complete examples
- [Human Interaction Patterns](./conductor-human-interaction.md) - Implementing approvals, signals, updates, and human-in-the-loop workflows
- [Quality Assurance](./conductor-quality-assurance.md) - Validation, and success criteria
- [Troubleshooting](./conductor-troubleshooting.md) - Common issues and solutions

---

**[← Back to Main Guide](./README.md)**

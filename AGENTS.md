# Temporal Sample Application — Code Agent Runbook (Python)

**Purpose:** A focused reference guide for writing Temporal workflow code in Python, covering project structure, setup, implementation patterns, and common coding pitfalls.

---

## 0) Golden Rules (Do Not Skip)

* ✅ Prefer **`uv run`** for Python script execution
* ✅ Follow the workflow sandbox rules strictly: import specific activity functions by name, never import entire activity modules
* ✅ Use proper imports: `RetryPolicy` comes from `temporalio.common`, not `temporalio.workflow`
* ✅ Always use type hints and follow PEP 8 style guidelines
* ✅ **CRITICAL - Conductor Migrations**: If migrating from Netflix Conductor JSON workflow definitions, you **MUST** follow the comprehensive guides in [conductor-migration/README.md](./conductor-migration/README.md), including:
  - Cross-reference every Conductor task type with the [Primitives Reference](./conductor-migration/conductor-primitives-reference.md) before writing code
  - Implement human-in-the-loop patterns correctly using the [Human Interaction Patterns](./conductor-migration/conductor-human-interaction.md) guide if your workflow has HUMAN_TASK, WAIT, or approval loops
  - Follow all migration phases and quality standards as documented
* ✅ **Always create a comprehensive README.md** for your project that includes:
  - Project overview and purpose
  - Prerequisites and dependencies
  - Step-by-step installation instructions
  - Complete run guide with commands to start worker and execute workflows
  - Configuration details and environment variables
  - Troubleshooting common issues

---

## Migration Scenarios

### Migrating from Netflix Conductor

**If you are migrating a Conductor JSON workflow definition to Temporal**, follow the comprehensive migration guide:

➡️ **See [Conductor Migration Guide](./conductor-migration/README.md)** for complete migration instructions.

**Quick detection**: You're in a migration scenario if:
- You have a Conductor JSON workflow definition file (`.json`)
- The task is to "migrate", "convert", or "translate" from Conductor to Temporal
- You're working with Conductor task types (SIMPLE, HTTP, FORK_JOIN, SWITCH, etc.)

**Migration approach overview**:
1. **Analyze** the Conductor JSON to understand workflow structure and control flow
2. **Generate** complete Temporal Python project with activities, workflows, worker, and starter
3. **Validate** with syntax checking and type checking (mypy --strict)
4. **Document** with comprehensive setup instructions and Conductor comparison

**Key differences from building from scratch**:
- Start with existing Conductor workflow definition rather than requirements
- Follow structured 10-phase migration process
- Generate comprehensive documentation automatically
- Focus on faithful translation of Conductor logic to Temporal patterns

**The rest of this document (AGENTS.md) applies to both migration and from-scratch scenarios** for general Temporal development practices and troubleshooting.

---

## 1) Repository / File Layout (required)

```
_your_app_name_here_/ (or choose an appropriate name)
  __init__.py        # package marker (can be empty)
  shared.py          # dataclasses and shared types
  activities.py      # activity defs only
  workflow.py        # workflow defs only
  worker.py          # long‑running worker (PID + logging)
  starter.py         # workflow starter client (timeouts + exit codes)
AGENTS.md            # this file
pyproject.toml
```

> **Imports:** Use relative imports inside `_your_app_name_here_` (e.g., `from .activities import compose_greeting`). This keeps things consistent as a proper Python package.

> **Running scripts:** Since this is a package structure, run scripts using the module syntax:
> - `uv run python -m _your_app_name_here_.worker`
> - `uv run python -m _your_app_name_here_.starter`
>
> Or add console scripts to `pyproject.toml` (recommended):
> ```toml
> [project.scripts]
> worker = "_your_app_name_here_.worker:main"
> starter = "_your_app_name_here_.starter:main"
> ```
> Then run: `uv run worker` or `uv run starter`

---

## 2) Prerequisites

### 2.1 UV (Python package/runtime manager)

```bash
uv --version
```

If missing:

* **macOS:** `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
* **Windows:** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
* **Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`

Useful checks:

```bash
uv --version
uv python list
```

---

## 3) Project Setup (new projects)

```bash
uv init _your_app_name_here_
cd _your_app_name_here_
mkdir _your_app_name_here_ # (or choose an appropriate name)
```

**Dependencies**

```bash
uv venv
uv add temporalio
uv add --dev ruff mypy

# Sync all dependencies
uv sync --all-extras

# Verify all packages installed
uv pip list
```

### Setup Virtual Environment and Dependencies
```bash
# Create local virtual environment (recommended)
uv venv

# Activate environment (optional - uv run handles this automatically)
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate     # Windows

# Install core Temporal dependencies
uv add temporalio

# Add development dependencies for linting and type checking
uv add --dev ruff mypy

# Sync all dependencies
uv sync --all-extras

# Verify installation
uv pip list
```

**Recommended `pyproject.toml` setup**

```toml
[project]
name = "_your_app_name_here_"
version = "0.1.0"
description = "Temporal workflow sample application"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "temporalio>=1.7.0",
]

[project.optional-dependencies]
dev = ["ruff>=0.1.0", "mypy>=1.0.0"]

[project.scripts]
worker = "_your_app_name_here_.worker:main"
starter = "_your_app_name_here_.starter:main"

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

> **Note:** The `[project.scripts]` section creates console commands that can be run with `uv run worker` or `uv run starter`. This is the recommended approach for package-based projects.

---

## 4) Reference Code

### 4.1 `shared.py`

```python
from dataclasses import dataclass

@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str
```

### 4.2 `activities.py`

```python
from temporalio import activity
from shared import ComposeGreetingInput

@activity.defn
def compose_greeting(input: ComposeGreetingInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    return f"{input.greeting}, {input.name}!"
```

### 4.3 `workflow.py` (with **signal** + **query**)

> ⚠️ **WORKFLOW SANDBOX WARNING**
>
> **Import Pattern**: This example imports a specific activity function (`from activities import compose_greeting`), which is CORRECT.
>
> **DO NOT** import the entire activities module (`from . import activities` or `import activities`) if your activities.py contains non-deterministic imports like httpx, random, or I/O libraries. Doing so will violate the workflow sandbox.
>
> **Safe pattern**: Import specific functions by name
> **Unsafe pattern**: Import entire module when it has non-deterministic dependencies

```python
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy  # NOTE: Import from .common, NOT .workflow
from activities import compose_greeting  # Import specific function, not entire module
from shared import ComposeGreetingInput

@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self._greeting = "Hello"

    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running workflow with parameter %s" % name)
        default_retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=100),
            maximum_attempts=0,
        )
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput(self._greeting, name),
            schedule_to_close_timeout=timedelta(seconds=20),
            retry_policy=default_retry_policy,
        )

    @workflow.signal
    def update_greeting(self, new_greeting: str) -> None:
        self._greeting = new_greeting

    @workflow.query
    def current_greeting(self) -> str:
        return self._greeting
```

### 4.4 `worker.py`

```python
import asyncio, logging, os
from concurrent.futures import ThreadPoolExecutor
from temporalio.client import Client
from temporalio.worker import Worker
from activities import compose_greeting
from workflow import GreetingWorkflow

async def run_worker() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    with open("worker.pid", "w") as f:
        f.write(str(os.getpid()))
    logger.info("Worker starting")
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue="hello-activity-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        activity_executor=ThreadPoolExecutor(5),
    ):
        logger.info("Worker ready — polling: hello-activity-task-queue")
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

> **Important:** The `main()` function must be synchronous (not async) to work as a console script entry point. It wraps the async `run_worker()` function with `asyncio.run()`. If `main()` is async, you'll get "coroutine was never awaited" errors when running via console scripts.

**Running the worker:**
```bash
# Option 1: Run as module
uv run python -m _your_app_name_here_.worker

# Option 2: Use console script (best practice)
# Add to pyproject.toml:
# [project.scripts]
# worker = "_your_app_name_here_.worker:main"
# Then run:
uv run worker
```

### 4.5 `starter.py`

```python
import asyncio, logging, sys
from temporalio.client import Client
from workflow import GreetingWorkflow

async def run_starter() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    try:
        client = await Client.connect("localhost:7233")
        logger.info(f"Starting workflow for name: {name}")
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            name,
            id=f"hello-activity-workflow-{name}",
            task_queue="hello-activity-task-queue",
        )
        print(f"Result: {result}")
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise SystemExit(1)

def main() -> None:
    """Console script entry point."""
    asyncio.run(run_starter())

if __name__ == "__main__":
    main()
```

> **Important:** The `main()` function must be synchronous (not async) to work as a console script entry point. It wraps the async `run_starter()` function with `asyncio.run()`. If `main()` is async, you'll get "coroutine was never awaited" errors when running via console scripts.

**Running the starter:**
```bash
# Option 1: Run as module
uv run python -m _your_app_name_here_.starter

# Option 2: Use console script (best practice)
# Add to pyproject.toml:
# [project.scripts]
# starter = "_your_app_name_here_.starter:main"
# Then run:
uv run starter
```

---

## 5) Troubleshooting

* **Dependency issues:** `uv pip check`, `uv sync --reinstall`, `uv lock --upgrade`
* **SDK features and best practices:** Check https://github.com/temporalio/samples-python.git for examples
* **Intentionally failing a workflow:** Raise a Temporal ApplicationError. Any exception that is an instance of `temporalio.exceptions.FailureError` (e.g., `ApplicationError`) fails the Workflow Execution immediately. Non-Temporal exceptions suspend instead of failing. Example: `raise ApplicationError("Customer lives outside the service area")`
* **Workflow logic patterns:**
  - `workflow.wait_condition` pauses until condition(s) are met
  - Workflows can wait indefinitely for signals or external input
  - Workflow timers (`await asyncio.sleep`) allow time-based delays
  - Non-Temporal exceptions in workflow code cause the workflow task to retry until code is fixed

---

## 6) Common Development Pitfalls (Documented from Real Issues)

These critical issues have been encountered in actual development and have proven solutions:

### Issue: Dependencies Missing
**Symptom**: `ModuleNotFoundError: No module named 'temporalio'`

**Fix**:
```bash
uv sync --all-extras
uv pip list | grep temporalio
```

**Prevention**: Always run `uv sync --all-extras` after adding dependencies

---

### Issue: Console Script Async Main Error
**Symptom**: `RuntimeWarning: coroutine 'main' was never awaited` when running via console scripts (e.g., `uv run worker`)

**Cause**: Console script entry points must be synchronous functions, not async functions.

**Wrong**:
```python
async def main() -> None:  # ❌ Async function
    client = await Client.connect("localhost:7233")
    # ...

if __name__ == "__main__":
    asyncio.run(main())
```

**Correct**:
```python
async def run_worker() -> None:  # Async implementation
    client = await Client.connect("localhost:7233")
    # ...

def main() -> None:  # ✓ Synchronous entry point
    """Console script entry point."""
    asyncio.run(run_worker())

if __name__ == "__main__":
    main()
```

**Why**: When `pyproject.toml` defines `[project.scripts]` entry points like `worker = "package.worker:main"`, it calls `main()` directly. If `main()` is async, Python returns a coroutine object instead of executing it, causing the warning.

---

### Issue: Workflow Sandbox Violation (CRITICAL)
**Symptom**: `RuntimeError: Failed validating workflow` at worker startup

**Cause**: Importing activities module that has non-deterministic dependencies (httpx, boto3, I/O libraries)

**Wrong**:
```python
from . import activities  # ❌ Imports ALL module dependencies
```

**Correct**:
```python
from .activities import activity1, activity2  # ✓ Imports only functions
```

**Detection**:
```bash
python3 -c "from your_package.workflow import YourWorkflow"
```

**Why**: The workflow sandbox requires deterministic code. When you import an entire module, all its imports (including httpx, random, etc.) are loaded, violating sandbox rules.

---

### Issue: Wrong RetryPolicy Import
**Symptom**: `AttributeError: module 'temporalio.workflow' has no attribute 'RetryPolicy'`

**Wrong**:
```python
from temporalio import workflow
retry_policy = workflow.RetryPolicy(...)  # ❌
```

**Correct**:
```python
from temporalio.common import RetryPolicy  # ✓
```

---

### Quick Diagnostic Commands

Run these in order when troubleshooting:

1. **Dependencies**: `uv pip list | grep temporalio`
2. **Syntax**: `python3 -m py_compile your_package/*.py`
3. **Sandbox**: `python3 -c 'from your_package.workflow import YourWorkflow'`
4. **Imports**: `grep "from temporalio.common import RetryPolicy" your_package/workflow.py`
5. **Type checking**: `uv run mypy your_package/ --strict`
6. **Linting**: `uv run ruff check your_package/`

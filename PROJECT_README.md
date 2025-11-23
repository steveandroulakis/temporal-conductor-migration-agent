# Shopping Cart - Temporal Migration

Migrated from Netflix Conductor workflow definition to Temporal Python SDK.

**Original Conductor Workflow**: `conductor-definition/shopping_cart_1.json`
**Migration Date**: November 23, 2025
**Complexity**: HIGH (Max nesting depth: 4)

## Overview

This project implements the **shopping_cart** workflow using Temporal's Python SDK. The workflow was automatically migrated from a Conductor JSON definition.

### Workflow Description

This workflow implements a shopping cart state machine with user interaction at multiple stages. Users can update their cart multiple times before moving to checkout, and the checkout process can succeed or fail, allowing the user to retry.

### Control Flow

This workflow implements:
- 1 DO_WHILE loop with human interaction
- 2 SWITCH statements (one nested within another)
- 1 SUB_WORKFLOW execution (pi_calc_test - placeholder)
- 2 WAIT tasks for human interaction (cart updates and checkout confirmation)
- Multiple SET_VARIABLE tasks for state management
- Human interaction with 2 Update handlers and 1 Query handler

The workflow continues looping until the cart status changes to "checkout", then processes the checkout flow which can either succeed (emptying the cart) or fail (returning to shopping mode).

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
uv sync --all-extras
```

### 2. Start the Worker

In a terminal window:
```bash
uv run worker
```

You should see:
```
Worker ready — polling task queue: shopping-cart-task-queue
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
- Show that the workflow is waiting for human interaction

### 4. Monitor in Web UI

Open the workflow in your browser:
```
http://localhost:8233
```

Navigate to your workflow to see:
- Workflow execution history
- Current status (waiting for cart updates)
- Pending human interactions

## Project Structure

```
shopping_cart_temporal/
├── shopping_cart_temporal/          # Main package directory
│   ├── __init__.py                  # Package marker
│   ├── shared.py                    # Data models (dataclasses)
│   ├── activities.py                # Activity implementations (none in this workflow)
│   ├── workflow.py                  # Workflow definition
│   ├── worker.py                    # Worker registration
│   ├── starter.py                   # Workflow starter
│   └── interact.py                  # Workflow interaction client (Updates/Queries)
├── pyproject.toml                   # Project configuration
├── setup.sh                         # Automated setup script
├── PROJECT_README.md                # This file
├── CONDUCTOR_COMPARISON.md          # Conductor vs Temporal mapping
├── CONDUCTOR_MIGRATION_NOTES.md     # Migration decisions
├── VALIDATION_REPORT.md             # Code validation results
└── WORKFLOW_EXECUTION_REPORT.md     # Execution test results
```

### Module Overview

- **shared.py**: Dataclass definitions for workflow inputs, outputs, and Update handler data
- **activities.py**: No activities in this workflow (pure control flow)
- **workflow.py**: Workflow orchestration with DO_WHILE loop, SWITCH statements, and Update handlers
- **worker.py**: Worker process that executes workflows
- **starter.py**: Client for starting workflow executions
- **interact.py**: Client for interacting with running workflows (Updates/Queries)

## Interacting with Running Workflows

**IMPORTANT**: This workflow has 2 Update handlers and 1 Query handler. You **must** use the `interact.py` client to interact with running workflows.

The `interact.py` script provides a command-line interface for:
- **Updates**: Send validated cart updates and checkout confirmations
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

#### Update: `update_cart`
**Purpose**: Update cart status and items during shopping phase

**Input**: `CartUpdate` with fields:
- `cart` (str): Cart status - must be "shopping" or "checkout"
- `cart_items` (str): Comma-separated list of items

**Example**:
```bash
# Add items to cart
uv run interact update shopping-cart-abc123 update_cart '{
  "cart": "shopping",
  "cart_items": "item1, item2, item3"
}'

# Move to checkout
uv run interact update shopping-cart-abc123 update_cart '{
  "cart": "checkout",
  "cart_items": "item1, item2, item3"
}'
```

**Python equivalent**:
```python
from temporalio.client import Client
from shopping_cart_temporal.shared import CartUpdate

client = await Client.connect("localhost:7233")
handle = client.get_workflow_handle("shopping-cart-abc123")

result = await handle.execute_update(
    "update_cart",
    CartUpdate(cart="shopping", cart_items="item1, item2, item3")
)
print(f"Result: {result}")
```

**Validation**:
- Cart status must be "shopping" or "checkout"
- Cannot send multiple updates in same iteration (must wait for workflow to process)

#### Update: `confirm_checkout`
**Purpose**: Confirm checkout completion after sub-workflow execution

**Input**: `CheckoutConfirmation` with fields:
- `success` (str): Checkout status - "checkout_failed" or any other value for success

**Example**:
```bash
# Confirm successful checkout
uv run interact update shopping-cart-abc123 confirm_checkout '{
  "success": "checkout_success"
}'

# Report failed checkout
uv run interact update shopping-cart-abc123 confirm_checkout '{
  "success": "checkout_failed"
}'
```

**Python equivalent**:
```python
from shopping_cart_temporal.shared import CheckoutConfirmation

result = await handle.execute_update(
    "confirm_checkout",
    CheckoutConfirmation(success="checkout_success")
)
print(f"Result: {result}")
```

**Validation**:
- Can only be sent when cart status is "checkout"
- Cannot send multiple confirmations (must wait for workflow processing)

#### Query: `get_cart_status`
**Purpose**: Check current cart state and workflow status without modifying execution

**Returns**: Dictionary with:
- `status` (str): Workflow status ("shopping", "completed", etc.)
- `cart` (str): Current cart status
- `cart_items` (str): Current items in cart
- `last_cart_items` (str): Previous cart items
- `loop_iteration` (int): Current loop iteration
- `waiting_for_cart_update` (bool): Whether workflow is waiting for cart update
- `waiting_for_checkout_confirmation` (bool): Whether workflow is waiting for checkout confirmation

**Example**:
```bash
uv run interact query shopping-cart-abc123 get_cart_status
```

**Python equivalent**:
```python
status = await handle.query("get_cart_status")
print(f"Status: {status}")
```

### Complete Workflow Example

```bash
# Terminal 1: Start worker
uv run worker

# Terminal 2: Start workflow
uv run starter
# Note the workflow ID from output: shopping-cart-abc123

# Terminal 3: Monitor in Web UI
open http://localhost:8233/namespaces/default/workflows/shopping-cart-abc123

# Terminal 4: Interact with workflow

# Step 1: Check initial status
uv run interact query shopping-cart-abc123 get_cart_status
# Output: {"status": "shopping", "cart": "shopping", "cart_items": "item1, item2, item3", ...}

# Step 2: Update cart (add item)
uv run interact update shopping-cart-abc123 update_cart '{
  "cart": "shopping",
  "cart_items": "item1, item2, item3, item4"
}'

# Step 3: Check status again
uv run interact query shopping-cart-abc123 get_cart_status
# Output shows updated items and loop_iteration: 2

# Step 4: Move to checkout
uv run interact update shopping-cart-abc123 update_cart '{
  "cart": "checkout",
  "cart_items": "item1, item2, item3, item4"
}'

# Step 5: Check status (now waiting for checkout confirmation)
uv run interact query shopping-cart-abc123 get_cart_status
# Output: {"waiting_for_checkout_confirmation": true, ...}

# Step 6: Confirm successful checkout
uv run interact update shopping-cart-abc123 confirm_checkout '{
  "success": "checkout_success"
}'

# Step 7: Workflow completes with empty cart
# Check Web UI - workflow should show COMPLETED status
# Final result: {"cart": "checkout", "cart_items": ""}
```

### Testing Failure Path

```bash
# Start a second workflow
uv run starter
# Note workflow ID: shopping-cart-xyz789

# Move directly to checkout
uv run interact update shopping-cart-xyz789 update_cart '{
  "cart": "checkout",
  "cart_items": "test-item"
}'

# Report failed checkout
uv run interact update shopping-cart-xyz789 confirm_checkout '{
  "success": "checkout_failed"
}'

# Check status - cart should be reset to "shopping"
uv run interact query shopping-cart-xyz789 get_cart_status
# Output: {"cart": "shopping", "cart_items": "test-item", "loop_iteration": 2, ...}

# Workflow continues - can send more cart updates
```

## Configuration

### Workflow Timeouts

The workflow has the following timeout configuration:
- **Cart update timeout**: 24 hours (configurable in workflow.py line 139)
- **Checkout confirmation timeout**: 24 hours (configurable in workflow.py line 208)
- **Execution timeout**: No explicit limit (configured in starter.py)

To adjust timeouts, edit the timeout parameters in `shopping_cart_temporal/workflow.py`:
```python
await workflow.wait_condition(
    lambda: self._cart_update is not None,
    timeout=timedelta(hours=24)  # Modify as needed
)
```

### Loop Safety

The workflow has a safety limit of 100 iterations (line 118 in workflow.py) to prevent infinite loops. Adjust based on expected user behavior:
```python
max_iterations = 100  # Increase if users need more cart updates
```

### Task Queue

The worker and starter use task queue: **shopping-cart-task-queue**

To change the task queue:
1. Update `worker.py`: `task_queue="shopping-cart-task-queue"`
2. Update `starter.py`: `task_queue="shopping-cart-task-queue"`

### Workflow Input

To customize workflow input, edit `shopping_cart_temporal/starter.py`:
```python
workflow_input = WorkflowInput(
    items=["item1", "item2", "item3"]  # Modify these values
)
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

**Error**: `Workflow execution timeout`

**Solution**: This workflow waits for human interaction. It should not time out unless you set an execution_timeout in starter.py. The workflow will wait up to 24 hours for each Update.

---

**Error**: `Update already submitted`

**Solution**: You sent two Updates in the same workflow iteration. Wait for the workflow to process the first Update (check with Query) before sending another.

### Update Handler Errors

**Error**: `Invalid cart status: X`

**Solution**: The `update_cart` handler only accepts "shopping" or "checkout" as cart status values.

---

**Error**: `Cannot confirm checkout - cart status is 'shopping', not 'checkout'`

**Solution**: You tried to send `confirm_checkout` before moving the cart to checkout status. First send `update_cart` with `"cart": "checkout"`.

### Type Checking Issues

To run type checking:
```bash
mypy shopping_cart_temporal --strict --ignore-missing-imports
```

All type checking should pass. See `VALIDATION_REPORT.md` for details.

## Development

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
ruff check shopping_cart_temporal/
```

## Migration Notes

This project was automatically migrated from Conductor. See:
- **CONDUCTOR_COMPARISON.md** - Side-by-side Conductor vs Temporal examples
- **CONDUCTOR_MIGRATION_NOTES.md** - Migration decisions and recommendations
- **WORKFLOW_EXECUTION_REPORT.md** - Execution test results

### Key Differences from Conductor

- **Control Flow**: Conductor DO_WHILE loop → Python while loop with continue-as-new support
- **WAIT Tasks**: Conductor WAIT → Temporal Update handlers with wait_condition
- **SWITCH Statements**: Conductor SWITCH → Python if/elif/else
- **SET_VARIABLE**: Conductor SET_VARIABLE → Python variable assignments
- **SUB_WORKFLOW**: Conductor SUB_WORKFLOW → workflow.execute_child_workflow() (placeholder)
- **INLINE Tasks**: Conductor JavaScript expressions → Python code
- **Data Passing**: Conductor `${workflow.variables.X}` → Python `self._X`
- **Human Interaction**: Conductor WAIT with external data → Temporal Update handlers with validation

### Sub-Workflow Note

The workflow references a sub-workflow `pi_calc_test` that is currently a placeholder (lines 183-189 in workflow.py). This sub-workflow must be migrated separately before the checkout flow can execute completely.

## Additional Resources

- [Temporal Python SDK Documentation](https://docs.temporal.io/develop/python)
- [Temporal Python SDK API Reference](https://python.temporal.io/)
- [Temporal Learning Portal](https://learn.temporal.io/)
- [Conductor to Temporal Migration Guide](./conductor-migration/)

## Support

For migration-specific questions:
- Review `CONDUCTOR_MIGRATION_NOTES.md` for decisions made during migration
- Check `VALIDATION_REPORT.md` for code quality notes
- Review `WORKFLOW_EXECUTION_REPORT.md` for execution test results
- Consult the Conductor migration documentation in `conductor-migration/`

---

**Generated by Conductor to Temporal Migration Tool**
**Migration Date**: November 23, 2025

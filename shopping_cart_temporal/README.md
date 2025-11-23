# shopping_cart_temporal Module Documentation

This module contains the Temporal workflow implementation for the **shopping_cart** workflow, migrated from Netflix Conductor.

## Module Structure

### shared.py
Data models (dataclasses) for workflow and activity inputs/outputs.

**Exports**:
- `WorkflowInput` - Workflow input parameters (initial items)
- `WorkflowOutput` - Workflow output (final cart status and items)
- `CartUpdate` - Cart update data for update_cart Update handler
- `CartUpdateResult` - Result returned from update_cart Update handler
- `CheckoutConfirmation` - Checkout confirmation data for confirm_checkout Update handler
- `CheckoutConfirmationResult` - Result returned from confirm_checkout Update handler

### activities.py
Activity implementations (empty - this workflow has no activities).

**Note**: This workflow consists entirely of control flow primitives (DO_WHILE, SWITCH, SET_VARIABLE, WAIT, SUB_WORKFLOW, INLINE) and does not call any external activities.

### workflow.py
Workflow orchestration with shopping cart state machine.

**Exports**:
- `ShoppingCartWorkflow` - Main workflow class with:
  - `run()` - Workflow execution method
  - `update_cart()` - Update handler for cart modifications
  - `confirm_checkout()` - Update handler for checkout confirmation
  - `get_cart_status()` - Query handler for current cart state

**Control Flow**:
- DO_WHILE loop continues until cart status is "checkout"
- SWITCH statement determines checkout vs shopping path
- Nested SWITCH handles checkout success/failure
- SUB_WORKFLOW placeholder for checkout processing (pi_calc_test)
- Continue-as-new support for long-running carts

**Human Interaction**:
- Two Update handlers receive external input at different workflow phases
- Query handler allows status checking without modification

### worker.py
Worker registration and execution.

**Entry Point**: `worker:main`

**Functionality**:
- Connects to Temporal server at localhost:7233
- Registers ShoppingCartWorkflow
- Polls task queue: shopping-cart-task-queue
- Handles graceful shutdown (Ctrl+C)

### starter.py
Workflow starter client.

**Entry Point**: `starter:main`

**Functionality**:
- Connects to Temporal server at localhost:7233
- Starts workflow with example input: `["item1", "item2", "item3"]`
- Displays workflow ID and Web UI link
- Indicates workflow is waiting for human interaction

### interact.py
Workflow interaction client for Updates and Queries.

**Entry Point**: `interact:main`

**Functionality**:
- Send Updates: `uv run interact update <workflow-id> <update-name> '<json-data>'`
- Execute Queries: `uv run interact query <workflow-id> <query-name>`
- Comprehensive usage documentation

**Available Updates**:
- `update_cart` - Update cart status and items (CartUpdate input)
- `confirm_checkout` - Confirm checkout completion (CheckoutConfirmation input)

**Available Queries**:
- `get_cart_status` - Get current cart state and workflow status

## Usage

See the main project PROJECT_README.md for complete setup and usage instructions.

## Development

When modifying this module:

1. **Maintain strict type hints**: All functions must pass `mypy --strict`
   ```bash
   mypy shopping_cart_temporal --strict --ignore-missing-imports
   ```

2. **Update docstrings**: Keep comprehensive documentation for all public APIs

3. **Run validation**: Check syntax and types before committing
   ```bash
   python3 -m py_compile shopping_cart_temporal/*.py
   mypy shopping_cart_temporal --strict --ignore-missing-imports
   ```

4. **Test with worker and starter**: Ensure changes work end-to-end
   ```bash
   # Terminal 1
   uv run worker

   # Terminal 2
   uv run starter

   # Terminal 3
   uv run interact query <workflow-id> get_cart_status
   ```

## Migration Details

**Original Conductor Workflow**: conductor-definition/shopping_cart_1.json

**Complexity**: HIGH
- Max nesting depth: 4
- DO_WHILE loop with external interaction
- Nested SWITCH statements
- SUB_WORKFLOW execution (placeholder)

**Key Translation Decisions**:
- DO_WHILE → Python while loop with continue-as-new
- WAIT tasks → Update handlers with validation
- SWITCH → Python if/elif/else
- SET_VARIABLE → Python variable assignments
- SUB_WORKFLOW → workflow.execute_child_workflow() (placeholder)

See CONDUCTOR_COMPARISON.md and CONDUCTOR_MIGRATION_NOTES.md for detailed migration information.

---

**Migrated from Conductor workflow**: shopping_cart (version 1)
**Migration Date**: November 23, 2025
**Migration Tool**: Conductor to Temporal Migration Agent (Claude Code)

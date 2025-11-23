# Conductor to Temporal: Comparison Guide

This document shows side-by-side comparisons of how each Conductor task type was translated to Temporal Python code for the shopping_cart workflow.

**Original Conductor Workflow**: `conductor-definition/shopping_cart_1.json`

---

## Workflow Definition

### Conductor (JSON)
```json
{
  "name": "shopping_cart",
  "version": 1,
  "description": "Edit or extend this sample workflow. Set the workflow name to get started",
  "inputParameters": ["items"],
  "outputParameters": {
    "cart": "${workflow.variables.cart}",
    "cart_items": "${workflow.variables.cart_items}"
  }
}
```

### Temporal (Python)
```python
@workflow.defn
class ShoppingCartWorkflow:
    """Shopping cart workflow with human interaction and checkout process.

    This workflow manages a shopping cart lifecycle:
    - User can update cart multiple times
    - User can move to checkout
    - Checkout can succeed or fail (with retry loop)
    - Final cart state is returned
    """

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        # Workflow implementation
        ...
        return WorkflowOutput(
            cart=self._cart,
            cart_items=self._cart_items
        )
```

### Translation Notes
- Conductor JSON structure becomes a Python class with decorator
- Input parameters become a dataclass (WorkflowInput)
- Output parameters become a dataclass (WorkflowOutput)
- Workflow description moves to class docstring
- Variable references `${workflow.variables.X}` become instance attributes `self._X`

---

## Task: cart_creation (SET_VARIABLE)

**Original Conductor Task**: `cart_creation_ref`

### Conductor JSON
```json
{
  "name": "cart_creation",
  "taskReferenceName": "cart_creation_ref",
  "inputParameters": {
    "cart": "shopping",
    "cart_items": "${workflow.input.items}"
  },
  "type": "SET_VARIABLE"
}
```

### Temporal Python
```python
# In workflow.run() method:

# Task: cart_creation (SET_VARIABLE)
# Original: cart_creation_ref
# Initialize shopping cart with workflow input items
self._cart = "shopping"
self._cart_items = ", ".join(input.items) if input.items else ""
workflow.logger.info(f"Cart initialized: cart={self._cart}, items={self._cart_items}")
```

### Translation Notes
- SET_VARIABLE tasks become direct Python variable assignments
- Instance variables (`self._cart`) replace Conductor workflow variables
- Input reference `${workflow.input.items}` becomes `input.items`
- List of items joined into comma-separated string for display
- Added logging for observability

---

## Control Flow Pattern: DO_WHILE Loop

**Original Conductor Task**: `checkout_success_ref`

### Conductor JSON
```json
{
  "name": "checkout_success",
  "taskReferenceName": "checkout_success_ref",
  "type": "DO_WHILE",
  "loopCondition": "if(\"${workflow.variables.cart}\"!=\"checkout\") { true; } else { false; }",
  "loopOver": [
    { "name": "last_cart", ... },
    { "name": "cart_wait", ... },
    { "name": "cart_update", ... },
    { "name": "shopping_checkout", ... }
  ]
}
```

### Temporal Python
```python
# Task: checkout_success (DO_WHILE)
# Original: checkout_success_ref
# Loop until cart status is 'checkout'
self._status = "shopping"
max_iterations = 100  # Prevent infinite loops

while self._cart != "checkout" and self._loop_iteration < max_iterations:
    self._loop_iteration += 1
    workflow.logger.info(f"Shopping loop iteration {self._loop_iteration}")

    # Task: last_cart (SET_VARIABLE)
    self._last_cart_items = self._cart_items

    # Task: cart_wait (WAIT) - see WAIT task section
    # ... wait for update ...

    # Task: cart_update (SET_VARIABLE)
    self._cart = self._cart_update.cart
    self._cart_items = self._cart_update.cart_items

    # Task: shopping_checkout (SWITCH)
    if self._cart == "checkout":
        # ... checkout flow ...
    else:
        # ... continue shopping ...

    # Check if we should suggest continue-as-new
    if workflow.info().is_continue_as_new_suggested():
        workflow.logger.info("Continue-as-new suggested - restarting workflow")
        new_input = WorkflowInput(items=self._cart_items.split(", ") if self._cart_items else [])
        workflow.continue_as_new(new_input)
```

### Translation Notes
- Conductor `loopCondition` string becomes Python `while` condition
- Conductor JavaScript `if(X != "checkout")` becomes Python `while cart != "checkout"`
- Added `max_iterations` safety limit (100) to prevent infinite loops
- `loopOver` tasks become statements inside the while loop body
- Added `continue-as-new` support for long-running loops (prevents history bloat)
- Loop iteration counter for observability

---

## Task: cart_wait (WAIT) - Human Interaction

**Original Conductor Task**: `cart_wait_ref`

### Conductor JSON
```json
{
  "name": "cart_wait",
  "taskReferenceName": "cart_wait_ref",
  "type": "WAIT",
  "inputParameters": {}
}
```

Later referenced as:
```json
{
  "name": "cart_update",
  "inputParameters": {
    "cart": "${cart_wait_ref.output.cart}",
    "cart_items": "${cart_wait_ref.output.cart_items}"
  }
}
```

### Temporal Python

**Workflow Code**:
```python
# Task: cart_wait (WAIT)
# Original: cart_wait_ref (nesting level 1)
# Wait for external cart update from user
workflow.logger.info("Waiting for cart update from user...")
self._cart_update = None  # Reset for new update
await workflow.wait_condition(
    lambda: self._cart_update is not None,
    timeout=timedelta(hours=24)  # Allow 24 hours for user to update
)

workflow.logger.info(f"Cart update received: {self._cart_update}")

# Task: cart_update (SET_VARIABLE) - uses data from WAIT
if self._cart_update is not None:
    self._cart = self._cart_update.cart
    self._cart_items = self._cart_update.cart_items
```

**Update Handler**:
```python
@workflow.update
async def update_cart(self, cart_update: CartUpdate) -> CartUpdateResult:
    """Handle cart update from user.

    This Update handler receives cart updates during the shopping phase.
    It corresponds to the cart_wait_ref WAIT task in Conductor.
    """
    workflow.logger.info(f"Update handler called: update_cart with {cart_update}")

    # Validation: Ensure we're waiting for a cart update
    if self._cart_update is not None:
        raise ApplicationError(
            "Cart update already submitted for this iteration",
            non_retryable=True
        )

    # Validation: Ensure cart status is valid
    valid_statuses = ["shopping", "checkout"]
    if cart_update.cart not in valid_statuses:
        raise ApplicationError(
            f"Invalid cart status: {cart_update.cart}. Must be one of {valid_statuses}",
            non_retryable=True
        )

    # Store the cart update
    self._cart_update = cart_update

    # Return confirmation to caller
    return CartUpdateResult(
        status="accepted",
        message="Cart update received successfully",
        current_cart=cart_update.cart,
        current_items=cart_update.cart_items
    )
```

**Client Interaction**:
```python
# From interact.py
from shopping_cart_temporal.shared import CartUpdate

handle = client.get_workflow_handle(workflow_id)
result = await handle.execute_update(
    "update_cart",
    CartUpdate(cart="shopping", cart_items="item1, item2")
)
```

### Translation Notes
- Conductor WAIT task becomes Temporal Update handler + `wait_condition()`
- Update handler provides validation and immediate feedback (not possible in Conductor)
- `wait_condition()` blocks until Update handler sets `self._cart_update`
- Conductor output references `${cart_wait_ref.output.X}` become `self._cart_update.X`
- Added 24-hour timeout (configurable) vs Conductor's indefinite wait
- Type-safe dataclasses (CartUpdate, CartUpdateResult) vs Conductor's unstructured JSON

---

## Control Flow Pattern: SWITCH Statement

**Original Conductor Task**: `shopping_checkout_ref`

### Conductor JSON
```json
{
  "name": "shopping_checkout",
  "taskReferenceName": "shopping_checkout_ref",
  "type": "SWITCH",
  "inputParameters": {
    "switchCaseValue": "${workflow.variables.cart}"
  },
  "evaluatorType": "value-param",
  "expression": "switchCaseValue",
  "decisionCases": {
    "checkout": [
      { "name": "checkout_task", ... },
      { "name": "checkout_wait", ... },
      { "name": "sample_task_name_switch", ... }
    ]
  },
  "defaultCase": [
    { "name": "sample_task_name_inline", ... }
  ]
}
```

### Temporal Python
```python
# Task: shopping_checkout (SWITCH)
# Original: shopping_checkout_ref (nesting level 1)
# Conditional logic based on cart status

if self._cart == "checkout":
    # SWITCH case: checkout
    # Execute checkout flow with sub-workflow and confirmation
    workflow.logger.info("Cart status is 'checkout' - initiating checkout flow")

    # Task: checkout_task (SUB_WORKFLOW)
    workflow.logger.info("Executing checkout sub-workflow: pi_calc_test")
    # ... sub-workflow execution ...

    # Task: checkout_wait (WAIT)
    workflow.logger.info("Waiting for checkout confirmation...")
    # ... wait for confirmation ...

    # Task: sample_task_name_switch (nested SWITCH)
    if self._checkout_result.success == "checkout_failed":
        # ... handle failure ...
    else:
        # ... handle success ...

else:
    # SWITCH default case: not in checkout mode (still shopping)
    workflow.logger.info(f"Cart status is '{self._cart}' - continuing shopping")

    # Task: sample_task_name_inline (INLINE)
    inline_result = {"someKey": "someValue"}
    workflow.logger.info(f"Inline task result: {inline_result}")
```

### Translation Notes
- Conductor SWITCH with `evaluatorType: value-param` becomes Python `if/elif/else`
- Conductor `switchCaseValue: ${workflow.variables.cart}` becomes `self._cart`
- `decisionCases` map to `if` conditions
- `defaultCase` becomes `else` block
- Tasks in each case become statements in corresponding block
- Nesting preserved (SWITCH can contain other SWITCH statements)

---

## Task: checkout_task (SUB_WORKFLOW)

**Original Conductor Task**: `checkout_task_ref`

### Conductor JSON
```json
{
  "name": "checkout_task",
  "taskReferenceName": "checkout_task_ref",
  "type": "SUB_WORKFLOW",
  "subWorkflowParam": {
    "name": "pi_calc_test",
    "version": 1
  }
}
```

### Temporal Python
```python
# Task: checkout_task (SUB_WORKFLOW)
# Original: checkout_task_ref (nesting level 2)
# Execute checkout sub-workflow
workflow.logger.info("Executing checkout sub-workflow: pi_calc_test")

# Note: The sub-workflow "pi_calc_test" must be migrated separately
# For now, we'll create a placeholder child workflow execution
try:
    # Placeholder for sub-workflow execution
    # TODO: Migrate pi_calc_test workflow and uncomment below
    # child_result = await workflow.execute_child_workflow(
    #     PiCalcTestWorkflow.run,
    #     id=f"{workflow.info().workflow_id}-checkout-{self._loop_iteration}",
    #     task_queue="pi-calc-task-queue",
    #     retry_policy=DEFAULT_RETRY_POLICY
    # )

    # For now, log that sub-workflow would be executed
    workflow.logger.info("Sub-workflow pi_calc_test completed (placeholder)")

except Exception as e:
    workflow.logger.error(f"Sub-workflow failed: {e}")
    raise
```

### Translation Notes
- Conductor SUB_WORKFLOW becomes `workflow.execute_child_workflow()`
- Sub-workflow name reference requires the actual workflow class to be migrated separately
- Child workflow gets unique ID (parent ID + suffix)
- Added retry policy for transient failures
- Sub-workflow runs in same Temporal cluster but separate execution
- Placeholder implementation until pi_calc_test is migrated

---

## Task: checkout_wait (WAIT) - Second Human Interaction

**Original Conductor Task**: `checkout_wait_ref`

### Conductor JSON
```json
{
  "name": "checkout_wait",
  "taskReferenceName": "checkout_wait_ref",
  "type": "WAIT"
}
```

Later referenced as:
```json
{
  "name": "sample_task_name_switch",
  "inputParameters": {
    "switchCaseValue": "${checkout_wait_ref.output.success}"
  }
}
```

### Temporal Python

**Workflow Code**:
```python
# Task: checkout_wait (WAIT)
# Original: checkout_wait_ref (nesting level 2)
# Wait for checkout completion confirmation
workflow.logger.info("Waiting for checkout confirmation...")
self._checkout_result = None  # Reset for new confirmation
await workflow.wait_condition(
    lambda: self._checkout_result is not None,
    timeout=timedelta(hours=24)
)

workflow.logger.info(f"Checkout confirmation received: {self._checkout_result}")

# Use result in nested SWITCH
if self._checkout_result.success == "checkout_failed":
    # ... failure handling ...
```

**Update Handler**:
```python
@workflow.update
async def confirm_checkout(self, confirmation: CheckoutConfirmation) -> CheckoutConfirmationResult:
    """Handle checkout confirmation.

    This Update handler receives checkout completion confirmation after
    the checkout sub-workflow completes.
    """
    workflow.logger.info(f"Update handler called: confirm_checkout with {confirmation}")

    # Validation: Ensure we're waiting for checkout confirmation
    if self._checkout_result is not None:
        raise ApplicationError(
            "Checkout confirmation already submitted",
            non_retryable=True
        )

    # Validation: Ensure we're in checkout phase
    if self._cart != "checkout":
        raise ApplicationError(
            f"Cannot confirm checkout - cart status is '{self._cart}', not 'checkout'",
            non_retryable=True
        )

    # Store the checkout result
    self._checkout_result = confirmation

    return CheckoutConfirmationResult(
        status="accepted",
        message="Checkout confirmation received successfully",
        checkout_status=confirmation.success
    )
```

### Translation Notes
- Second WAIT task becomes second Update handler with different data structure
- Each WAIT task gets its own Update handler name and input type
- Validation ensures Updates arrive in correct workflow phase
- Conductor output reference `${checkout_wait_ref.output.success}` becomes `self._checkout_result.success`

---

## Control Flow Pattern: Nested SWITCH Statement

**Original Conductor Task**: `sample_task_name_vn45m_ref`

### Conductor JSON
```json
{
  "name": "sample_task_name_switch",
  "taskReferenceName": "sample_task_name_vn45m_ref",
  "type": "SWITCH",
  "inputParameters": {
    "switchCaseValue": "${checkout_wait_ref.output.success}"
  },
  "evaluatorType": "value-param",
  "expression": "switchCaseValue",
  "decisionCases": {
    "checkout_failed": [
      {
        "name": "continue_shopping",
        "inputParameters": {
          "cart": "shopping"
        },
        "type": "SET_VARIABLE"
      }
    ]
  },
  "defaultCase": [
    {
      "name": "empty_cart_exit",
      "inputParameters": {
        "cart_items": ""
      },
      "type": "SET_VARIABLE"
    }
  ]
}
```

### Temporal Python
```python
# Task: sample_task_name_switch (SWITCH)
# Original: sample_task_name_vn45m_ref (nesting level 3)
# Nested conditional checking checkout success status

if self._checkout_result is None:
    raise ApplicationError("Checkout result is None after wait_condition", non_retryable=True)

if self._checkout_result.success == "checkout_failed":
    # Nested SWITCH case: checkout_failed
    workflow.logger.info("Checkout failed - resetting to shopping mode")

    # Task: continue_shopping (SET_VARIABLE)
    # Original: continue_shopping_ref (nesting level 4)
    self._cart = "shopping"
    workflow.logger.info("Cart reset to 'shopping' - loop will continue")

else:
    # Nested SWITCH default case: successful checkout
    workflow.logger.info("Checkout successful - clearing cart items")

    # Task: empty_cart_exit (SET_VARIABLE)
    # Original: empty_cart_exit_ref (nesting level 4)
    self._cart_items = ""
    workflow.logger.info("Cart items cleared - loop will exit")
```

### Translation Notes
- Nested SWITCH (inside another SWITCH case) becomes nested if/else
- Nesting level 3 indicates this is inside DO_WHILE > SWITCH > SWITCH
- Failure case resets cart to "shopping" (loop continues)
- Success case clears items but keeps cart="checkout" (loop exits)
- Added None check for type safety

---

## Task: sample_task_name_inline (INLINE)

**Original Conductor Task**: `sample_task_name_skwrs_ref`

### Conductor JSON
```json
{
  "name": "sample_task_name_inline",
  "taskReferenceName": "sample_task_name_skwrs_ref",
  "type": "INLINE",
  "inputParameters": {
    "expression": "({ someKey: 'someValue' })",
    "evaluatorType": "javascript"
  }
}
```

### Temporal Python
```python
# Task: sample_task_name_inline (INLINE)
# Original: sample_task_name_skwrs_ref (nesting level 2)
# Execute inline JavaScript when not in checkout mode
# Conductor expression: "({ someKey: 'someValue' })"

# Translate inline JavaScript to Python equivalent
inline_result = {"someKey": "someValue"}
workflow.logger.info(f"Inline task result: {inline_result}")
# Result is not used downstream, just executed for side effects
```

### Translation Notes
- Conductor INLINE with JavaScript expression becomes direct Python code
- JavaScript object literal `({ key: 'value' })` becomes Python dict `{"key": "value"}`
- This particular inline task has no downstream consumers
- In Conductor, INLINE tasks are evaluated at runtime; in Temporal, they're compiled Python

---

## Query Handler Pattern

**Not present in Conductor** - Temporal enhancement

### Temporal Python
```python
@workflow.query
def get_cart_status(self) -> Dict[str, Any]:
    """Query current cart status without modifying workflow.

    This query allows external systems to check the current state of the
    shopping cart workflow without affecting execution.
    """
    return {
        "status": self._status,
        "cart": self._cart,
        "cart_items": self._cart_items,
        "last_cart_items": self._last_cart_items,
        "loop_iteration": self._loop_iteration,
        "waiting_for_cart_update": self._cart_update is None and self._status == "shopping",
        "waiting_for_checkout_confirmation": self._checkout_result is None and self._cart == "checkout"
    }
```

**Client Interaction**:
```python
# From interact.py
status = await handle.query("get_cart_status")
print(f"Status: {status}")
```

### Translation Notes
- Queries are a Temporal feature not present in Conductor
- Allow read-only access to workflow state without blocking or modifying execution
- Useful for building UIs or monitoring systems
- Multiple queries can be called simultaneously

---

## Data Flow Examples

### Workflow Input Access

**Conductor**:
```json
"inputParameters": {
  "cart_items": "${workflow.input.items}"
}
```

**Temporal**:
```python
self._cart_items = ", ".join(input.items) if input.items else ""
```

### Workflow Variable Access

**Conductor**:
```json
"switchCaseValue": "${workflow.variables.cart}"
```

**Temporal**:
```python
if self._cart == "checkout":
```

### Task Output References

**Conductor**:
```json
"inputParameters": {
  "cart": "${cart_wait_ref.output.cart}",
  "cart_items": "${cart_wait_ref.output.cart_items}"
}
```

**Temporal**:
```python
if self._cart_update is not None:
    self._cart = self._cart_update.cart
    self._cart_items = self._cart_update.cart_items
```

---

## Key Architectural Differences

### 1. Execution Model
- **Conductor**: Poll-based task execution with JSON configuration interpreted at runtime
- **Temporal**: Code-first workflow orchestration with compiled Python, executed deterministically

### 2. Data Passing
- **Conductor**: JSONPath expressions with string templates (`${...}`)
- **Temporal**: Native Python objects with type safety (dataclasses, type hints)

### 3. Control Flow
- **Conductor**: JSON operators (DO_WHILE, SWITCH, loopCondition strings)
- **Temporal**: Native Python constructs (while, if/elif/else, boolean expressions)

### 4. Human Interaction
- **Conductor**: WAIT tasks with manual completion and unstructured output
- **Temporal**: Update handlers with validation, immediate feedback, and type-safe data

### 5. State Management
- **Conductor**: Workflow variables stored in conductor server (`workflow.variables.X`)
- **Temporal**: Instance variables in workflow class (`self._X`)

### 6. Error Handling
- **Conductor**: Configuration-based retries in task definitions
- **Temporal**: Programmatic RetryPolicy objects + Python try/except

### 7. Observability
- **Conductor**: Server-side task status tracking
- **Temporal**: Built-in event history + structured logging + Query handlers

---

## Activity Mapping Table

| Conductor Task | Task Type | Temporal Implementation | Notes |
|----------------|-----------|------------------------|-------|
| cart_creation | SET_VARIABLE | Python variable assignment | `self._cart = "shopping"` |
| checkout_success | DO_WHILE | Python while loop | With continue-as-new support |
| last_cart | SET_VARIABLE | Python variable assignment | `self._last_cart_items = ...` |
| cart_wait | WAIT | Update handler + wait_condition | `update_cart()` handler |
| cart_update | SET_VARIABLE | Python variable assignment | Uses Update handler data |
| shopping_checkout | SWITCH | Python if/else | Conditional branching |
| checkout_task | SUB_WORKFLOW | workflow.execute_child_workflow() | Placeholder (not yet migrated) |
| checkout_wait | WAIT | Update handler + wait_condition | `confirm_checkout()` handler |
| sample_task_name_switch | SWITCH | Python if/else | Nested conditional |
| continue_shopping | SET_VARIABLE | Python variable assignment | Failure path |
| empty_cart_exit | SET_VARIABLE | Python variable assignment | Success path |
| sample_task_name_inline | INLINE | Direct Python code | Dict literal |

---

**This comparison was generated automatically during migration.**
For detailed migration decisions, see `CONDUCTOR_MIGRATION_NOTES.md`.

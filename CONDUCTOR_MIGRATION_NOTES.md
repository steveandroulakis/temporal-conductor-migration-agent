# Conductor to Temporal: Migration Notes

**Migration Date**: November 23, 2025
**Original Workflow**: conductor-definition/shopping_cart_1.json
**Complexity**: HIGH

---

## Migration Overview

This document records the decisions, assumptions, and considerations made during the automatic migration from Conductor to Temporal for the shopping_cart workflow.

## Workflow Characteristics

### Complexity Analysis
- **Max Nesting Depth**: 4 (DO_WHILE > SWITCH > nested tasks > nested SWITCH)
- **Has Loops**: Yes (DO_WHILE loop with external interaction)
- **Has Parallel Execution**: No
- **Has Dynamic Parallelism**: No
- **Has Sub-workflows**: Yes (pi_calc_test - placeholder)

### Task Breakdown
- **Total Tasks**: 12
- **SET_VARIABLE tasks**: 5 → Direct Python variable assignments
- **DO_WHILE tasks**: 1 → Python while loop with continue-as-new
- **WAIT tasks**: 2 → 2 Update handlers (update_cart, confirm_checkout)
- **SWITCH tasks**: 2 → Python if/elif/else statements (one nested)
- **SUB_WORKFLOW tasks**: 1 → workflow.execute_child_workflow() (placeholder)
- **INLINE tasks**: 1 → Direct Python dict literal

**No SIMPLE or HTTP tasks** - This workflow is pure control flow and state management with no external activity execution.

---

## Migration Decisions

### 1. Control Flow Translation

#### DO_WHILE Loop
**Conductor Pattern**:
```json
{
  "type": "DO_WHILE",
  "loopCondition": "if(\"${workflow.variables.cart}\"!=\"checkout\") { true; } else { false; }",
  "loopOver": [...]
}
```

**Decision**: Translated to Python `while` loop with:
- Condition: `while self._cart != "checkout" and self._loop_iteration < max_iterations`
- Safety limit: 100 iterations (prevents infinite loops)
- Continue-as-new support (prevents history bloat in long-running workflows)

**Rationale**:
- Native Python control flow is more readable and maintainable
- Safety limit protects against runaway workflows
- Continue-as-new is critical for loops with many iterations (each cart update = 1 iteration)
- Loop counter provides observability

**Alternative Approaches Considered**:
- Recursive child workflow: More complex, harder to reason about
- No safety limit: Risky for production (could loop forever)
- Fixed timeout instead of iteration limit: User experience depends on timing, not actions

#### SWITCH Statements
**Conductor Pattern**:
```json
{
  "type": "SWITCH",
  "evaluatorType": "value-param",
  "expression": "switchCaseValue",
  "decisionCases": {...},
  "defaultCase": [...]
}
```

**Decision**: Translated to Python `if/elif/else`:
- Single case → `if X == "value": ... else: ...`
- Multiple cases → `if X == "value1": ... elif X == "value2": ... else: ...`
- Nested SWITCH preserved as nested if/else

**Rationale**:
- Python's if/elif/else is semantically equivalent
- More idiomatic and readable than creating switch-like abstractions
- Supports arbitrary expressions (not just value matching)

### 2. Human Interaction Patterns

This workflow has **two distinct human interaction points**, both implemented as WAIT tasks in Conductor:

#### Pattern 1: Cart Updates (cart_wait_ref)
**Conductor Pattern**: WAIT task expecting external data (cart status and items)

**Decision**: Implemented as **Update handler** `update_cart()`

**Rationale**:
- **Validation Required**: Cart status must be "shopping" or "checkout" (finite set of values)
- **Immediate Feedback**: User needs to know if cart update was accepted
- **State Synchronization**: Update handler ensures cart state is consistent before workflow proceeds
- **Multiple Iterations**: User can update cart many times (loop continues until checkout)

**Update Handler Features**:
```python
@workflow.update
async def update_cart(self, cart_update: CartUpdate) -> CartUpdateResult:
    # Validation: cart status must be "shopping" or "checkout"
    if cart_update.cart not in ["shopping", "checkout"]:
        raise ApplicationError(...)

    # Validation: cannot submit duplicate updates
    if self._cart_update is not None:
        raise ApplicationError(...)

    # Return immediate feedback
    return CartUpdateResult(status="accepted", ...)
```

**Alternative Approach**: Signal handler
- Rejected because: No validation, no immediate feedback, fire-and-forget semantics unsuitable for cart state changes

#### Pattern 2: Checkout Confirmation (checkout_wait_ref)
**Conductor Pattern**: WAIT task expecting external data (success status: "checkout_failed" or other)

**Decision**: Implemented as **Update handler** `confirm_checkout()`

**Rationale**:
- **Phase Validation**: Can only confirm checkout when cart status is "checkout"
- **Critical Decision Point**: Determines if workflow completes or loops again
- **Immediate Feedback**: External system needs confirmation that checkout status was recorded
- **Single Occurrence**: Each checkout attempt gets one confirmation (then loop continues or exits)

**Update Handler Features**:
```python
@workflow.update
async def confirm_checkout(self, confirmation: CheckoutConfirmation) -> CheckoutConfirmationResult:
    # Validation: must be in checkout phase
    if self._cart != "checkout":
        raise ApplicationError(...)

    # Validation: cannot submit duplicate confirmations
    if self._checkout_result is not None:
        raise ApplicationError(...)

    # Return immediate feedback
    return CheckoutConfirmationResult(status="accepted", ...)
```

**Alternative Approach**: Signal handler
- Rejected because: No validation of workflow phase, no immediate feedback, could accept confirmations at wrong time

#### Query Handler (Temporal Enhancement)
**Decision**: Added `get_cart_status()` Query handler (not present in Conductor)

**Rationale**:
- Allows external systems to check workflow state without blocking
- Essential for building UIs that show cart contents and status
- Helps users know when to send Updates (e.g., wait until `waiting_for_cart_update: true`)
- Provides observability (loop iteration, current phase, waiting state)

**Alternative Approach**: Polling workflow status via Web UI
- Rejected because: Requires manual inspection, not programmatic

### 3. Data Type Mapping

**Decision**: Created strongly-typed dataclasses for all data structures

**Conductor Input Parameters** → **Temporal Dataclasses**:

| Conductor Field | Type | Temporal Dataclass | Field | Rationale |
|----------------|------|-------------------|-------|-----------|
| `items` (workflow input) | Array | `WorkflowInput` | `items: List[str]` | List of initial cart items |
| `cart` (workflow output) | String | `WorkflowOutput` | `cart: str` | Final cart status |
| `cart_items` (workflow output) | String | `WorkflowOutput` | `cart_items: str` | Final cart items (comma-separated) |
| `cart` (WAIT output) | String | `CartUpdate` | `cart: str` | Cart status from user |
| `cart_items` (WAIT output) | String | `CartUpdate` | `cart_items: str` | Cart items from user |
| `success` (WAIT output) | String | `CheckoutConfirmation` | `success: str` | Checkout status |

**Rationale**:
- Type safety: mypy --strict compliance ensures correct data types
- IDE support: Auto-completion and inline documentation
- Runtime validation: Dataclasses validate field presence
- Self-documenting: Field names and types show intent

**Alternative Approach**: Dict[str, Any]
- Rejected because: No type safety, no IDE support, error-prone

### 4. Sub-Workflow Handling

**Conductor Pattern**:
```json
{
  "type": "SUB_WORKFLOW",
  "subWorkflowParam": {
    "name": "pi_calc_test",
    "version": 1
  }
}
```

**Decision**: Implemented as **placeholder** with `workflow.execute_child_workflow()` commented out

**Rationale**:
- Sub-workflow `pi_calc_test` is a separate Conductor workflow that must be migrated independently
- Placeholder allows workflow to compile and run (skips sub-workflow execution)
- Commented code shows exact Temporal pattern to use once sub-workflow is migrated
- Documented in code comments and TODOs

**Production Implementation** (after sub-workflow migration):
```python
child_result = await workflow.execute_child_workflow(
    PiCalcTestWorkflow.run,
    id=f"{workflow.info().workflow_id}-checkout-{self._loop_iteration}",
    task_queue="pi-calc-task-queue",
    retry_policy=DEFAULT_RETRY_POLICY
)
```

**Alternative Approach**: Create stub workflow class
- Rejected because: Would hide the fact that real implementation is missing

### 5. Timeout Configuration

**Conductor Configuration**:
```json
{
  "timeoutSeconds": 0,
  "timeoutPolicy": "ALERT_ONLY"
}
```

**Decision**: Implemented per-operation timeouts:
- Cart update wait: 24 hours (`timedelta(hours=24)`)
- Checkout confirmation wait: 24 hours (`timedelta(hours=24)`)
- No overall execution timeout

**Rationale**:
- Conductor `timeoutSeconds: 0` means no timeout (indefinite wait)
- 24-hour timeout provides safety net while allowing long user think time
- Separate timeouts for each wait point allow different SLAs
- No execution timeout preserves Conductor behavior (workflow can run indefinitely)

**Alternative Approach**: Short timeouts (e.g., 1 hour)
- Rejected because: Users may need extended time for cart decisions

### 6. Loop Safety

**Decision**: Added 100-iteration safety limit

**Rationale**:
- Prevents infinite loops if logic error occurs
- 100 iterations = 100 cart updates (generous for typical use case)
- Loop counter provides observability
- Fails fast with clear error message if limit reached

**Alternative Approach**: No limit
- Rejected because: Risk of runaway workflow consuming resources

### 7. Continue-As-New

**Decision**: Added `workflow.info().is_continue_as_new_suggested()` check in loop

**Rationale**:
- Temporal workflows store complete event history
- Each loop iteration adds events (Update received, variables updated, etc.)
- Long-running workflows with many iterations can hit history size limits
- Continue-as-new creates new workflow execution with current state, resets history
- Temporal suggests continue-as-new automatically when history grows large

**Implementation**:
```python
if workflow.info().is_continue_as_new_suggested():
    workflow.logger.info("Continue-as-new suggested - restarting workflow")
    new_input = WorkflowInput(items=self._cart_items.split(", ") if self._cart_items else [])
    workflow.continue_as_new(new_input)
```

**Alternative Approach**: No continue-as-new
- Rejected because: Workflow could fail after many iterations due to history size

---

## Assumptions Made

### 1. Conductor Task Implementations

**Assumption**: All Conductor tasks are control flow primitives (SET_VARIABLE, WAIT, SWITCH, etc.) with no external activity execution.

**Impact**: No activities.py implementations needed. Entire workflow is orchestration logic in workflow.py.

**Validation**: Analysis confirmed zero SIMPLE or HTTP tasks.

### 2. Workflow Input Format

**Assumption**: `items` input is an array of strings (e.g., `["item1", "item2", "item3"]`)

**Impact**: Workflow joins items into comma-separated string for internal storage and display.

**Customization Needed**: Update starter.py with actual item format (could be objects with properties, not just strings).

### 3. Cart Status Values

**Assumption**: Cart status has two valid values: "shopping" and "checkout"

**Impact**: Update handler validation rejects other values.

**Validation Source**: Conductor loopCondition checks for "checkout", SET_VARIABLE tasks set "shopping"

**Customization Needed**: If cart has other states (e.g., "abandoned", "expired"), update validation logic.

### 4. Checkout Success Values

**Assumption**: Checkout success field has special value "checkout_failed" for failure, any other value indicates success.

**Impact**: Nested SWITCH checks specifically for "checkout_failed" string, defaultCase handles all other values as success.

**Validation Source**: Conductor decisionCases has single case for "checkout_failed", defaultCase is success path.

**Customization Needed**: If checkout has multiple success/failure codes, update conditional logic.

### 5. Item Format

**Assumption**: Cart items are stored as comma-separated string internally, converted from/to list at workflow boundaries.

**Impact**: Workflow manipulates string, not structured list.

**Rationale**: Conductor SET_VARIABLE tasks store items as single value (likely string).

**Customization Needed**: If items need structured format (quantities, prices, SKUs), change to list of dataclasses.

### 6. Sub-Workflow Purpose

**Assumption**: `pi_calc_test` sub-workflow is the actual checkout processing logic (payment, inventory, etc.)

**Impact**: Placeholder implementation means checkout flow cannot actually execute.

**Next Step**: Migrate `pi_calc_test` workflow separately, then uncomment workflow.execute_child_workflow() code.

### 7. Inline Task Purpose

**Assumption**: INLINE task with `{ someKey: 'someValue' }` is example/placeholder code with no real business logic.

**Impact**: Translated to Python dict literal, result not used downstream.

**Customization Needed**: Replace with actual business logic if this task should do something meaningful.

---

## Known Limitations

### 1. Sub-Workflow Placeholder

**Limitation**: Checkout sub-workflow (`pi_calc_test`) is not implemented.

**Impact**: Workflow can reach checkout phase but cannot execute actual checkout processing.

**Workaround**: Workflow logs placeholder message and continues to checkout confirmation.

**Resolution**: Migrate `pi_calc_test` workflow using same migration tool, update workflow.py to call it.

### 2. No Activity Batching

**Limitation**: N/A (workflow has no activities)

**Impact**: None

### 3. No Comprehensive Tests

**Limitation**: No unit tests or integration tests included.

**Impact**: Manual testing required to verify behavior.

**Recommendation**: Add tests for:
- Update handler validation (invalid cart status, duplicate updates, wrong phase)
- Loop behavior (continue until checkout, reset on failure)
- Continue-as-new trigger
- Query handler responses

### 4. Hardcoded Configuration

**Limitation**: Timeouts (24 hours), max iterations (100), task queue name hardcoded.

**Impact**: Requires code changes to adjust configuration.

**Recommendation**: Move to configuration file or environment variables:
```python
CART_UPDATE_TIMEOUT = timedelta(hours=int(os.environ.get("CART_UPDATE_TIMEOUT_HOURS", "24")))
MAX_LOOP_ITERATIONS = int(os.environ.get("MAX_LOOP_ITERATIONS", "100"))
```

### 5. No Metrics/Monitoring

**Limitation**: No custom metrics emitted (e.g., loop iterations, cart update frequency, checkout success rate).

**Impact**: Limited observability beyond Temporal's built-in metrics.

**Recommendation**: Add workflow metrics:
```python
workflow.metrics.counter("cart_updates_received").inc()
workflow.metrics.histogram("loop_iterations").observe(self._loop_iteration)
```

---

## Customization Recommendations

### Immediate Customizations Needed

#### 1. Workflow Input
**Current**: Example items `["item1", "item2", "item3"]`

**Customize**: Update `starter.py` with realistic cart items:
```python
workflow_input = WorkflowInput(
    items=["SKU-123", "SKU-456", "SKU-789"]  # Real product SKUs
)
```

Or with structured data (requires changing WorkflowInput dataclass):
```python
@dataclass
class CartItem:
    sku: str
    quantity: int
    price_cents: int

@dataclass
class WorkflowInput:
    items: List[CartItem]
```

#### 2. Sub-Workflow Implementation
**Current**: Placeholder (commented out)

**Customize**: Migrate `pi_calc_test` workflow, then:
```python
# Uncomment and update:
child_result = await workflow.execute_child_workflow(
    PiCalcTestWorkflow.run,
    # Pass checkout data
    input=CheckoutInput(
        cart_items=self._cart_items,
        user_id=input.user_id  # Add to WorkflowInput
    ),
    id=f"{workflow.info().workflow_id}-checkout-{self._loop_iteration}",
    task_queue="checkout-task-queue",  # Update queue name
    retry_policy=DEFAULT_RETRY_POLICY
)

# Use result in subsequent logic
if child_result.payment_failed:
    # Handle payment failure
```

#### 3. Cart Status Validation
**Current**: Accepts "shopping" or "checkout" only

**Customize**: Add more states if needed:
```python
valid_statuses = ["shopping", "checkout", "abandoned", "expired"]
```

#### 4. Timeout Configuration
**Current**: 24 hours for all waits

**Customize**: Adjust based on business requirements:
```python
# Shopping phase: longer timeout (users browse)
await workflow.wait_condition(
    lambda: self._cart_update is not None,
    timeout=timedelta(hours=48)  # 2 days
)

# Checkout phase: shorter timeout (payment session expiration)
await workflow.wait_condition(
    lambda: self._checkout_result is not None,
    timeout=timedelta(minutes=30)  # 30 minutes
)
```

#### 5. Inline Task Logic
**Current**: Placeholder dict `{"someKey": "someValue"}`

**Customize**: Replace with actual business logic:
```python
# Example: Log shopping activity
workflow.logger.info(f"User continued shopping, current items: {self._cart_items}")

# Example: Update analytics
inline_result = {
    "event": "cart_updated",
    "timestamp": workflow.now(),  # Note: Use workflow.now() for determinism
    "item_count": len(self._cart_items.split(", "))
}
```

### Optional Enhancements

#### 1. Structured Cart Items
**Enhancement**: Change from comma-separated string to list of structured items

**Benefit**: Type safety, easier to manipulate (add/remove items), richer data (quantities, prices)

**Implementation**:
```python
@dataclass
class CartItem:
    sku: str
    name: str
    quantity: int
    price_cents: int

# In workflow:
self._cart_items: List[CartItem] = []

# In Update handler:
def update_cart(self, cart_update: CartUpdate) -> CartUpdateResult:
    # Validate items
    for item in cart_update.items:
        if item.quantity <= 0:
            raise ApplicationError("Quantity must be positive")

    self._cart_items = cart_update.items
```

#### 2. Cart Update Notifications
**Enhancement**: Send notifications when cart is updated (email, push notification)

**Implementation**: Add activity calls in Update handler or after wait_condition

**Note**: Update handlers cannot call activities directly (Temporal limitation). Workaround:
```python
# In workflow, after cart update:
if self._cart_update is not None:
    # Send notification via activity
    await workflow.execute_activity(
        send_cart_update_notification,
        SendNotificationInput(
            user_id=input.user_id,
            cart_items=self._cart_items
        ),
        start_to_close_timeout=timedelta(seconds=10)
    )
```

#### 3. Checkout Retry Limits
**Enhancement**: Limit number of checkout failures before abandoning cart

**Implementation**:
```python
# Add instance variable
self._checkout_attempts: int = 0
self._max_checkout_attempts: int = 3

# In checkout failure path:
if self._checkout_result.success == "checkout_failed":
    self._checkout_attempts += 1

    if self._checkout_attempts >= self._max_checkout_attempts:
        workflow.logger.warning("Max checkout attempts reached - abandoning cart")
        self._cart = "abandoned"  # Exit loop
    else:
        workflow.logger.info(f"Checkout failed (attempt {self._checkout_attempts}) - resetting to shopping")
        self._cart = "shopping"  # Continue loop
```

#### 4. Cart Expiration
**Enhancement**: Automatically abandon cart after timeout period with no updates

**Implementation**:
```python
# In cart wait:
try:
    await workflow.wait_condition(
        lambda: self._cart_update is not None,
        timeout=timedelta(hours=24)
    )
except asyncio.TimeoutError:
    workflow.logger.warning("Cart expired due to inactivity")
    return WorkflowOutput(
        cart="expired",
        cart_items=""
    )
```

#### 5. Query for Cart Value
**Enhancement**: Add query to calculate total cart value

**Implementation**:
```python
@workflow.query
def get_cart_value(self) -> int:
    """Calculate total cart value in cents."""
    total = 0
    for item in self._cart_items:
        total += item.price_cents * item.quantity
    return total
```

---

## Future Considerations

### 1. Scalability

For high-volume shopping cart workflows (thousands of concurrent users):

- **Worker Scaling**: Run multiple workers across machines to handle load
- **Task Queue Partitioning**: Use user-specific task queues for isolation
- **Continue-As-New**: Already implemented, critical for long-lived carts
- **Temporal Cloud**: Consider managed service for production (auto-scaling, global namespace)

### 2. Human Interaction UI

Build web/mobile interface for cart operations:

- **Frontend**: React/Vue app that calls interact.py logic via REST API
- **Backend API**: Endpoint that wraps Temporal client and execute_update()
- **Real-time Updates**: WebSocket connection that polls query handler for status
- **Error Handling**: Display validation errors from Update handlers to user

Example API endpoint:
```python
@app.post("/cart/{workflow_id}/update")
async def update_cart(workflow_id: str, cart_update: CartUpdate):
    client = await Client.connect("temporal.example.com:7233")
    handle = client.get_workflow_handle(workflow_id)

    try:
        result = await handle.execute_update("update_cart", cart_update)
        return {"success": True, "result": result}
    except ApplicationError as e:
        return {"success": False, "error": str(e)}, 400
```

### 3. Analytics and Reporting

Track cart behavior for business intelligence:

- **Cart Abandonment Rate**: % of carts that reach shopping but never checkout
- **Average Time to Checkout**: Time between workflow start and checkout
- **Checkout Failure Rate**: % of checkout attempts that fail
- **Popular Items**: Most frequently added items

Implementation: Query completed workflows via Temporal visibility API:
```python
async for workflow in client.list_workflows(
    query="WorkflowType='ShoppingCartWorkflow' AND ExecutionStatus='Completed'"
):
    result = await workflow.result()
    # Aggregate metrics
```

### 4. Integration with Payment Systems

Connect to real payment processors (Stripe, PayPal):

- **Sub-Workflow**: Migrate `pi_calc_test` as payment processing workflow
- **Activities**: Create activities for payment API calls (charge card, verify payment)
- **Error Handling**: Retry payment failures with exponential backoff
- **Idempotency**: Use workflow ID as idempotency key to prevent double-charging

### 5. Inventory Management

Ensure items are available before checkout:

- **Activity**: Check inventory levels before allowing checkout
- **Reservation**: Reserve inventory when user moves to checkout (release on failure/timeout)
- **Out-of-Stock Handling**: Update handler rejects checkout if items unavailable

---

## Validation Results Summary

See `VALIDATION_REPORT.md` for detailed validation results.

**Summary**:
- Syntax Validation: PASS (7/7 files)
- Type Checking: PASS (0 errors after fixes)
- Sandbox Compliance: PASS (no sandbox violations)
- Configuration: PASS (pyproject.toml correct)
- Console Scripts: PASS (all synchronous main functions)

**Execution Test Results**:
See `WORKFLOW_EXECUTION_REPORT.md` for detailed execution test results.

**Summary**:
- Worker startup: PASS
- Workflow execution: PASS (COMPLETED status)
- Update handlers: PASS (2/2 tested)
- Query handler: PASS (1/1 tested)
- Execution paths: PASS (success and failure paths validated)
- Workflow task failures: 0

---

## References

- Original Conductor workflow: `conductor-definition/shopping_cart_1.json`
- Conductor Primitives Reference: [conductor-migration/conductor-primitives-reference.md](./conductor-migration/conductor-primitives-reference.md)
- Conductor Human Interaction Guide: [conductor-migration/conductor-human-interaction.md](./conductor-migration/conductor-human-interaction.md)
- Temporal Python SDK: https://docs.temporal.io/develop/python
- Temporal Updates: https://docs.temporal.io/encyclopedia/workflow-message-passing#sending-updates

---

**Migration Tool Version**: 1.0
**Generated**: November 23, 2025
**Pipeline Status**: COMPLETE

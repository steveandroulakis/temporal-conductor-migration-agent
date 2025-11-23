# Conductor to Temporal: Comparison Guide

This document shows side-by-side comparisons of how each Conductor task type was translated to Temporal Python code for this specific workflow.

**Original Conductor Workflow**: `conductor-definition/EXAMPLE_review_approval.json`

---

## Workflow Definition

### Conductor (JSON)
```json
{
  "name": "schema_approval",
  "version": 1,
  "description": "Schema approval workflow with multi-stage review process",
  "inputParameters": [],
  "outputParameters": {},
  "schemaVersion": 2,
  "restartable": true,
  "timeoutPolicy": "ALERT_ONLY",
  "timeoutSeconds": 0
}
```

### Temporal (Python)
```python
@workflow.defn
class SchemaApprovalWorkflow:
    """
    Schema approval workflow with multi-stage review process.
    
    Implements complex control flow with DO_WHILE loop, FORK_JOIN parallel
    execution, 3 SWITCH conditionals, and human interaction via Updates.
    """

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        # Workflow implementation
        ...
```

---

## Task: upload_schema (SIMPLE)

**Original Conductor Task Reference**: `upload_schema`

### Conductor JSON
```json
{
  "name": "upload_schema",
  "taskReferenceName": "upload_schema",
  "inputParameters": {},
  "type": "SIMPLE",
  "optional": false,
  "asyncComplete": false
}
```

### Temporal Python
```python
# Activity definition (activities.py)
@activity.defn
async def upload_schema(input_data: UploadSchemaInput) -> UploadSchemaOutput:
    """Upload schema for review process."""
    activity.logger.info(
        f"Uploading schema {input_data.schema_id} (iteration {input_data.iteration})"
    )
    # Implementation logic here
    return UploadSchemaOutput(...)

# Activity execution (workflow.py)
upload_result = await workflow.execute_activity(
    upload_schema,
    UploadSchemaInput(
        schema_id=input.schema_id,
        schema_content=input.schema_content,
        submitter_id=input.submitter_id,
        iteration=self._iteration,
    ),
    start_to_close_timeout=timedelta(seconds=30),
    retry_policy=DEFAULT_RETRY_POLICY,
)
```

### Translation Notes
- Conductor SIMPLE task → Temporal @activity.defn function
- Conductor inputParameters → Python function arguments (strongly typed)
- Conductor retry configuration → Temporal RetryPolicy object
- Timeout configured via start_to_close_timeout parameter

---

## Task: FORK_JOIN - Parallel Reviews

**Original Conductor Task Reference**: `my_fork_join_ref`

### Conductor JSON
```json
{
  "name": "fork_join",
  "taskReferenceName": "my_fork_join_ref",
  "type": "FORK_JOIN",
  "forkTasks": [
    [
      {
        "name": "Review1.a",
        "taskReferenceName": "Review1.a",
        "type": "SIMPLE"
      }
    ],
    [
      {
        "name": "Review1.b",
        "taskReferenceName": "Review1.b",
        "type": "SIMPLE"
      }
    ]
  ]
}
```

### Temporal Python
```python
# Execute two activities in parallel using asyncio.gather()
review1a_result, review1b_result = await asyncio.gather(
    workflow.execute_activity(
        review_1a,
        args=[input.schema_id, upload_result.upload_id],
        start_to_close_timeout=timedelta(seconds=20),
        retry_policy=DEFAULT_RETRY_POLICY,
    ),
    workflow.execute_activity(
        review_1b,
        args=[input.schema_id, upload_result.upload_id],
        start_to_close_timeout=timedelta(seconds=20),
        retry_policy=DEFAULT_RETRY_POLICY,
    ),
    return_exceptions=False,  # Both must succeed
)
```

### Translation Notes
- Conductor FORK_JOIN → Python `asyncio.gather()`
- Conductor forkTasks array → Multiple activity calls in gather()
- JOIN task (notification_join_ref) is implicit - asyncio.gather() waits for all
- Both tasks must complete successfully (return_exceptions=False)

---

## Task: Review1Check (SWITCH with Human Interaction)

**Original Conductor Task Reference**: `Review1Check`

### Conductor JSON
```json
{
  "name": "Review1Check",
  "taskReferenceName": "Review1Check",
  "type": "SWITCH",
  "inputParameters": {
    "switchCaseValue": "${user_action.output.approved}",
    "expression": "if (both approved) return YES; else return NO;"
  },
  "evaluatorType": "value-param",
  "expression": "switchCaseValue",
  "decisionCases": {
    "YES": [
      { "name": "Review2", "type": "SIMPLE" },
      { "name": "Review2Check", "type": "SWITCH" }
    ],
    "NO": []
  },
  "defaultCase": []
}
```

### Temporal Python
```python
# Update handler for receiving approval (workflow.py)
@workflow.update
async def submit_review1_approval(
    self, decision: ApprovalDecision
) -> ApprovalResult:
    """Handle approval decision from Review1 checkpoint."""
    # Validate decision
    if self._review1_approval is not None:
        raise ApplicationError("Review1 approval already submitted")
    
    # Store decision
    self._review1_approval = decision
    workflow.logger.info(
        f"Review1 approval received: {decision.decision} from {decision.reviewer_id}"
    )
    
    return ApprovalResult(status="accepted", ...)

# Wait for approval and branch (workflow.py)
try:
    await workflow.wait_condition(
        lambda: self._review1_approval is not None,
        timeout=timedelta(hours=24),
    )
except asyncio.TimeoutError:
    # NO case: timeout, continue loop
    continue

# Process approval decision (if/elif logic)
if self._review1_approval.decision == "YES" and self._review1_approval.approved:
    # YES branch: Proceed to Review2
    review2_result = await workflow.execute_activity(review_2, ...)
    # ... Review2Check logic ...
else:
    # NO branch: Loop continues
    continue
```

### Translation Notes
- Conductor SWITCH with `${user_action.output.approved}` → Temporal Update + wait_condition
- Conductor decisionCases → Python if/elif branches
- Human interaction: Update provides validation and immediate feedback
- Timeout handling: 24 hour wait with timeout exception handling
- Empty NO case → Python `continue` (restart loop)

---

## Control Flow Pattern: DO_WHILE Loop

### Conductor JSON
```json
{
  "name": "repeat_until_approved",
  "taskReferenceName": "repeat_until_approved",
  "type": "DO_WHILE",
  "loopCondition": "if ($.approved) { false;} else { true;}",
  "inputParameters": {
    "approved": "${workflow.variables.approved}"
  },
  "loopOver": [
    "upload_schema",
    "my_fork_join_ref",
    "notification_join_ref",
    "Review1Check"
  ]
}
```

### Temporal Python
```python
# DO_WHILE loop translation
max_iterations = 10  # Prevent infinite loops
self._iteration = 0
self._approved = False

# Loop while not approved and under max iterations
while self._iteration < max_iterations and not self._approved:
    self._iteration += 1
    workflow.logger.info(f"Starting approval iteration {self._iteration}")
    
    # Reset approvals for this iteration
    self._review1_approval = None
    self._review2_approval = None
    self._review3_approval = None
    
    # Execute loop body: upload, parallel reviews, approval checks
    upload_result = await workflow.execute_activity(upload_schema, ...)
    review1a_result, review1b_result = await asyncio.gather(...)
    
    # Wait for approval and branch
    await workflow.wait_condition(lambda: self._review1_approval is not None, ...)
    
    if self._review1_approval.approved:
        # Proceed through nested reviews...
        # CompleteReview activities set self._approved = True
        ...
    else:
        # Continue to next iteration
        continue
    
    # Check if continue-as-new needed for large histories
    if workflow.info().is_continue_as_new_suggested():
        workflow.continue_as_new(input)
```

### Translation Notes
- Conductor loopCondition → Python while loop condition
- Conductor workflow variable `$.approved` → Python instance variable `self._approved`
- Max iteration limit added for safety (not in Conductor)
- Continue-as-new used to prevent history bloat (Temporal best practice)
- Loop exits when `self._approved = True` (set by CompleteReview activities)

---

## Control Flow Pattern: Nested SWITCH Statements

### Conductor Structure
```
Review1Check (SWITCH - level 2)
  └─ YES branch
      └─ Review2Check (SWITCH - level 3)
          ├─ YES branch → CompleteReview_1 (level 4)
          └─ NO branch → Review3Check (SWITCH - level 4)
              ├─ YES branch → CompleteReview_2 (level 5)
              └─ NO branch → Continue loop
```

### Temporal Python
```python
# Level 2: Review1Check
if self._review1_approval.decision == "YES" and self._review1_approval.approved:
    # YES branch: Review2
    review2_result = await workflow.execute_activity(review_2, ...)
    
    # Level 3: Review2Check
    await workflow.wait_condition(lambda: self._review2_approval is not None, ...)
    
    if self._review2_approval.decision == "YES" and self._review2_approval.skip_review3:
        # YES branch: Skip Review3 (level 4)
        completion_result = await workflow.execute_activity(
            complete_review_skip_review3, ...
        )
        self._approved = True  # Exit DO_WHILE loop
        return WorkflowOutput(status="approved", ...)
    
    else:
        # NO branch: Proceed to Review3 (level 4)
        review3_result = await workflow.execute_activity(review_3, ...)
        
        # Level 4: Review3Check
        await workflow.wait_condition(lambda: self._review3_approval is not None, ...)
        
        if self._review3_approval.decision == "YES" and self._review3_approval.approved:
            # YES branch: Complete after Review3 (level 5 - max depth)
            completion_result = await workflow.execute_activity(
                complete_review_after_review3, ...
            )
            self._approved = True  # Exit DO_WHILE loop
            return WorkflowOutput(status="approved", ...)
        else:
            # NO branch: Continue loop
            continue
else:
    # NO branch at Review1: Continue loop
    continue
```

### Translation Notes
- Conductor nested SWITCH tasks → Python nested if/elif statements
- Each SWITCH corresponds to one level of if/elif nesting
- Maximum nesting depth: 5 levels (deepest at CompleteReview_2)
- Empty NO cases → Python `continue` statement (restart loop)
- Approval gates use wait_condition with timeout for human interaction

---

## Data Flow Examples

### Workflow Input Access

**Conductor**: `${workflow.input.fieldName}` (not used - inputParameters empty)
**Temporal**: `input.schema_id`, `input.schema_content`, `input.submitter_id`

### Task Output Access

**Conductor**: `${upload_schema.output.upload_id}`
**Temporal**: `upload_result.upload_id`

### Human Interaction Data

**Conductor**: `${user_action.output.approved}`
**Temporal**: `self._review1_approval.approved` (after Update received)

### Workflow Variables

**Conductor**: `${workflow.variables.approved}`
**Temporal**: `self._approved` (instance variable)

---

## Key Architectural Differences

### 1. Execution Model
- **Conductor**: Poll-based task execution with JSON configuration, external task workers
- **Temporal**: Code-first workflow orchestration with Python, workflows and activities in same codebase

### 2. Data Passing
- **Conductor**: JSONPath expressions with string templates (`${...}`)
- **Temporal**: Native Python objects with type safety (dataclasses, mypy --strict)

### 3. Control Flow
- **Conductor**: JSON operators (DO_WHILE, FORK_JOIN, SWITCH, JOIN)
- **Temporal**: Native Python constructs (while, asyncio.gather, if/elif)

### 4. Error Handling
- **Conductor**: Configuration-based retries in task definitions (retryCount, retryLogic)
- **Temporal**: Programmatic RetryPolicy objects per activity

### 5. Human Interaction
- **Conductor**: SWITCH tasks referencing external variables (`${user_action.output.approved}`)
- **Temporal**: Workflow Updates with validation, immediate feedback, and type safety

### 6. State Management
- **Conductor**: Workflow variables stored externally (`.variables.approved`)
- **Temporal**: Instance variables in workflow class (`self._approved`)

### 7. Loop Safety
- **Conductor**: No built-in protection against infinite loops
- **Temporal**: Max iteration limits + continue-as-new for history management

---

## Activity Mapping Table

| Conductor Task | Task Type | Temporal Activity | Arguments | Notes |
|----------------|-----------|-------------------|-----------|-------|
| upload_schema | SIMPLE | upload_schema | UploadSchemaInput | First task in loop |
| Review1.a | SIMPLE | review_1a | schema_id, upload_id | Parallel execution |
| Review1.b | SIMPLE | review_1b | schema_id, upload_id | Parallel execution |
| Review2 | SIMPLE | review_2 | schema_id, review1_results | Sequential after Review1Check |
| Review3 | SIMPLE | review_3 | schema_id, review2_results | Optional, based on Review2Check |
| CompleteReview (ref_1) | SIMPLE | complete_review_skip_review3 | schema_id, review_results, approved | Expedited path |
| CompleteReview (ref_2) | SIMPLE | complete_review_after_review3 | schema_id, review_results, approved | Full review path |

---

## Human Interaction Comparison

### Review1Check Approval

**Conductor Approach**:
```json
{
  "name": "Review1Check",
  "type": "SWITCH",
  "inputParameters": {
    "switchCaseValue": "${user_action.output.approved}"
  },
  "decisionCases": {
    "YES": [...],
    "NO": []
  }
}
```
- External system must update workflow state
- No validation of approval data
- No immediate feedback to approver

**Temporal Approach**:
```python
@workflow.update
async def submit_review1_approval(self, decision: ApprovalDecision) -> ApprovalResult:
    # Validate authorization
    if decision.reviewer_id not in self._authorized_reviewers:
        raise ApplicationError("Unauthorized reviewer")
    
    # Validate state
    if self._review1_approval is not None:
        raise ApplicationError("Approval already submitted")
    
    # Store decision
    self._review1_approval = decision
    
    # Return immediate feedback
    return ApprovalResult(status="accepted", ...)
```
- Built-in validation (authorization, state checks)
- Immediate feedback to approver (ApprovalResult)
- Type-safe decision data (ApprovalDecision dataclass)
- Raises errors for invalid submissions

---

**This comparison was generated automatically during migration.**
For detailed migration decisions, see `CONDUCTOR_MIGRATION_NOTES.md`.

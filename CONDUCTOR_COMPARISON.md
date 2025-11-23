# Conductor to Temporal: Comparison Guide

This document shows side-by-side comparisons of how each Conductor task type was translated to Temporal Python code for the **schema_approval** workflow.

**Original Conductor Workflow**: `conductor-definition/EXAMPLE_review_approval.json`
**Workflow Name**: schema_approval
**Version**: 1
**Complexity**: HIGH (max nesting depth: 5)

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
  "timeoutPolicy": "ALERT_ONLY",
  "timeoutSeconds": 0,
  "restartable": true,
  "workflowStatusListenerEnabled": false,
  "ownerEmail": "manan16489@gmail.com"
}
```

### Temporal (Python)
```python
@workflow.defn
class SchemaApprovalWorkflow:
    """
    Multi-stage schema approval workflow with human review checkpoints.

    This workflow implements a DO_WHILE loop containing a complex approval process
    with parallel reviews, nested conditional checks, and multiple human interaction
    points. The workflow repeats until final approval is achieved.
    """

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        # Workflow implementation
        ...
```

---

## Control Flow Patterns

### Pattern 1: DO_WHILE Loop

**Original Conductor Task Reference**: `repeat_until_approved`

#### Conductor JSON
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
    // ... tasks to repeat ...
  ]
}
```

#### Temporal Python
```python
# DO_WHILE loop: Repeat until approval is received
max_iterations = 10  # Prevent infinite loops
self._iteration = 0

while self._iteration < max_iterations and not self._approved:
    self._iteration += 1
    workflow.logger.info(f"Starting approval loop iteration {self._iteration}")

    # Execute the approval process for this iteration
    await self._execute_approval_iteration(input)

    # Check if continue-as-new is needed for long-running workflows
    if workflow.info().is_continue_as_new_suggested():
        workflow.logger.info("Continue-as-new suggested")
        # workflow.continue_as_new(input)  # Uncomment for production
```

#### Translation Notes
- Conductor's `loopCondition` "if ($.approved) { false;} else { true;}" → Python `while not self._approved`
- Conductor references `${workflow.variables.approved}` → Temporal instance variable `self._approved`
- Added `max_iterations` safety limit (Conductor has no built-in protection against infinite loops)
- Added `continue-as-new` support for workflows that could exceed 100 iterations
- Loop body extracted to helper method `_execute_approval_iteration()` for readability

---

### Pattern 2: FORK_JOIN - Parallel Execution

**Original Conductor Task Reference**: `my_fork_join_ref` + `notification_join_ref`

#### Conductor JSON
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
},
{
  "name": "notification_join",
  "taskReferenceName": "notification_join_ref",
  "type": "JOIN",
  "joinOn": ["Review1.a", "Review1.b"]
}
```

#### Temporal Python
```python
# FORK_JOIN - Parallel execution of Review1.a and Review1.b
review_input_1a = ReviewInput(
    submission_id=input.submission_id,
    schema_data=input.schema_data,
    review_stage="Review1.a",
)
review_input_1b = ReviewInput(
    submission_id=input.submission_id,
    schema_data=input.schema_data,
    review_stage="Review1.b",
)

# Execute both reviews in parallel using asyncio.gather()
# The JOIN task is implicit - gather() waits for all activities to complete
self._review1a_result, self._review1b_result = await asyncio.gather(
    workflow.execute_activity(
        review_1a,
        review_input_1a,
        start_to_close_timeout=timedelta(minutes=5),
        retry_policy=DEFAULT_RETRY_POLICY,
    ),
    workflow.execute_activity(
        review_1b,
        review_input_1b,
        start_to_close_timeout=timedelta(minutes=5),
        retry_policy=DEFAULT_RETRY_POLICY,
    ),
)

workflow.logger.info(
    f"Parallel reviews completed: Review1.a={self._review1a_result.status}, "
    f"Review1.b={self._review1b_result.status}"
)
```

#### Translation Notes
- Conductor FORK_JOIN with 2 branches → Python `asyncio.gather()` with 2 activity executions
- Conductor JOIN task is **implicit** in Temporal - `asyncio.gather()` automatically waits for all parallel tasks
- Results are captured in instance variables for later reference
- Timeouts and retry policies are configured per activity execution

---

### Pattern 3: SWITCH - Conditional Branching with Human Interaction

**Original Conductor Task Reference**: `Review1Check`

#### Conductor JSON
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
      // Tasks to execute if approved
    ]
  },
  "defaultCase": []
}
```

#### Temporal Python
```python
# Review1Check (SWITCH) - Wait for human approval decision
workflow.logger.info("Step 3: Waiting for Review1 approval decision")
self._current_stage = "review1_check"

# Wait for human approval decision with timeout
try:
    await workflow.wait_condition(
        lambda: self._review1_approval is not None,
        timeout=timedelta(hours=24),
    )
except asyncio.TimeoutError:
    workflow.logger.warning("Review1 approval timeout - restarting loop")
    return  # Exit iteration, loop will restart

# Process Review1 approval decision (SWITCH logic)
if self._review1_approval and self._review1_approval.approved:
    workflow.logger.info("Review1Check: YES - Proceeding to Review2")
    # Continue to Review2 (this is the "YES" case)
    await self._execute_review2_branch(input)
else:
    workflow.logger.info("Review1Check: NO - Restarting approval loop")
    # This is the "NO" or default case - loop will restart
    return

# Update handler for receiving approval decision
@workflow.update
async def submit_review1_approval(
    self, decision: ApprovalDecision
) -> ApprovalResult:
    """Handle Review1 approval decision from human reviewer."""

    # Validation: Check if we're at the correct stage
    if self._current_stage != "review1_check":
        raise ApplicationError(
            f"Cannot submit Review1 approval at stage: {self._current_stage}"
        )

    # Validation: Check for duplicate submission
    if self._review1_approval is not None:
        raise ApplicationError("Review1 approval already submitted for this iteration")

    # Store the approval decision
    self._review1_approval = decision

    # Return result to caller
    return ApprovalResult(
        status="accepted",
        message=f"Review1 approval recorded: {'approved' if decision.approved else 'rejected'}",
        reviewer=decision.reviewer_id,
        current_stage="review1_check",
    )
```

#### Translation Notes
- Conductor `${user_action.output.approved}` → Temporal Update handler `submit_review1_approval`
- Conductor external data reference → Temporal `workflow.wait_condition()` + instance variable
- Conductor SWITCH cases (YES/NO) → Python `if/elif/else` statements
- Added timeout (24 hours) for human approvals - Conductor had no timeout
- Update handler provides validation, stores decision, and returns immediate feedback
- Conductor evaluatorType "value-param" → Temporal simple boolean evaluation

---

### Pattern 4: Nested SWITCH Statements

**Original Conductor Task Reference**: `Review2Check` (nested within `Review1Check`)

#### Conductor JSON
```json
{
  "name": "Review2Check",
  "taskReferenceName": "Review2Check",
  "type": "SWITCH",
  "inputParameters": {
    "switchCaseValue": "${user_action.output.approved}",
    "expression": "if (skippReview3) return YES; else return NO;"
  },
  "evaluatorType": "value-param",
  "expression": "switchCaseValue",
  "decisionCases": {
    "YES": [
      {
        "name": "CompleteReview",
        "taskReferenceName": "CompleteReview_1",
        "type": "SIMPLE"
      }
    ],
    "NO": [
      {
        "name": "Review3",
        "taskReferenceName": "Review3",
        "type": "SIMPLE"
      },
      {
        "name": "Review3Check",
        "taskReferenceName": "Review3Check",
        "type": "SWITCH"
      }
    ]
  }
}
```

#### Temporal Python
```python
# Review2Check (SWITCH) - nested within Review1Check YES branch
workflow.logger.info("Step 5: Waiting for Review2 approval decision")
self._current_stage = "review2_check"

# Wait for human approval decision with timeout
try:
    await workflow.wait_condition(
        lambda: self._review2_approval is not None,
        timeout=timedelta(hours=24),
    )
except asyncio.TimeoutError:
    workflow.logger.warning("Review2 approval timeout - restarting loop")
    return

# Process Review2 approval decision (SWITCH logic)
if self._review2_approval and self._review2_approval.skip_review3:
    # YES case: Skip Review3, go to CompleteReview_1
    workflow.logger.info("Review2Check: YES (skip Review3) - Completing review")
    await self._execute_complete_review(
        input,
        approval_decisions={
            "Review1": self._review1_approval.approved if self._review1_approval else False,
            "Review2": self._review2_approval.approved if self._review2_approval else False,
            "Review3": "skipped",
        },
        final_approval=True,
    )
else:
    # NO case: Do not skip Review3, continue to Review3 branch
    workflow.logger.info("Review2Check: NO (requires Review3) - Proceeding to Review3")
    await self._execute_review3_branch(input)

# Update handler with skip_review3 flag
@workflow.update
async def submit_review2_approval(
    self, decision: ApprovalDecision
) -> ApprovalResult:
    """Handle Review2 approval decision from human reviewer."""

    workflow.logger.info(
        f"Received Review2 approval from {decision.reviewer_id}: "
        f"approved={decision.approved}, skip_review3={decision.skip_review3}"
    )

    # Validation...
    self._review2_approval = decision

    # Return result indicating next stage
    next_stage = "complete" if decision.skip_review3 else "review3"
    return ApprovalResult(
        status="accepted",
        message=f"Review2 approval recorded. Next: {next_stage}",
        reviewer=decision.reviewer_id,
        current_stage="review2_check",
    )
```

#### Translation Notes
- Nested SWITCH → Nested if/else statements in separate helper methods
- `skip_review3` flag in ApprovalDecision dataclass controls branching
- Two exit paths: CompleteReview_1 (skip Review3) or Review3 branch (require Review3)
- Helper methods `_execute_complete_review()` and `_execute_review3_branch()` improve readability
- Maximum nesting depth of 5 handled through method extraction

---

## Task Type Mappings

### Task 1: upload_schema (SIMPLE)

**Conductor Task**:
```json
{
  "name": "upload_schema",
  "taskReferenceName": "upload_schema",
  "type": "SIMPLE",
  "inputParameters": {}
}
```

**Temporal Activity**:
```python
@activity.defn
async def upload_schema(input_data: UploadSchemaInput) -> str:
    """Upload schema for review.

    Activity migrated from Conductor SIMPLE task: upload_schema
    This is the first task in the approval loop, executed at the start
    of each iteration.
    """
    activity.logger.info(
        f"Uploading schema for submission {input_data.submission_id} "
        f"(iteration {input_data.iteration})"
    )

    # TODO: Implement actual schema upload logic
    upload_message = (
        f"Schema uploaded successfully for submission {input_data.submission_id} "
        f"(iteration {input_data.iteration}). "
        f"Schema contains {len(input_data.schema_data)} fields."
    )

    activity.logger.info(f"Upload complete: {upload_message}")
    return upload_message
```

**Workflow Execution**:
```python
upload_message = await workflow.execute_activity(
    upload_schema,
    UploadSchemaInput(
        submission_id=input.submission_id,
        schema_data=input.schema_data,
        iteration=self._iteration,
    ),
    start_to_close_timeout=timedelta(seconds=30),
    retry_policy=DEFAULT_RETRY_POLICY,
)
```

**Translation Notes**:
- Conductor SIMPLE task → Temporal `@activity.defn` function
- No input parameters in Conductor → Created type-safe UploadSchemaInput dataclass
- Conductor had no timeout → Added 30 second timeout
- Added retry policy with 3 attempts and exponential backoff

---

### Task 2: Review1.a and Review1.b (SIMPLE, parallel)

**Conductor Tasks**:
```json
// Part of FORK_JOIN
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
```

**Temporal Activities**:
```python
@activity.defn
async def review_1a(input_data: ReviewInput) -> ReviewOutput:
    """First parallel review task (Review1.a).

    Activity migrated from Conductor SIMPLE task: Review1.a
    Part of FORK_JOIN parallel execution with Review1.b.
    """
    activity.logger.info(f"Starting Review1.a for submission {input_data.submission_id}")

    # TODO: Implement actual review logic
    review_output = ReviewOutput(
        reviewer_id="reviewer_1a",
        review_stage="Review1.a",
        status="reviewed",
        timestamp=datetime.utcnow(),
        comments="Schema structure validated by Review1.a",
    )

    return review_output

@activity.defn
async def review_1b(input_data: ReviewInput) -> ReviewOutput:
    """Second parallel review task (Review1.b).

    Activity migrated from Conductor SIMPLE task: Review1.b
    Part of FORK_JOIN parallel execution with Review1.a.
    """
    activity.logger.info(f"Starting Review1.b for submission {input_data.submission_id}")

    # TODO: Implement actual review logic
    review_output = ReviewOutput(
        reviewer_id="reviewer_1b",
        review_stage="Review1.b",
        status="reviewed",
        timestamp=datetime.utcnow(),
        comments="Schema semantics validated by Review1.b",
    )

    return review_output
```

**Translation Notes**:
- Two separate activity functions with similar structure
- Both use same ReviewInput dataclass, differentiated by `review_stage` field
- Returns ReviewOutput with reviewer-specific results
- Executed in parallel using `asyncio.gather()` (see FORK_JOIN pattern above)
- 5 minute timeout for each review activity

---

### Task 3: CompleteReview (SIMPLE, appears twice)

**Conductor Tasks**:
```json
// CompleteReview_1 - after Review2Check = YES
{
  "name": "CompleteReview",
  "taskReferenceName": "CompleteReview_1",
  "type": "SIMPLE"
}

// CompleteReview_2 - after Review3Check = YES
{
  "name": "CompleteReview",
  "taskReferenceName": "CompleteReview_2",
  "type": "SIMPLE"
}
```

**Temporal Activity** (shared):
```python
@activity.defn
async def complete_review(input_data: CompleteReviewInput) -> CompleteReviewOutput:
    """Complete the review process and finalize approval.

    Activity migrated from Conductor SIMPLE task: CompleteReview
    This task appears twice in Conductor workflow (CompleteReview_1, CompleteReview_2)
    but implements the same logic - finalizing the approval process.

    Execution paths:
    - CompleteReview_1: Executed when Review2Check = YES (Review3 skipped)
    - CompleteReview_2: Executed when Review3Check = YES (after Review3 approval)
    """
    activity.logger.info(
        f"Completing review for submission {input_data.submission_id} "
        f"with final_approval={input_data.final_approval}"
    )

    # TODO: Implement actual completion logic
    status = "approved" if input_data.final_approval else "rejected"
    message = f"Schema review process completed. Final decision: {status}"

    return CompleteReviewOutput(
        status=status,
        message=message,
        timestamp=datetime.utcnow(),
    )
```

**Workflow Execution** (two call sites):
```python
# Call site 1: CompleteReview_1 (skip Review3)
await self._execute_complete_review(
    input,
    approval_decisions={
        "Review1": self._review1_approval.approved,
        "Review2": self._review2_approval.approved,
        "Review3": "skipped",
    },
    final_approval=True,
)

# Call site 2: CompleteReview_2 (after Review3)
await self._execute_complete_review(
    input,
    approval_decisions={
        "Review1": self._review1_approval.approved,
        "Review2": self._review2_approval.approved,
        "Review3": self._review3_approval.approved,
    },
    final_approval=True,
)

# Helper method that calls the activity
async def _execute_complete_review(
    self, input: WorkflowInput, approval_decisions: Dict[str, Any], final_approval: bool
) -> None:
    complete_result = await workflow.execute_activity(
        complete_review,
        CompleteReviewInput(
            submission_id=input.submission_id,
            approval_decisions=approval_decisions,
            final_approval=final_approval,
        ),
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=RetryPolicy(maximum_attempts=5),  # Higher retry for critical step
    )

    # Set approval flag to exit DO_WHILE loop
    self._approved = final_approval
```

**Translation Notes**:
- Conductor has two task references but same task name → Temporal has single activity implementation
- Called from two different code paths (Review2Check YES, Review3Check YES)
- Activity sets `self._approved = True` to exit DO_WHILE loop
- Higher retry policy (5 attempts) for this critical completion step
- Captures all approval decisions from Review1, Review2, and Review3

---

## Data Flow Examples

### Workflow Input Access

**Conductor**: `${workflow.input.fieldName}`
**Temporal**: `input.field_name`

Example:
```python
# Conductor JSON
"inputParameters": {
  "submission": "${workflow.input.submission_id}"
}

# Temporal Python
UploadSchemaInput(
    submission_id=input.submission_id
)
```

### Task Output Access

**Conductor**: `${taskRef.output.result}`
**Temporal**: `task_ref_result.result`

Example:
```python
# Store activity result
self._review1a_result = await workflow.execute_activity(review_1a, ...)

# Access later
previous_reviews={
    "Review1.a": {
        "status": self._review1a_result.status
    }
}
```

### Human Interaction Data

**Conductor**: `${user_action.output.approved}`
**Temporal**: `self._review1_approval.approved`

Example:
```python
# Conductor SWITCH condition
"switchCaseValue": "${user_action.output.approved}"

# Temporal workflow code
if self._review1_approval and self._review1_approval.approved:
    # YES case
    await self._execute_review2_branch(input)
else:
    # NO case
    return
```

### Workflow Variables

**Conductor**: `${workflow.variables.approved}`
**Temporal**: `self._approved`

Example:
```python
# Conductor loop condition
"loopCondition": "if ($.approved) { false;} else { true;}"

# Temporal while loop
while self._iteration < max_iterations and not self._approved:
    # Loop body
```

---

## Key Architectural Differences

### 1. Execution Model
- **Conductor**: Poll-based task execution with JSON configuration
- **Temporal**: Code-first workflow orchestration with Python

### 2. Data Passing
- **Conductor**: JSONPath expressions with string templates (`${...}`)
- **Temporal**: Native Python objects with type safety (dataclasses)

### 3. Control Flow
- **Conductor**: JSON operators (DO_WHILE, FORK_JOIN, SWITCH, JOIN)
- **Temporal**: Native Python constructs (while, asyncio.gather, if/elif)

### 4. Error Handling
- **Conductor**: Configuration-based retries in task definitions
- **Temporal**: Programmatic RetryPolicy objects per activity

### 5. Human Interaction
- **Conductor**: SWITCH tasks waiting for external data (`${user_action.output}`)
- **Temporal**: Update handlers with `workflow.wait_condition()` and validation

### 6. Loop Management
- **Conductor**: No built-in protection against infinite loops
- **Temporal**: Added `max_iterations` limit and `continue-as-new` support

---

## Activity Mapping Table

| Conductor Task | Task Type | Reference Name | Temporal Activity | Timeout | Notes |
|----------------|-----------|----------------|-------------------|---------|-------|
| upload_schema | SIMPLE | upload_schema | upload_schema | 30s | First task in loop |
| Review1.a | SIMPLE | Review1.a | review_1a | 5m | Parallel with Review1.b |
| Review1.b | SIMPLE | Review1.b | review_1b | 5m | Parallel with Review1.a |
| Review2 | SIMPLE | Review2 | review_2 | 10m | Conditional on Review1Check |
| Review3 | SIMPLE | Review3 | review_3 | 15m | Conditional on Review2Check |
| CompleteReview | SIMPLE | CompleteReview_1 | complete_review | 30s | Two call sites |
| CompleteReview | SIMPLE | CompleteReview_2 | complete_review | 30s | Same activity |
| fork_join | FORK_JOIN | my_fork_join_ref | asyncio.gather() | N/A | Parallel execution |
| notification_join | JOIN | notification_join_ref | (implicit) | N/A | Implicit in gather() |
| Review1Check | SWITCH | Review1Check | if/elif + Update | 24h | Human approval |
| Review2Check | SWITCH | Review2Check | if/elif + Update | 24h | Human approval |
| Review3Check | SWITCH | Review3Check | if/elif + Update | 24h | Human approval |
| repeat_until_approved | DO_WHILE | repeat_until_approved | while loop | N/A | Max 10 iterations |

---

## Query and Update Handlers

### Query: get_status

**Purpose**: Check current workflow status without modifying state

**Implementation**:
```python
@workflow.query
def get_status(self) -> Dict[str, Any]:
    """Query current workflow status and review stage."""
    return {
        "current_stage": self._current_stage,
        "iteration": self._iteration,
        "approved": self._approved,
        "review1_status": {
            "review1a_completed": self._review1a_result is not None,
            "review1b_completed": self._review1b_result is not None,
            "approval_received": self._review1_approval is not None,
            "approved": self._review1_approval.approved if self._review1_approval else None,
        },
        # ... more status details
    }
```

**Usage**:
```bash
uv run interact query <workflow-id> get_status
```

### Update: submit_review1_approval

**Conductor Pattern**: `${user_action.output.approved}` in Review1Check SWITCH

**Temporal Implementation**:
```python
@workflow.update
async def submit_review1_approval(self, decision: ApprovalDecision) -> ApprovalResult:
    """Handle Review1 approval decision from human reviewer."""

    # Validation
    if self._current_stage != "review1_check":
        raise ApplicationError(f"Cannot submit Review1 approval at stage: {self._current_stage}")

    if self._review1_approval is not None:
        raise ApplicationError("Review1 approval already submitted")

    # Store decision
    self._review1_approval = decision

    # Return immediate feedback
    return ApprovalResult(
        status="accepted",
        message=f"Review1 approval recorded: {'approved' if decision.approved else 'rejected'}",
        reviewer=decision.reviewer_id,
        current_stage="review1_check",
    )
```

**Usage**:
```bash
uv run interact update <workflow-id> submit_review1_approval \
  '{"reviewer_id": "user@example.com", "approved": true}'
```

---

**This comparison was generated automatically during migration.**
For detailed migration decisions, see `CONDUCTOR_MIGRATION_NOTES.md`.

**Generated by**: documentation-generator agent (Agent 7)
**Migration Date**: November 23, 2025

# Conductor to Temporal: Migration Notes

**Migration Date**: 2025-11-23
**Original Workflow**: conductor-definition/EXAMPLE_review_approval.json
**Complexity**: high

---

## Migration Overview

This document records the decisions, assumptions, and considerations made during the automatic migration from Conductor to Temporal.

## Workflow Characteristics

### Complexity Analysis
- **Max Nesting Depth**: 5 levels
- **Has Loops**: Yes (DO_WHILE loop)
- **Has Parallel Execution**: Yes (FORK_JOIN with 2 branches)
- **Has Dynamic Parallelism**: No
- **Has Sub-workflows**: No
- **Total Tasks**: 11 (including JOIN and SWITCH tasks)
- **SIMPLE tasks**: 7 → 7 activities

### Task Breakdown
- **SIMPLE tasks**: 7 (upload_schema, Review1.a, Review1.b, Review2, Review3, CompleteReview x2)
- **FORK_JOIN tasks**: 1 (parallel Review1.a and Review1.b)
- **JOIN tasks**: 1 (implicit in asyncio.gather)
- **SWITCH tasks**: 3 (Review1Check, Review2Check, Review3Check)
- **DO_WHILE tasks**: 1 (repeat_until_approved)

---

## Migration Decisions

### 1. Control Flow Translation

#### DO_WHILE Loop
**Decision**: Translated to Python while loop with iteration counter and max limit

**Conductor Pattern**:
```json
{
  "type": "DO_WHILE",
  "loopCondition": "if ($.approved) { false;} else { true;}",
  "loopOver": [...]
}
```

**Temporal Implementation**:
```python
max_iterations = 10
while self._iteration < max_iterations and not self._approved:
    self._iteration += 1
    # Loop body
    ...
```

**Rationale**: 
- Added max_iterations (10) for safety - Conductor had no limit
- Used instance variable `self._approved` instead of Conductor's workflow variable
- Implemented continue-as-new for large iteration counts (history management)

**Alternative Approaches**:
- Could use recursive workflow with continue-as-new from start
- Could implement as separate sub-workflow per iteration
- Chose while loop for clarity and simplicity

#### FORK_JOIN - Parallel Reviews
**Decision**: Translated to `asyncio.gather()` with two parallel activity calls

**Conductor Pattern**:
```json
{
  "type": "FORK_JOIN",
  "forkTasks": [["Review1.a"], ["Review1.b"]]
}
```

**Temporal Implementation**:
```python
review1a_result, review1b_result = await asyncio.gather(
    workflow.execute_activity(review_1a, ...),
    workflow.execute_activity(review_1b, ...),
    return_exceptions=False
)
```

**Rationale**:
- asyncio.gather() provides native Python parallelism
- return_exceptions=False ensures both must succeed
- JOIN task becomes implicit (gather waits for all)

#### SWITCH - Conditional Branching
**Decision**: Translated to Python if/elif statements with wait_condition for human interaction

**Conductor Pattern**:
```json
{
  "type": "SWITCH",
  "inputParameters": {"switchCaseValue": "${user_action.output.approved}"},
  "decisionCases": {"YES": [...], "NO": []}
}
```

**Temporal Implementation**:
```python
await workflow.wait_condition(
    lambda: self._review1_approval is not None,
    timeout=timedelta(hours=24)
)

if self._review1_approval.decision == "YES" and self._review1_approval.approved:
    # YES branch
    ...
else:
    # NO branch
    continue
```

**Rationale**:
- wait_condition provides clean blocking until approval received
- if/elif provides clear branching logic
- Added timeout (24 hours) for safety
- Empty NO cases translated to `continue` (restart loop)

### 2. Human Interaction Patterns

#### Review1Check, Review2Check, Review3Check
**Conductor Pattern**: SWITCH tasks referencing `${user_action.output.approved}`

**Temporal Mechanism**: Workflow Updates

**Decision Rationale**:
- **Why Updates over Signals**: 
  - Updates provide validation before accepting data
  - Updates return immediate feedback to caller (ApprovalResult)
  - Updates ensure data integrity (can't submit duplicate approvals)
  - Signals would allow invalid submissions without validation

**Decision Criteria Met**:
- Validation required: Check reviewer authorization, check state
- Return value needed: ApprovalResult with status and message
- Atomicity: Each approval is atomic operation

**Implementation Pattern**:
```python
@workflow.update
async def submit_review1_approval(self, decision: ApprovalDecision) -> ApprovalResult:
    # Validate authorization
    if decision.reviewer_id not in self._authorized_reviewers:
        raise ApplicationError("Unauthorized reviewer")
    
    # Validate state
    if self._review1_approval is not None:
        raise ApplicationError("Approval already submitted")
    
    # Store and return result
    self._review1_approval = decision
    return ApprovalResult(status="accepted", ...)
```

**Timeout Handling**:
- Each approval gate has 24-hour timeout
- Timeout → loop continues (treated as rejection)
- Logged for audit trail

#### Approval Loop Pattern
**Conductor Pattern**: DO_WHILE loop checking `${workflow.variables.approved}`

**Temporal Mechanism**: Instance variable `self._approved` set by CompleteReview activities

**Decision Rationale**:
- CompleteReview activities set `self._approved = True` to exit loop
- Loop continues until approval or max iterations
- Each iteration resets approval variables for clean state

### 3. Activity Design

**Decision**: Created 7 activities from Conductor SIMPLE tasks

**Activity Function Signatures**:
- upload_schema: 1 argument (UploadSchemaInput dataclass)
- review_1a, review_1b: 2 arguments (schema_id, upload_id)
- review_2: 2 arguments (schema_id, review1_results dict)
- review_3: 2 arguments (schema_id, review2_results dict)
- complete_review_skip_review3: 3 arguments (schema_id, review_results, approved)
- complete_review_after_review3: 3 arguments (schema_id, review_results, approved)

**Activity Timeout Strategy**:
- upload_schema: 30 seconds (may involve file I/O)
- review activities: 20-30 seconds (review processing)
- complete activities: 20 seconds (finalization)

**Retry Policy Strategy**:
- All activities use DEFAULT_RETRY_POLICY:
  - initial_interval: 1 second
  - maximum_interval: 100 seconds
  - maximum_attempts: 3
  - backoff_coefficient: 2.0
- Suitable for transient failures (network, temporary unavailability)

### 4. Data Type Mapping

**Conductor Input Parameters** → **Temporal Dataclasses**

Conductor workflow had empty inputParameters. Created sensible structure:

- `WorkflowInput`:
  - `schema_id: str` - Schema identifier
  - `schema_content: Dict[str, Any]` - Schema data
  - `submitter_id: str` - Submitter identifier
  - `priority: int = 1` - Priority level (default 1)
  - `metadata: Optional[Dict[str, Any]] = None` - Additional metadata

- `ApprovalDecision`:
  - `reviewer_id: str` - Reviewer identifier
  - `approved: bool` - Approval flag
  - `decision: str` - "YES" or "NO" matching Conductor SWITCH cases
  - `stage: str` - Approval stage identifier
  - `skip_review3: bool = False` - For Review2Check expedited path
  - `comments: Optional[str] = None` - Review comments

**Rationale**:
- Strong typing for mypy --strict compliance
- Explicit field types prevent runtime errors
- Optional fields with defaults for flexibility
- decision field matches Conductor SWITCH case names exactly

---

## Assumptions Made

1. **Activity Implementations**: Activity functions contain placeholder implementations marked with TODO comments. These need to be filled in with actual business logic based on the original Conductor task implementations.

2. **Timeout Values**: Activity timeouts (20-30 seconds) were chosen based on typical activity execution times. Adjust based on actual performance requirements.

3. **Example Input Data**: The starter.py generates example input data:
   ```python
   schema_id="example-schema-001"
   schema_content={"type": "object", "properties": {...}}
   submitter_id="user-123"
   ```
   These should be customized for your specific use case.

4. **Authorized Reviewers**: The workflow includes a hardcoded set of authorized reviewers:
   ```python
   self._authorized_reviewers = {
       "reviewer-1a",
       "reviewer-1b",
       "reviewer-2",
       "reviewer-3",
   }
   ```
   This should be replaced with actual authorization logic (database lookup, IAM integration, etc.)

5. **CompleteReview Logic**: The Conductor JSON doesn't explicitly show how the `approved` workflow variable is set. Assumed that CompleteReview activities set this variable to exit the loop.

6. **Approval Timeout**: 24-hour timeout for each approval gate was chosen as reasonable default. Adjust based on your approval SLA requirements.

7. **Max Iterations**: Limited DO_WHILE loop to 10 iterations to prevent infinite loops. Conductor had no such limit.

---

## Known Limitations

1. **Empty Conductor Input**: The original Conductor workflow has empty inputParameters array. Created WorkflowInput structure based on common schema approval use cases.

2. **Workflow Variable Mystery**: Conductor references `${workflow.variables.approved}` but doesn't show where this variable is set. Implemented as instance variable set by CompleteReview activities.

3. **Review Logic**: The Conductor JSON doesn't specify what "both approved" means for Review1Check. Assumed it means both Review1.a and Review1.b completed successfully.

4. **SkipReview3 Logic**: Review2Check expression mentions "skipReview3" but doesn't define the business rule. Implemented as boolean field in ApprovalDecision that reviewer sets.

5. **No Sub-task Details**: Conductor SIMPLE tasks have empty inputParameters. Created sensible parameter structures based on task names and dependencies.

---

## Customization Recommendations

### Immediate Customizations Needed

1. **Activity Implementations**: Review all TODO comments in `schema_approval_temporal/activities.py` and implement actual business logic:
   ```python
   # TODO: Implement actual schema upload logic
   # Replace with your upload logic:
   # - Validate schema content
   # - Store schema in repository/database
   # - Generate upload ID
   ```

2. **Workflow Input**: Update example data in `schema_approval_temporal/starter.py` to match your use case:
   ```python
   workflow_input = WorkflowInput(
       schema_id="your-real-schema-id",
       schema_content=your_actual_schema_data,
       submitter_id=authenticated_user_id,
       ...
   )
   ```

3. **Timeout Configuration**: Review and adjust timeouts based on your activity performance:
   ```python
   # In workflow.py
   start_to_close_timeout=timedelta(seconds=X)  # Adjust based on testing
   ```

4. **Reviewer Authorization**: Replace hardcoded reviewer set with actual authorization:
   ```python
   # Query from database, check IAM roles, etc.
   authorized_reviewers = await get_authorized_reviewers_for_schema(schema_id)
   ```

### Optional Enhancements

1. **Error Handling**: Add specific exception handling for business logic failures:
   ```python
   try:
       upload_result = await workflow.execute_activity(upload_schema, ...)
   except ActivityError as e:
       # Handle upload failure
       workflow.logger.error(f"Upload failed: {e}")
       # Decide whether to retry or fail workflow
   ```

2. **Logging**: Enhance logging with additional context for debugging:
   ```python
   activity.logger.info(
       "Review1.a starting",
       extra={
           "schema_id": schema_id,
           "iteration": current_iteration,
           "submitter": submitter_id
       }
   )
   ```

3. **Monitoring**: Add custom metrics and observability:
   ```python
   workflow.logger.info(
       "approval_received",
       extra={
           "stage": "Review1Check",
           "decision": decision.decision,
           "time_to_approve": time_elapsed
       }
   )
   ```

4. **Testing**: Create unit tests for activities and integration tests for workflows:
   ```python
   # tests/test_activities.py
   async def test_upload_schema():
       result = await upload_schema(UploadSchemaInput(...))
       assert result.status == "success"
   ```

5. **Approval UI**: Build web UI for submitting approvals:
   - Display workflow status via Query
   - Submit approvals via Update
   - Show approval history from workflow state

---

## Future Considerations

### 1. Scalability
For high-volume workflows, consider:
- **Activity batching**: Group multiple schema uploads in single activity
- **Worker scaling**: Run multiple worker processes for throughput
- **Temporal Cloud**: For production deployment with high availability

### 2. Continue-As-New
The workflow includes DO_WHILE loop that can run indefinitely. Implemented continue-as-new:
```python
if workflow.info().is_continue_as_new_suggested():
    workflow.logger.info("Using continue-as-new for large history")
    workflow.continue_as_new(input)
```

Monitor history size and tune continue-as-new threshold if needed.

### 3. Human Interaction UI
Consider building approval interface:
- Web dashboard showing pending approvals
- Email notifications for new approval requests
- Mobile app for on-the-go approvals
- Integration with Slack/Teams for approval notifications

### 4. Audit Trail
Enhance approval history tracking:
- Store detailed approval history in external database
- Track review duration at each stage
- Generate compliance reports
- Implement immutable audit log

### 5. Review Assignment
Current implementation has fixed authorized reviewers. Consider:
- Dynamic reviewer assignment based on schema type
- Round-robin assignment for load balancing
- Escalation if reviews not completed within SLA
- Reviewer availability checking

---

## Validation Results

See `VALIDATION_REPORT.md` for detailed validation results.

**Summary**:
- Syntax Validation: PASS
- Type Checking (mypy --strict): PASS (17 errors fixed)
- Sandbox Compliance: PASS
- Configuration: PASS
- Console Scripts: PASS
- Activity Argument Counts: PASS

---

## References

- Original Conductor workflow: `conductor-definition/EXAMPLE_review_approval.json`
- Conductor Primitives Reference: [conductor-migration/conductor-primitives-reference.md](./conductor-migration/conductor-primitives-reference.md)
- Temporal Python SDK: https://docs.temporal.io/develop/python
- Human Interaction Patterns: [conductor-migration/conductor-human-interaction.md](./conductor-migration/conductor-human-interaction.md)

---

**Migration Tool Version**: 1.0
**Generated**: 2025-11-23

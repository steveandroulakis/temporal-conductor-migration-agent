# Conductor to Temporal: Migration Notes

**Migration Date**: November 23, 2025
**Original Workflow**: conductor-definition/EXAMPLE_review_approval.json
**Complexity**: HIGH

---

## Migration Overview

This document records the decisions, assumptions, and considerations made during the automatic migration from Conductor to Temporal for the **schema_approval** workflow.

## Workflow Characteristics

### Complexity Analysis
- **Max Nesting Depth**: 5 (CompleteReview_2 task)
- **Has Loops**: YES (DO_WHILE loop containing entire approval process)
- **Has Parallel Execution**: YES (FORK_JOIN with 2 branches)
- **Has Dynamic Parallelism**: NO
- **Has Sub-workflows**: NO
- **Complexity Score**: HIGH

### Task Breakdown
- **Total Tasks**: 13 Conductor tasks
- **SIMPLE tasks**: 6 tasks → 6 Temporal activities
  - upload_schema
  - Review1.a
  - Review1.b
  - Review2
  - Review3
  - CompleteReview (appears twice: CompleteReview_1, CompleteReview_2)
- **FORK_JOIN tasks**: 1 task → asyncio.gather()
- **JOIN tasks**: 1 task → implicit (no explicit implementation needed)
- **SWITCH tasks**: 3 tasks → 3 Update handlers + conditional logic
- **DO_WHILE tasks**: 1 task → while loop with max iterations

### Human Interaction Patterns
- **3 approval checkpoints**:
  1. Review1Check (after parallel Review1.a and Review1.b)
  2. Review2Check (determines if Review3 is needed)
  3. Review3Check (final approval)
- **Recommended mechanism**: Update handlers (all 3)
- **Rationale**: Updates provide validation, immediate feedback, and ensure approval decisions are recorded atomically

---

## Migration Decisions

### 1. Control Flow Translation

#### DO_WHILE Loop (repeat_until_approved)
**Decision**: Implemented as Python `while` loop with safety mechanisms
**Rationale**:
- Direct translation: Conductor `loopCondition` → Python `while not self._approved`
- Added `max_iterations = 10` to prevent infinite loops (Conductor has no built-in protection)
- Added `continue-as-new` support for workflows exceeding 100 iterations (commented out, ready for production)
- Extracted loop body to `_execute_approval_iteration()` helper method for readability

**Alternative Approaches**:
- Could use recursion with continue-as-new, but while loop is more Pythonic
- Could use a for loop with fixed range, but while loop better matches Conductor semantics

#### FORK_JOIN Pattern (Review1.a, Review1.b)
**Decision**: Implemented using `asyncio.gather()` with two parallel activity executions
**Rationale**:
- `asyncio.gather()` is the idiomatic Temporal Python pattern for parallel execution
- JOIN task (notification_join_ref) is implicit in `gather()` - no explicit implementation needed
- Results captured in instance variables (`self._review1a_result`, `self._review1b_result`) for later reference

**Alternative Approaches**:
- Could use `asyncio.create_task()` with separate await calls, but gather() is cleaner
- Could use workflow.execute_child_workflow() for each review, but activities are more appropriate for this use case

#### SWITCH Statements (Review1Check, Review2Check, Review3Check)
**Decision**: Translated to Python `if/elif/else` statements with helper methods for nested branches
**Rationale**:
- Conductor SWITCH evaluatorType "value-param" → simple boolean checks in Python
- Nested SWITCH statements (depth 3) handled by extracting helper methods:
  - `_execute_review2_branch()` for Review1Check YES case
  - `_execute_review3_branch()` for Review2Check NO case
  - `_execute_complete_review()` for final completion (two call sites)
- This approach keeps nesting manageable and improves code readability

**Alternative Approaches**:
- Could inline all logic in single method, but this creates 5-level nesting that's hard to read
- Could use state machine pattern, but overkill for this workflow structure

### 2. Human Interaction Patterns

#### Review1Check Approval Checkpoint
**Conductor Pattern**: SWITCH task with `${user_action.output.approved}` external reference
**Temporal Mechanism**: Update handler (`submit_review1_approval`)
**Decision Rationale**:
- **Why Update (not Signal)**:
  - Validation required: Must verify workflow is at correct stage (review1_check)
  - Immediate feedback needed: Return ApprovalResult to caller
  - Duplicate prevention: Must reject duplicate approvals for same iteration
  - Atomic operation: Approval decision must be recorded atomically
- **Implementation**: `workflow.wait_condition()` with 24-hour timeout + Update handler with validation

**Decision Criteria**:
- Update provides synchronous response to caller (Signal does not)
- Update can validate input and reject invalid approvals (Signal accepts all inputs)
- Update ensures exactly-once semantics for approval decisions

#### Review2Check Approval Checkpoint
**Conductor Pattern**: SWITCH task with `skip_review3` decision logic
**Temporal Mechanism**: Update handler (`submit_review2_approval`) with `skip_review3` field
**Decision Rationale**:
- Same rationale as Review1Check (validation, feedback, duplicate prevention)
- Added `skip_review3` boolean field to ApprovalDecision dataclass
- This field controls branching: YES case (skip Review3) vs NO case (require Review3)
- Update handler returns next stage information ("complete" or "review3") for caller visibility

**Alternative Approaches**:
- Could use separate Update handlers for "approve and skip" vs "approve and continue", but single handler with flag is simpler
- Could use Signal for notification + Query to check result, but Update provides better UX

#### Review3Check Approval Checkpoint
**Conductor Pattern**: SWITCH task with final approval decision
**Temporal Mechanism**: Update handler (`submit_review3_approval`)
**Decision Rationale**:
- Same validation and feedback requirements as previous checkpoints
- This is the final approval decision point - after this, workflow completes
- Update handler validates stage and stores decision, triggering CompleteReview activity

### 3. Activity Design

**Decision**: Created 6 activities from Conductor SIMPLE tasks

**Activity Implementations**:
1. **upload_schema**: 30 second timeout (file upload + database operations)
2. **review_1a**: 5 minute timeout (validation logic)
3. **review_1b**: 5 minute timeout (validation logic)
4. **review_2**: 10 minute timeout (more detailed review)
5. **review_3**: 15 minute timeout (comprehensive final review)
6. **complete_review**: 30 second timeout (notifications + status updates)

**Activity Timeout Strategy**:
- Conductor had no timeouts configured → Added sensible defaults based on task names
- Reviews have progressively longer timeouts (5m → 10m → 15m) reflecting increasing complexity
- Quick operations (upload, complete) have 30 second timeouts
- All activities have 24-hour schedule-to-start timeout (default) for queue backlog

**Retry Policy Strategy**:
- All activities use default retry policy: 3 attempts with exponential backoff
- Exception: complete_review has 5 attempts (critical to exit loop successfully)
- Initial interval: 1 second
- Maximum interval: 100 seconds
- Backoff coefficient: 2.0

**Note on CompleteReview**:
- Conductor has two task references (CompleteReview_1, CompleteReview_2) with same task name
- Temporal implementation: Single activity called from two code paths
- This is correct - same business logic, different execution contexts

### 4. Data Type Mapping

**Conductor Input Parameters** → **Temporal Dataclasses**

The Conductor workflow had **no explicit input parameters** (`inputParameters: []`), but we created a sensible default structure:

1. **WorkflowInput**:
   - `submission_id: str` - Unique identifier for schema submission
   - `schema_data: Dict[str, Any]` - The schema content to be reviewed
   - `submitter_email: str` - Email of the person submitting the schema
   - `priority: int = 1` - Priority level (default 1)

   **Rationale**: These fields cover typical schema approval workflow requirements

2. **ReviewInput** (for all review activities):
   - `submission_id: str` - Links review to submission
   - `schema_data: Dict[str, Any]` - Schema being reviewed
   - `review_stage: str` - Which review stage ("Review1.a", "Review1.b", "Review2", "Review3")
   - `previous_reviews: Optional[Dict[str, Any]]` - Results from previous review stages

   **Rationale**: Provides context for each review, enables cascading review logic

3. **ApprovalDecision** (for Update handlers):
   - `reviewer_id: str` - Who is making the approval decision
   - `approved: bool` - The decision (true/false)
   - `skip_review3: bool = False` - For Review2Check only
   - `comments: Optional[str]` - Optional reviewer comments
   - `timestamp: Optional[datetime]` - When decision was made

   **Rationale**: Captures all information needed for approval decisions, supports audit trail

---

## Assumptions Made

### 1. Activity Implementations

Activities contain placeholder implementations marked with TODO comments. These need to be filled in with actual business logic based on the original Conductor task implementations.

**Assumed Business Logic**:
- **upload_schema**: Should store schema in registry, generate IDs, notify reviewers
- **review_1a/review_1b**: Should validate schema structure/semantics, assign to reviewers
- **review_2**: Should perform architectural review, determine if Review3 is needed
- **review_3**: Should perform comprehensive final review by senior reviewers
- **complete_review**: Should finalize approval, send notifications, update statuses

### 2. Timeout Values

Activity timeouts were derived from task names and typical durations. Default values used:
- Quick operations (upload, complete): 30 seconds
- Basic reviews (Review1.a, Review1.b): 5 minutes
- Detailed reviews (Review2): 10 minutes
- Comprehensive reviews (Review3): 15 minutes
- Human approval wait: 24 hours per stage

**These should be adjusted** based on actual production workload and performance requirements.

### 3. Example Input Data

The starter.py generates example input data based on field names:
```python
workflow_input = WorkflowInput(
    submission_id="schema-submission-" + str(uuid.uuid4())[:8],
    schema_data={
        "schema_name": "example_schema",
        "schema_version": "1.0.0",
        "fields": ["field1", "field2", "field3", "field4"],
        "description": "Example schema for testing approval workflow",
    },
    submitter_email="user@example.com",
    priority=1,
)
```

**This should be customized** for your specific use case (real schema format, actual submitter data, etc.).

### 4. Loop Iteration Limit

Set `max_iterations = 10` to prevent infinite loops. Conductor had no such protection.

**Considerations**:
- 10 iterations allows for multiple rejection/resubmission cycles
- If more iterations needed in production, increase this value
- For workflows that could legitimately exceed 100 iterations, uncomment the continue-as-new logic

### 5. No Workflow-Level Timeout

Conductor had `timeoutPolicy: "ALERT_ONLY"` and `timeoutSeconds: 0` (no timeout).

Temporal implementation: No workflow execution timeout configured (defaults to unlimited).

**Recommendation**: Add workflow execution timeout in production:
```python
await client.start_workflow(
    SchemaApprovalWorkflow.run,
    workflow_input,
    id=workflow_id,
    task_queue="schema-approval-task-queue",
    execution_timeout=timedelta(days=7),  # Example: 7 day max
)
```

---

## Known Limitations

### 1. Complex JSONPath Expressions

Conductor workflow uses simple value references (`${user_action.output.approved}`, `${workflow.variables.approved}`). If your original workflow used complex JSONPath expressions (array indexing, filtering, etc.), these may require additional translation work.

### 2. Custom Task Types

This workflow uses only standard Conductor task types (SIMPLE, FORK_JOIN, JOIN, SWITCH, DO_WHILE). If your workflow includes custom task types, those would need custom migration logic.

### 3. External Dependencies

The workflow references external approval data via `${user_action.output.approved}`. In production:
- You may need to integrate with external approval systems (Jira, ServiceNow, custom UI)
- You may need to implement notification activities (email, Slack, etc.) to request approvals
- You may need to add webhook handlers to receive approval decisions from external systems

### 4. Workflow Variables

Conductor `workflow.variables.approved` → Temporal `self._approved`. If your workflow uses other workflow variables, these need to be mapped to Temporal instance variables.

---

## Customization Recommendations

### Immediate Customizations Needed

#### 1. Activity Implementations
Review all TODO comments in `schema_approval_temporal/activities.py` and implement actual business logic:

**upload_schema**:
```python
# TODO: Implement
# - Validate schema_data structure
# - Store in schema registry or database
# - Generate upload confirmation
# - Notify reviewers (email, Slack, etc.)
# - Create audit log entry
```

**review_1a / review_1b**:
```python
# TODO: Implement
# - Validate schema structure/semantics
# - Check compliance with standards
# - Assign to reviewer pool
# - Send notification to reviewer
# - Record review in database
# - For human reviews: May need to poll or wait for callback
```

**review_2 / review_3**:
```python
# TODO: Implement
# - Review previous stage decisions
# - Perform architectural/comprehensive review
# - Check system-wide compatibility
# - Determine next steps (skip Review3, require Review3)
# - Send notifications to stakeholders
# - Record review decision
```

**complete_review**:
```python
# TODO: Implement
# - Update schema registry with approval status
# - Send notifications to submitter and stakeholders
# - Trigger post-approval workflows (deployment, etc.)
# - Create comprehensive audit trail
# - Update metrics and dashboards
# - Archive review artifacts
```

#### 2. Workflow Input

Update example data in `schema_approval_temporal/starter.py` to match your schema format:

```python
workflow_input = WorkflowInput(
    submission_id="your-submission-id-format",
    schema_data={
        # Your actual schema structure
        "schema_name": "...",
        "fields": [...],
        # etc.
    },
    submitter_email="actual-user@yourcompany.com",
    priority=1,  # Adjust priority logic
)
```

#### 3. Timeout Configuration

Review and adjust timeouts based on your actual performance requirements:

**Activity timeouts** (in `workflow.py`):
```python
start_to_close_timeout=timedelta(minutes=5)  # Adjust based on testing
```

**Human approval timeouts**:
```python
await workflow.wait_condition(
    lambda: self._review1_approval is not None,
    timeout=timedelta(hours=24),  # Adjust based on SLA
)
```

**Workflow execution timeout** (in `starter.py`):
```python
execution_timeout=timedelta(days=7)  # Add if needed
```

### Optional Enhancements

#### 1. Enhanced Error Handling

Add specific exception handling for business logic failures:

```python
try:
    upload_message = await workflow.execute_activity(...)
except ApplicationError as e:
    if e.type == "SchemaValidationError":
        # Handle validation failure
        workflow.logger.error(f"Schema validation failed: {e}")
        return  # Exit iteration, loop will restart
    raise  # Re-raise unexpected errors
```

#### 2. Enhanced Logging

Add more context to logging for debugging:

```python
workflow.logger.info(
    "Review decision received",
    extra={
        "reviewer_id": decision.reviewer_id,
        "approved": decision.approved,
        "iteration": self._iteration,
        "submission_id": input.submission_id,
    }
)
```

#### 3. Monitoring and Metrics

Add custom metrics for observability:

```python
# In activities
from temporalio import activity

@activity.defn
async def upload_schema(input_data: UploadSchemaInput) -> str:
    start_time = datetime.now()

    # ... business logic ...

    duration = (datetime.now() - start_time).total_seconds()
    activity.logger.info(f"upload_schema completed in {duration}s")

    # Send metrics to your monitoring system
    # send_metric("schema_approval.upload_duration", duration)
```

#### 4. Continue-As-New Implementation

If workflows could legitimately exceed 100 iterations, implement continue-as-new:

```python
if workflow.info().is_continue_as_new_suggested():
    workflow.logger.info("Continue-as-new - preserving state")
    workflow.continue_as_new(
        WorkflowInput(
            submission_id=input.submission_id,
            schema_data=input.schema_data,
            submitter_email=input.submitter_email,
            priority=input.priority,
        )
    )
```

#### 5. Testing

Create unit tests for activities and integration tests for workflows:

```python
# tests/test_activities.py
import pytest
from schema_approval_temporal.activities import upload_schema
from schema_approval_temporal.shared import UploadSchemaInput

@pytest.mark.asyncio
async def test_upload_schema():
    result = await upload_schema(
        UploadSchemaInput(
            submission_id="test-123",
            schema_data={"test": "data"},
            iteration=1,
        )
    )
    assert "test-123" in result
    assert "uploaded successfully" in result.lower()
```

```python
# tests/test_workflow.py
import pytest
from temporalio.testing import WorkflowEnvironment
from schema_approval_temporal.workflow import SchemaApprovalWorkflow
from schema_approval_temporal.shared import WorkflowInput

@pytest.mark.asyncio
async def test_approval_workflow_full_path():
    async with WorkflowEnvironment() as env:
        # Test complete approval path
        # (Review1 → Review2 → Review3 → Complete)
        ...
```

---

## Future Considerations

### 1. Scalability

For high-volume workflows, consider:

**Activity Batching**:
- If submitting many schemas simultaneously, consider batching notifications
- Could implement queue-based notification system

**Worker Scaling**:
- Start with single worker, scale horizontally as needed
- Monitor task queue lag and worker utilization
- Use Temporal Cloud for automatic scaling

**Temporal Cloud**:
- For production, consider Temporal Cloud for managed infrastructure
- Provides global namespace, multi-region deployment, enterprise support

### 2. Continue-As-New for Long-Running Workflows

The workflow includes a DO_WHILE loop that could theoretically run indefinitely. Monitor history size:

```python
if workflow.info().get_current_history_length() > 2000:
    workflow.logger.info("History size exceeds 2000 events - implementing continue-as-new")
    workflow.continue_as_new(input)
```

**When to use continue-as-new**:
- Workflow history exceeds 50KB (warning) or 50MB (error)
- Workflow iterations exceed 100
- Long-running workflows (days/weeks) with periodic state updates

### 3. Human Interaction UI

The workflow uses Update handlers for approval decisions. Consider building a UI:

**Web UI for Approvals**:
- Display pending approvals from `get_status` query
- Submit approval decisions via Update handlers
- Show approval history and audit trail
- Integrate with SSO/authentication

**Webhook Integration**:
- Receive approval decisions from external systems (Jira, ServiceNow)
- Map external approval data to ApprovalDecision format
- Send Update to workflow

**Notification System**:
- Email/Slack notifications when approval needed
- Include workflow URL: `http://localhost:8233/namespaces/default/workflows/{workflow_id}`
- Include approve/reject action links

### 4. Multi-Tenancy

If supporting multiple teams/organizations:

**Namespace Separation**:
- Use separate Temporal namespaces per tenant
- Configure worker per namespace

**Task Queue Routing**:
- Use tenant-specific task queues: `schema-approval-{tenant_id}`
- Start workers per tenant or use dynamic task queue routing

**Data Isolation**:
- Ensure schema data is properly isolated per tenant
- Add tenant_id to all dataclasses
- Validate tenant access in Update handlers

### 5. Audit Trail and Compliance

For regulated industries:

**Comprehensive Logging**:
- Log all approval decisions with timestamps
- Log all review activity results
- Store workflow history for compliance period (7 years for some regulations)

**Immutable Storage**:
- Archive completed workflow histories to immutable storage
- Use Temporal's archival feature to move history to S3/GCS

**Compliance Reports**:
- Query Temporal for approval audit trails
- Generate compliance reports showing all review stages
- Track approval SLAs and missed deadlines

---

## Validation Results

See `VALIDATION_REPORT.md` for detailed validation results.

**Summary**:
- Syntax Validation: PASS (all 7 files compile without errors)
- Type Checking: PASS (mypy --strict with 0 errors, 2 fixed)
- Sandbox Compliance: PASS (activities imported by name, no non-deterministic code in workflow)
- Configuration: PASS ([tool.uv] present, console scripts configured)
- Activity Argument Counts: PASS (all match function signatures)

**Fixes Applied During Validation**:
1. Type safety for optional ReviewOutput: Added conditional checks for None cases in logging
2. Workflow sandbox violation: Fixed during execution testing (datetime.utcnow() → workflow.now())

## Execution Results

See `WORKFLOW_EXECUTION_REPORT.md` for detailed execution results.

**Summary**:
- Workflow executed successfully: PASS (after 1 fix)
- All 6 activities executed: PASS
- 3 Update handlers tested: PASS
- 1 Query handler tested: PASS
- Human interaction flow: PASS (Review1 → Review2 → Review3 → Complete)
- Execution time: 38.98 seconds for full approval path

**Critical Finding**:
- Initial code validation did not catch `datetime.utcnow()` sandbox violation (runtime error only)
- Demonstrates value of execution testing phase
- Fix applied: `datetime.utcnow()` → `workflow.now()` (deterministic timestamp)

---

## References

- Original Conductor workflow: `conductor-definition/EXAMPLE_review_approval.json`
- Conductor Primitives Reference: [conductor-migration/conductor-primitives-reference.md](./conductor-migration/conductor-primitives-reference.md)
- Temporal Python SDK: https://docs.temporal.io/develop/python
- Temporal Python SDK API: https://python.temporal.io/

---

**Migration Tool Version**: 1.0
**Generated**: November 23, 2025
**Generated by**: documentation-generator agent (Agent 7)
**Pipeline Stage**: 7 of 8 (Documentation Generation)

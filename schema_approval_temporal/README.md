# schema_approval_temporal Module Documentation

This module contains the Temporal workflow implementation for **schema_approval**.

**Migrated from**: Conductor workflow `conductor-definition/EXAMPLE_review_approval.json`

## Module Structure

### shared.py
Data models (dataclasses) for workflow and activity inputs/outputs.

**Exports**:
- `WorkflowInput` - Workflow input parameters (schema_id, schema_content, submitter_id, priority, metadata)
- `WorkflowOutput` - Workflow output results (status, approved, iterations, approval_history)
- `UploadSchemaInput` - Input for upload_schema activity
- `UploadSchemaOutput` - Output from upload_schema activity
- `ReviewResult` - Result from review activities (Review1.a, Review1.b, Review2, Review3)
- `CompleteReviewOutput` - Output from CompleteReview activities
- `ApprovalDecision` - Human approval decision for review checkpoints
- `ApprovalResult` - Result returned from approval update
- `WorkflowState` - Internal workflow state tracking

### activities.py
Activity implementations for schema approval process.

**Exports**:
- `upload_schema(input_data: UploadSchemaInput) -> UploadSchemaOutput` - Upload schema for review
- `review_1a(schema_id: str, upload_id: str) -> ReviewResult` - First parallel review (branch A)
- `review_1b(schema_id: str, upload_id: str) -> ReviewResult` - First parallel review (branch B)
- `review_2(schema_id: str, review1_results: Dict[str, Any]) -> ReviewResult` - Second review stage
- `review_3(schema_id: str, review2_results: Dict[str, Any]) -> ReviewResult` - Third review stage (optional)
- `complete_review_skip_review3(schema_id: str, review_results: Dict[str, Any], approved: bool) -> CompleteReviewOutput` - Complete review (expedited path)
- `complete_review_after_review3(schema_id: str, review_results: Dict[str, Any], approved: bool) -> CompleteReviewOutput` - Complete review (full review path)

**Activity Timeouts**:
- upload_schema: 30 seconds
- review_1a, review_1b: 20 seconds
- review_2, review_3: 30 seconds
- complete_review (both): 20 seconds

**Retry Policy**: All activities use DEFAULT_RETRY_POLICY (3 attempts, exponential backoff)

### workflow.py
Workflow orchestration for multi-stage approval process.

**Exports**:
- `SchemaApprovalWorkflow` - Main workflow class

**Workflow Updates** (Human Interaction):
- `submit_review1_approval(decision: ApprovalDecision) -> ApprovalResult` - Submit Review1 approval
- `submit_review2_approval(decision: ApprovalDecision) -> ApprovalResult` - Submit Review2 approval
- `submit_review3_approval(decision: ApprovalDecision) -> ApprovalResult` - Submit Review3 approval

**Workflow Queries**:
- `get_approval_status() -> Dict[str, Any]` - Query current approval status

**Control Flow**:
- DO_WHILE loop: Repeats until final approval
- FORK_JOIN: Parallel execution of Review1.a and Review1.b
- 3 SWITCH conditionals: Review1Check, Review2Check, Review3Check
- Maximum nesting depth: 5 levels
- Max iterations: 10 (configurable)

### worker.py
Worker registration and execution.

**Entry Point**: `worker:main` (console script)

**Configuration**:
- Task queue: schema-approval-task-queue
- Activity executor: ThreadPoolExecutor (5 workers)
- Temporal server: localhost:7233

**Usage**:
```bash
uv run worker
```

### starter.py
Workflow starter client.

**Entry Point**: `starter:main` (console script)

**Configuration**:
- Task queue: schema-approval-task-queue
- Execution timeout: 24 hours
- Temporal server: localhost:7233

**Usage**:
```bash
uv run starter
```

## Usage

See the main project README.md for complete setup and usage instructions.

## Development

When modifying this module:

1. **Maintain strict type hints** (mypy --strict compliance):
   ```bash
   mypy schema_approval_temporal --strict --ignore-missing-imports
   ```

2. **Update docstrings** for any function changes

3. **Run validation**:
   ```bash
   python3 -m py_compile schema_approval_temporal/*.py
   ```

4. **Test with worker and starter**:
   ```bash
   # Terminal 1
   temporal server start-dev
   
   # Terminal 2
   uv run worker
   
   # Terminal 3
   uv run starter
   ```

## Architecture Notes

### Human Interaction Pattern
This workflow uses **Workflow Updates** for approval gates:
- Provides validation before accepting approvals
- Returns immediate feedback to approver
- Ensures data integrity and authorization
- Three approval checkpoints: Review1Check, Review2Check, Review3Check

### Loop Pattern
DO_WHILE loop implementation:
- Repeats entire review process until approved
- Maximum 10 iterations (prevents infinite loops)
- Uses continue-as-new for large iteration counts
- Approval variables reset each iteration

### Parallel Execution
FORK_JOIN pattern using asyncio.gather():
- Review1.a and Review1.b execute in parallel
- Both must complete successfully
- JOIN is implicit (gather waits for all)

### Nested Conditionals
Three-level nested SWITCH statements:
- Level 2: Review1Check (after parallel reviews)
- Level 3: Review2Check (nested in Review1Check YES branch)
- Level 4: Review3Check (nested in Review2Check NO branch)
- Level 5: CompleteReview_2 (maximum nesting depth)

---

**Migrated from Conductor workflow**: `conductor-definition/EXAMPLE_review_approval.json`
**Complexity**: high (5-level nesting, loops, parallel execution, human interaction)

"""Temporal workflow package: schema_approval_temporal

Migrated from Netflix Conductor workflow definition to Temporal Python SDK.

**Original Conductor Workflow**: conductor-definition/EXAMPLE_review_approval.json
**Workflow Name**: schema_approval
**Version**: 1
**Complexity**: HIGH (max nesting depth: 5)

## Package Overview

This package implements a multi-stage schema approval workflow with human review
checkpoints. The workflow uses a DO_WHILE loop containing a complex approval process
with parallel reviews, nested conditional checks, and multiple human interaction points.

### Workflow Characteristics

- **DO_WHILE loop**: Repeats until final approval (max 10 iterations)
- **Parallel execution**: FORK_JOIN with 2 review branches
- **Conditional branching**: 3 SWITCH tasks with human approval decisions
- **Human interaction**: 3 Update handlers for approval decisions
- **Maximum nesting depth**: 5 levels

### Approval Flow

1. **Review1**: Parallel execution of Review1.a and Review1.b
   - Wait for human approval decision (Update: submit_review1_approval)
   - If approved: Proceed to Review2
   - If rejected: Restart loop

2. **Review2**: Second-stage review (conditional on Review1 approval)
   - Wait for human approval decision (Update: submit_review2_approval)
   - If approved + skip_review3=true: Complete via CompleteReview_1
   - If approved + skip_review3=false: Proceed to Review3
   - If rejected: Restart loop

3. **Review3**: Final-stage review (conditional on Review2 decision)
   - Wait for human approval decision (Update: submit_review3_approval)
   - If approved: Complete via CompleteReview_2
   - If rejected: Restart loop

## Module Structure

### Core Components

- **shared.py**: Type-safe dataclasses for workflow and activity inputs/outputs
- **activities.py**: 6 activity implementations for business logic
- **workflow.py**: Workflow orchestration with complex control flow
- **worker.py**: Worker registration and execution
- **starter.py**: Workflow starter client
- **interact.py**: Client for workflow interaction (Updates/Queries)

### Activity Implementations

1. **upload_schema**: Upload schema for review (30s timeout)
2. **review_1a**: First parallel review task (5m timeout)
3. **review_1b**: Second parallel review task (5m timeout)
4. **review_2**: Second-stage review (10m timeout)
5. **review_3**: Third-stage review (15m timeout)
6. **complete_review**: Finalize approval process (30s timeout)

### Human Interaction Handlers

**Update Handlers** (synchronous approval decisions with validation):
- `submit_review1_approval`: Submit Review1 approval decision
- `submit_review2_approval`: Submit Review2 approval decision (with skip_review3 flag)
- `submit_review3_approval`: Submit Review3 (final) approval decision

**Query Handlers** (workflow state inspection):
- `get_status`: Get current workflow status, review progress, and next action

## Usage

### Starting a Worker

```bash
uv run worker
```

### Starting a Workflow

```bash
uv run starter
```

### Interacting with Running Workflow

```bash
# Check status
uv run interact query <workflow-id> get_status

# Submit Review1 approval
uv run interact update <workflow-id> submit_review1_approval '{
  "reviewer_id": "user@example.com",
  "approved": true,
  "comments": "Looks good"
}'

# Submit Review2 approval (skip Review3)
uv run interact update <workflow-id> submit_review2_approval '{
  "reviewer_id": "user@example.com",
  "approved": true,
  "skip_review3": true
}'

# Submit Review3 approval (if required)
uv run interact update <workflow-id> submit_review3_approval '{
  "reviewer_id": "user@example.com",
  "approved": true
}'
```

### Monitoring

Access the Temporal Web UI at:
```
http://localhost:8233/namespaces/default/workflows/<workflow-id>
```

## Development

### Type Safety

All code is fully type-checked with mypy --strict:
```bash
mypy schema_approval_temporal --strict --ignore-missing-imports
```

### Code Quality

Code follows strict Python standards:
- Complete type hints on all functions
- Comprehensive docstrings
- PEP 8 compliant
- No use of `Any` type

### Activity Business Logic

Activities contain placeholder implementations marked with TODO comments.
These need to be filled in with actual business logic:

1. **upload_schema**: Implement schema storage, notifications
2. **review_1a/review_1b**: Implement validation, reviewer assignment
3. **review_2/review_3**: Implement review logic
4. **complete_review**: Implement finalization (notifications, audit trail)

## Migration Notes

This package was automatically migrated from Conductor. Key differences:

- **Control Flow**: Conductor JSON (DO_WHILE, FORK_JOIN, SWITCH) → Python (while, asyncio.gather, if/elif)
- **Data Passing**: Conductor `${workflow.variables.X}` → Python `self._X`
- **Human Interaction**: Conductor SWITCH + external data → Temporal Updates with validation
- **Error Handling**: Conductor retry configs → Temporal RetryPolicy objects
- **Loop Safety**: Added max_iterations limit (Conductor had no protection)

See documentation for complete migration details:
- PROJECT_README.md: Setup and usage instructions
- CONDUCTOR_COMPARISON.md: Side-by-side code comparison
- CONDUCTOR_MIGRATION_NOTES.md: Migration decisions and recommendations
- VALIDATION_REPORT.md: Code validation results
- WORKFLOW_EXECUTION_REPORT.md: Execution test results

## Requirements

- Python 3.11+
- temporalio>=1.5.0
- Temporal server (dev server or Temporal Cloud)

## Version

__version__ = "0.1.0"

---

**Generated by Conductor to Temporal Migration Tool**
**Migration Date**: November 23, 2025
**Migration Agent**: documentation-generator (Agent 7)
"""

__version__ = "0.1.0"

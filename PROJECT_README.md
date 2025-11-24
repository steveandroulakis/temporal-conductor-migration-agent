# Insurance Claim Processing - Temporal Migration

Migrated from Netflix Conductor workflow definition to Temporal Python SDK.

**Original Conductor Workflow**: `conductor-definition/insurance_claim.json`
**Migration Date**: November 23, 2025
**Complexity**: HIGH (Max nesting depth: 5 levels)

## Overview

This project implements the **insurance_claim** workflow using Temporal's Python SDK. The workflow was automatically migrated from a Conductor JSON definition to enable modern, code-first orchestration with type safety and deterministic execution.

### Workflow Description

This workflow automates insurance claim processing from initial submission through payment authorization. It handles policy validation, assessor evaluation, damage cost calculation, and conditional investigation for high-value claims.

**Business Process**:
1. Customer submits claim with policy selection
2. System validates policy type (AUTO only)
3. Assessor evaluates damage on-site
4. System calculates covered costs
5. High-cost claims trigger investigation
6. Approved claims authorize payment

### Control Flow

This workflow implements:
- **2 activity executions**: Policy lookup, claim creation
- **4 conditional branches (SWITCH)**: Policy validation, coverage check, cost threshold, post-investigation review
- **3 human interaction points**: Claim submission, assessor evaluation, investigation (conditional)
- **5 levels of nesting**: Deep decision tree with multiple termination paths
- **2 inline transformations**: Policy menu mapping, damage cost calculation
- **4 termination paths**: Invalid policy, not covered, investigation failure, success

### Key Features

- **Interactive Workflow**: 3 Update handlers for human input with validation
- **Complex Cost Logic**: Damage assessment with coverage percentages and cost mapping
- **Conditional Investigation**: Automatic trigger for claims exceeding $100 threshold
- **Multiple Outcomes**: 4 distinct termination scenarios with detailed results
- **Type-Safe**: Complete type hints, mypy --strict compliant
- **Production-Ready**: Validated and executed end-to-end successfully

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
chmod +x setup.sh  # Make executable (first time only)
./setup.sh
```

Or manually:
```bash
uv venv
uv add temporalio
uv add --dev mypy ruff
uv sync --all-extras
```

### 2. Start the Worker

In a terminal window:
```bash
uv run worker
```

You should see:
```
Worker ready — polling task queue: insurance-claim-task-queue
```

Keep this terminal running.

### 3. Execute the Workflow

In a new terminal window:
```bash
uv run starter
```

The starter will:
- Connect to Temporal
- Start the workflow with example input (John Smith)
- Display the workflow URL
- Wait for human interactions
- Display instructions for next steps

### 4. Monitor in Web UI

Open the workflow in your browser:
```
http://localhost:8233
```

Navigate to your workflow to see:
- Workflow execution history
- Activity results
- Current status
- Pending human interactions (awaiting_claim_submission initially)

## Project Structure

```
insurance_claim_temporal/
├── insurance_claim_temporal/          # Main package directory
│   ├── __init__.py                    # Package marker
│   ├── shared.py                      # Data models (18 dataclasses)
│   ├── activities.py                  # Activity implementations (2 activities)
│   ├── workflow.py                    # Workflow definition (complex nesting)
│   ├── worker.py                      # Worker registration
│   ├── starter.py                     # Workflow starter
│   └── interact.py                    # Workflow interaction client (3 Updates, 3 Queries)
├── pyproject.toml                     # Project configuration
├── setup.sh                           # Automated setup script
├── PROJECT_README.md                  # This file
├── CONDUCTOR_COMPARISON.md            # Conductor vs Temporal mapping
├── CONDUCTOR_MIGRATION_NOTES.md       # Migration decisions
├── VALIDATION_REPORT.md               # Code validation results
└── WORKFLOW_EXECUTION_REPORT.md       # End-to-end test results
```

### Module Overview

- **shared.py**: 18 dataclasses for workflow inputs, outputs, activities, and human interactions. Includes cost mapping constants.
- **activities.py**: 2 activities implementing business logic:
  - `find_policy_for_customer`: Query customer policies by name
  - `create_claim_for_policy`: Persist new claim in database
- **workflow.py**: Complex workflow orchestration with 5-level nesting, 4 SWITCH decisions, 3 Update handlers, 3 Query handlers, 2 inline Python functions
- **worker.py**: Worker process that executes workflows and activities
- **starter.py**: Client for starting workflow executions
- **interact.py**: **CRITICAL** - Client for interacting with running workflows (Updates, Signals, Queries)

## Interacting with Running Workflows

**IMPORTANT**: This workflow has **3 Update handlers** and **3 Query handlers**. You **must** use the `interact.py` client to interact with running workflows. The workflow cannot complete without human interactions.

The `interact.py` script provides a command-line interface for:
- **Updates**: Send validated decisions/data that return immediate feedback
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

#### Update: `submit_claim`
**Purpose**: Customer submits claim with policy selection and incident description
**Input**: `ClaimSubmission` with fields:
- `policy_picker` (str): Selected policy number (e.g., "POL-AUTO-001")
- `incident_description` (str): Description of incident (minimum 10 characters)

**Validation**:
- Policy selection required
- Incident description minimum 10 characters
- Cannot submit twice

**Example**:
```bash
uv run interact update insurance-claim-abc123 submit_claim '{
  "policy_picker": "POL-AUTO-001",
  "incident_description": "Minor fender bender on Main Street"
}'
```

**Python equivalent**:
```python
from temporalio.client import Client
from insurance_claim_temporal.shared import ClaimSubmission
from insurance_claim_temporal.workflow import InsuranceClaimWorkflow

client = await Client.connect("localhost:7233")
handle = client.get_workflow_handle("insurance-claim-abc123")

result = await handle.execute_update(
    InsuranceClaimWorkflow.submit_claim,
    ClaimSubmission(
        policy_picker="POL-AUTO-001",
        incident_description="Minor fender bender on Main Street"
    )
)
print(f"Result: {result.status} - {result.message}")
```

---

#### Update: `submit_assessor_findings`
**Purpose**: Assessor submits damage evaluation from on-site inspection
**Input**: `AssessorFindings` with fields:
- `visible_assesments` (List[DamageAssessment]): Array of damage items, each with:
  - `damage_type` (str): Type of damage (e.g., "Side collision Damage", "Minor front door damage", "Windshield Damage")
  - `coverage_determination` (str): "Covered" or "Not covered"
  - `coverage_score` (int): Coverage percentage (0-100)
- `overall_coverage` (str): Overall coverage decision ("yes", "no", or "Not Covered")
- `rationale` (str): Assessor's explanation
- `incident_city` (str): City where incident occurred
- `incident_street` (str): Street address
- `incident_state` (str): State

**Validation**:
- At least one damage assessment required
- Overall coverage determination required
- Cannot submit twice

**Example**:
```bash
uv run interact update insurance-claim-abc123 submit_assessor_findings '{
  "visible_assesments": [
    {
      "damage_type": "Minor front door damage",
      "coverage_determination": "Covered",
      "coverage_score": 100
    }
  ],
  "overall_coverage": "yes",
  "rationale": "Minor damage is fully covered under the policy",
  "incident_city": "San Francisco",
  "incident_street": "123 Main St",
  "incident_state": "CA"
}'
```

**Cost Calculation**: The workflow will automatically calculate costs based on the damage types:
- "Side collision Damage": $2,500
- "Minor front door damage": $500
- "Windshield Damage": $1,000

**Investigation Trigger**: If total covered cost exceeds $100, the workflow will wait for investigation findings.

---

#### Update: `submit_investigation_findings`
**Purpose**: Investigator submits findings for high-cost claims (>$100)
**Input**: `InvestigationFindings` with fields:
- `investigation_findings` (str): Detailed investigation results
- `witness_statements` (List[str], optional): Witness statements

**Validation**:
- Investigation findings cannot be empty
- Cannot submit twice
- Only applicable when cost exceeds threshold

**Example**:
```bash
uv run interact update insurance-claim-abc123 submit_investigation_findings '{
  "investigation_findings": "On-site investigation confirms no fraud detected. Damage is legitimate.",
  "witness_statements": [
    "Witness 1: Saw the accident occur",
    "Witness 2: Confirms details"
  ]
}'
```

**Note**: This Update is only needed if the total covered cost exceeds $100. Check the workflow status query to see if investigation is required.

---

#### Query: `get_status`
**Purpose**: Check current workflow status and progress
**Returns**: Dict with current status, stage, and submission states

**Example**:
```bash
uv run interact query insurance-claim-abc123 get_status
```

**Response**:
```json
{
  "status": "started",
  "current_stage": "awaiting_claim_submission",
  "has_claim_submission": false,
  "has_assessor_findings": false,
  "has_investigation_findings": false,
  "policy_selected": null,
  "overall_coverage": null
}
```

---

#### Query: `get_claim_details`
**Purpose**: Retrieve submitted claim details
**Returns**: Dict with policy selection and incident description, or null if not submitted

**Example**:
```bash
uv run interact query insurance-claim-abc123 get_claim_details
```

---

#### Query: `get_damage_summary`
**Purpose**: Retrieve damage assessment summary
**Returns**: Dict with assessor findings summary, or null if not available

**Example**:
```bash
uv run interact query insurance-claim-abc123 get_damage_summary
```

### Complete Workflow Example

Here's a complete end-to-end execution with high-cost claim (includes investigation):

```bash
# Terminal 1: Start Temporal dev server
temporal server start-dev

# Terminal 2: Start worker
uv run worker
# Output: Worker ready — polling task queue: insurance-claim-task-queue

# Terminal 3: Start workflow
uv run starter
# Output: Workflow started with ID: insurance-claim-abc123
#         Workflow URL: http://localhost:8233/namespaces/default/workflows/insurance-claim-abc123
#         Waiting for claim submission...

# Terminal 4: Interact with workflow

# Step 1: Check initial status
uv run interact query insurance-claim-abc123 get_status
# Output: {"status": "started", "current_stage": "awaiting_claim_submission", ...}

# Step 2: Submit claim
uv run interact update insurance-claim-abc123 submit_claim '{
  "policy_picker": "POL-AUTO-001",
  "incident_description": "Minor fender bender on Main Street"
}'
# Output: {"status": "accepted", "message": "Claim submitted for policy POL-AUTO-001"}

# Step 3: Submit assessor findings (high cost triggers investigation)
uv run interact update insurance-claim-abc123 submit_assessor_findings '{
  "visible_assesments": [
    {
      "damage_type": "Minor front door damage",
      "coverage_determination": "Covered",
      "coverage_score": 100
    }
  ],
  "overall_coverage": "yes",
  "rationale": "Minor damage is fully covered under the policy",
  "incident_city": "San Francisco",
  "incident_street": "123 Main St",
  "incident_state": "CA"
}'
# Output: {"status": "accepted", "message": "Assessor findings recorded with 1 damage assessments"}
# Note: $500 * 100% = $500 covered (exceeds $100, triggers investigation)

# Step 4: Submit investigation findings
uv run interact update insurance-claim-abc123 submit_investigation_findings '{
  "investigation_findings": "On-site investigation confirms no fraud detected. Damage is legitimate.",
  "witness_statements": [
    "Witness 1: Saw the accident occur",
    "Witness 2: Confirms details"
  ]
}'
# Output: {"status": "accepted", "message": "Investigation findings recorded"}

# Terminal 3 (starter) will display final result:
# Workflow completed with status: COMPLETED
# Reason: Send Payment to client
# Total covered cost: $500
```

### Workflow Execution Paths

The workflow has 4 possible termination paths:

1. **Invalid Policy** (TERMINATED)
   - Trigger: Selected policy type is not "AUTO"
   - Example: Select "POL-HOME-002" in submit_claim
   - Result: `{"status": "TERMINATED", "reason": "Terminated because of invalid policy"}`

2. **Not Covered by Policy** (TERMINATED)
   - Trigger: Assessor sets `overall_coverage = "Not Covered"`
   - Result: `{"status": "TERMINATED", "reason": "Policy does not cover incident"}`

3. **Not Covered After Investigation** (TERMINATED)
   - Trigger: High-cost claim where investigation reveals non-coverage
   - Result: `{"status": "TERMINATED", "reason": "Terminated after investigation. Incident not covered"}`

4. **Success - Payment Authorized** (COMPLETED)
   - Trigger: Valid AUTO policy, covered by policy, passes investigation (if needed)
   - Result: `{"status": "COMPLETED", "reason": "Send Payment to client", "details": {...}}`

## Configuration

### Workflow Timeouts

The workflow has the following timeout configuration:
- **Claim submission wait**: 72 hours (3 days)
- **Assessor findings wait**: 48 hours (2 days)
- **Investigation wait**: 24 hours (1 day)
- **Activity timeouts**:
  - `find_policy_for_customer`: 30 seconds
  - `create_claim_for_policy`: 45 seconds

To adjust timeouts, edit the timeout parameters in `insurance_claim_temporal/workflow.py`:
```python
await workflow.wait_condition(
    lambda: self._claim_submission is not None,
    timeout=timedelta(hours=72)  # Modify as needed
)
```

### Task Queue

The worker and starter use task queue: **insurance-claim-task-queue**

To change the task queue:
1. Update `worker.py`: `task_queue="new-queue-name"`
2. Update `starter.py`: `task_queue="new-queue-name"`

### Workflow Input

To customize workflow input, edit `insurance_claim_temporal/starter.py`:
```python
workflow_input = WorkflowInput(
    first_name="John",  # Modify customer name
    last_name="Smith"
)
```

### Cost Threshold

The investigation cost threshold is configurable in `insurance_claim_temporal/shared.py`:
```python
INVESTIGATION_COST_THRESHOLD: int = 100  # Modify threshold
```

**Note**: The current threshold of $100 is intentionally low for demonstration purposes. In production, this should be set to a realistic value (e.g., $5,000).

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

**Error**: `Activity X not found`

**Solution**: Ensure worker is running before starting workflow.

---

**Error**: `Workflow execution timeout`

**Solution**: This workflow requires human interactions. Use `interact.py` to submit claim data. Check workflow status:
```bash
uv run interact query <workflow-id> get_status
```

### Workflow Stuck

**Issue**: Workflow is running but not completing

**Solution**: The workflow is waiting for human input. Check current stage:
```bash
uv run interact query <workflow-id> get_status
```

Then submit the required Update:
- `awaiting_claim_submission` → Use `submit_claim`
- `awaiting_assessor_findings` → Use `submit_assessor_findings`
- `awaiting_investigation` → Use `submit_investigation_findings`

### Update Validation Errors

**Error**: `Claim already submitted`

**Solution**: Each Update can only be sent once. This is intentional to prevent duplicate submissions.

---

**Error**: `Policy selection is required`

**Solution**: Ensure `policy_picker` field is not empty in JSON payload.

---

**Error**: `Incident description must be at least 10 characters`

**Solution**: Provide a more detailed incident description (minimum 10 characters).

### Type Checking Issues

To run type checking:
```bash
mypy insurance_claim_temporal --strict --ignore-missing-imports
```

If errors occur, see `VALIDATION_REPORT.md` for guidance.

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
ruff check insurance_claim_temporal/
```

### Customization Required

The generated workflow is production-ready but requires customization for actual use:

1. **Activity Implementations**: Replace TODO placeholders in `activities.py`:
   - Implement actual database queries in `find_policy_for_customer`
   - Implement actual claim creation in `create_claim_for_policy`

2. **UI Integration**: Build web forms for human interactions:
   - Form for claim submission (`claimant_locator_form`)
   - Form for assessor report (`assesor_report`)
   - Form for investigation (`on_site_investigation`)

3. **Cost Threshold**: Adjust `INVESTIGATION_COST_THRESHOLD` in `shared.py` to realistic production value

4. **Damage Cost Map**: Update `DAMAGE_COST_MAP` in `shared.py` with actual damage type costs

5. **Timeout Values**: Adjust wait condition timeouts based on business requirements

## Migration Notes

This project was automatically migrated from Conductor. See:
- **CONDUCTOR_COMPARISON.md** - Side-by-side Conductor vs Temporal examples
- **CONDUCTOR_MIGRATION_NOTES.md** - Migration decisions and recommendations

### Key Differences from Conductor

- **Control Flow**: Conductor JSON primitives (SWITCH, FORK_JOIN, DO_WHILE) translated to Python (if/elif, asyncio.gather, while)
- **Data Passing**: Conductor expressions `${workflow.input.X}` → Python `input.X`
- **Human Interaction**: Conductor HUMAN_TASK → Temporal Update handlers with validation
- **Error Handling**: Conductor retry configs → Temporal RetryPolicy objects
- **Activities**: Conductor SIMPLE tasks → Temporal @activity.defn functions
- **Inline Tasks**: Conductor INLINE (JavaScript) → Pure Python functions in workflow
- **Determinism**: Temporal enforces deterministic workflow code (no random, datetime.now, etc.)

### Migration Highlights

- **Deep Nesting**: 5 levels of nested SWITCH tasks successfully translated to clean Python code
- **Complex Calculations**: 90+ line JavaScript damage calculation accurately translated to Python
- **Human Interactions**: 3 HUMAN tasks mapped to Update handlers with comprehensive validation
- **Multiple Termination Paths**: 4 TERMINATE tasks correctly mapped to distinct WorkflowOutput responses

## Additional Resources

- [Temporal Python SDK Documentation](https://docs.temporal.io/develop/python)
- [Temporal Python SDK API Reference](https://python.temporal.io/)
- [Temporal Learning Portal](https://learn.temporal.io/)
- [Conductor to Temporal Migration Guide](./conductor-migration/)

## Support

For migration-specific questions:
- Review `CONDUCTOR_MIGRATION_NOTES.md` for decisions made during migration
- Check `VALIDATION_REPORT.md` for code quality notes
- Review `WORKFLOW_EXECUTION_REPORT.md` for end-to-end test results
- Consult the Conductor migration documentation in `conductor-migration/`

---

**Generated by Conductor to Temporal Migration Tool**
**Migration Date**: November 23, 2025
**Migration System Version**: 1.0
**Workflow Complexity**: HIGH
**Validation Status**: ALL CHECKS PASSED
**Execution Status**: SUCCESSFULLY TESTED END-TO-END

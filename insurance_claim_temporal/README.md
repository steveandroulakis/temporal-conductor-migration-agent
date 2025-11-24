# insurance_claim_temporal Module Documentation

This module contains the Temporal workflow implementation for **insurance_claim** (Insurance Claim Processing).

**Migrated from**: Conductor workflow `conductor-definition/insurance_claim.json`
**Complexity**: HIGH (5-level nesting, 4 SWITCH tasks, 3 human interactions)

## Module Structure

### shared.py
Data models (dataclasses) for workflow and activity inputs/outputs.

**Exports**:
- **Workflow Types**:
  - `WorkflowInput(first_name, last_name)` - Workflow input parameters
  - `WorkflowOutput(status, reason, details)` - Workflow result with multiple termination paths

- **Activity Types**:
  - `Policy(policy_number, policy_type)` - Customer policy details
  - `PolicyMenuItem(const, title)` - Menu item format for UI
  - `FindPolicyInput(first_name, last_name)` - Input for policy lookup activity
  - `FindPolicyOutput(policies)` - Output from policy lookup
  - `CreateClaimInput(policy_id, description)` - Input for claim creation activity

- **Human Interaction Types**:
  - `ClaimSubmission(policy_picker, incident_description)` - Customer claim submission
  - `ClaimSubmissionResult(status, message)` - Result from claim submission Update
  - `DamageAssessment(damage_type, coverage_determination, coverage_score)` - Individual damage item
  - `AssessorFindings(visible_assesments, overall_coverage, rationale, incident_city, incident_street, incident_state)` - Assessor evaluation
  - `AssessorFindingsResult(status, message)` - Result from assessor Update
  - `InvestigationFindings(investigation_findings, witness_statements)` - Investigation report
  - `InvestigationFindingsResult(status, message)` - Result from investigation Update

- **Damage Calculation Types**:
  - `DamageItem(description, estimated_cost, coverage, covered_percentage)` - Calculated damage item
  - `DamageEstimation(total_damage_cost, items)` - Total damage estimation
  - `CoverageCalculation(total_covered_cost, total_non_covered_cost, explanation)` - Coverage calculation
  - `DamageCalculationResult(damage_estimation, coverage_calculation)` - Complete calculation result

- **Constants**:
  - `DAMAGE_COST_MAP` - Mapping of damage types to costs (Side collision: $2,500, Minor front door: $500, Windshield: $1,000)
  - `INVESTIGATION_COST_THRESHOLD` - Cost threshold for triggering investigation ($100)

### activities.py
Activity implementations for external operations.

**Exports**:
- `find_policy_for_customer(input_data: FindPolicyInput) -> FindPolicyOutput`
  - Queries customer policies by name
  - Timeout: 30 seconds
  - Retry: 3 attempts with exponential backoff
  - **TODO**: Implement actual database query (currently returns sample policies)

- `create_claim_for_policy(input_data: CreateClaimInput) -> Dict[str, Any]`
  - Persists new claim in database
  - Timeout: 45 seconds
  - Retry: 3 attempts with exponential backoff
  - **TODO**: Implement actual database insert (currently generates timestamp-based claim ID)

### workflow.py
Workflow orchestration with complex control flow.

**Exports**:
- `InsuranceClaimWorkflow` - Main workflow class

**Public Methods**:
- `run(input: WorkflowInput) -> WorkflowOutput` - Main workflow execution
- **Update Handlers**:
  - `submit_claim(submission: ClaimSubmission) -> ClaimSubmissionResult` - Customer submits claim
  - `submit_assessor_findings(findings: AssessorFindings) -> AssessorFindingsResult` - Assessor evaluation
  - `submit_investigation_findings(findings: InvestigationFindings) -> InvestigationFindingsResult` - Investigation report (conditional)
- **Query Handlers**:
  - `get_status() -> Dict[str, Any]` - Current workflow status and stage
  - `get_claim_details() -> Optional[Dict[str, Any]]` - Submitted claim details
  - `get_damage_summary() -> Optional[Dict[str, Any]]` - Damage assessment summary

**Private Methods** (inline transformations):
- `_map_policies_to_menu_items(policies: List[Policy]) -> List[PolicyMenuItem]` - Transform policies for UI
- `_determine_price_of_damage(visible_assesments: List[DamageAssessment], assessor_rationale: str) -> DamageCalculationResult` - Complex cost calculation with coverage percentages

**Control Flow**:
1. Find customer policies (activity)
2. Transform policies to menu items (inline)
3. Wait for claim submission (Update handler)
4. Validate policy type is AUTO (SWITCH)
   - If not AUTO: Terminate with invalid policy error
   - If AUTO:
     a. Create claim in database (activity)
     b. Wait for assessor findings (Update handler)
     c. Check if incident covered (SWITCH)
        - If not covered: Terminate
        - If covered:
          i. Calculate damage costs (inline)
          ii. Check if cost exceeds threshold (SWITCH)
              - If exceeds threshold:
                * Wait for investigation findings (Update handler)
                * Re-check coverage after investigation (SWITCH)
                  - If not covered: Terminate
                  - If covered: Continue to completion
              - If normal cost: Continue to completion
          iii. Terminate with success (send payment to client)

### worker.py
Worker registration and execution.

**Entry Point**: `worker:main` (console script)

**Responsibilities**:
- Connect to Temporal server (localhost:7233 by default)
- Register workflow and activities
- Poll task queue: `insurance-claim-task-queue`
- Handle graceful shutdown on SIGINT/SIGTERM
- Manage PID file for process tracking

**Configuration**:
- Task queue: `insurance-claim-task-queue`
- Server address: Configurable via environment or parameter
- Worker identity: Auto-generated

### starter.py
Workflow starter client.

**Entry Point**: `starter:main` (console script)

**Responsibilities**:
- Connect to Temporal server
- Start workflow with example input (John Smith)
- Display workflow ID and Web UI URL
- Wait for workflow completion
- Display final result

**Configuration**:
- Task queue: `insurance-claim-task-queue` (must match worker)
- Workflow ID: Auto-generated with timestamp
- Example input: `WorkflowInput(first_name="John", last_name="Smith")`

**Output**:
- Workflow ID for interaction
- Web UI URL for monitoring
- Instructions for interacting via Updates
- Final result when workflow completes

### interact.py
Workflow interaction client for Updates, Signals, and Queries.

**Entry Point**: `interact:main` (console script)

**Commands**:
- `interact update <workflow-id> <update-name> '<json-args>'` - Send Update with validation feedback
- `interact query <workflow-id> <query-name>` - Execute Query for status checking
- `interact` - Display usage help

**Supported Updates**:
- `submit_claim` - Submit customer claim with policy selection and incident description
- `submit_assessor_findings` - Submit assessor evaluation with damage assessments
- `submit_investigation_findings` - Submit investigation findings for high-cost claims

**Supported Queries**:
- `get_status` - Get current workflow status and stage
- `get_claim_details` - Get submitted claim details
- `get_damage_summary` - Get damage assessment summary

**Example Usage**:
```bash
# Submit claim
uv run interact update insurance-claim-abc123 submit_claim '{
  "policy_picker": "POL-AUTO-001",
  "incident_description": "Minor fender bender"
}'

# Check status
uv run interact query insurance-claim-abc123 get_status
```

## Usage

See the main project README.md for complete setup and usage instructions.

### Quick Start

```bash
# Install dependencies
uv sync --all-extras

# Start worker
uv run worker

# In another terminal, start workflow
uv run starter

# In a third terminal, interact with workflow
uv run interact update <workflow-id> submit_claim '{"policy_picker": "POL-AUTO-001", "incident_description": "Minor accident"}'
uv run interact update <workflow-id> submit_assessor_findings '{"visible_assesments": [...], "overall_coverage": "yes", ...}'
# If cost > $100:
uv run interact update <workflow-id> submit_investigation_findings '{"investigation_findings": "...", ...}'

# Query status
uv run interact query <workflow-id> get_status
```

## Development

When modifying this module:

1. **Maintain strict type hints** - All functions must have complete type annotations
2. **Update docstrings** - Keep documentation in sync with code changes
3. **Run validation**:
   ```bash
   mypy insurance_claim_temporal --strict --ignore-missing-imports
   python3 -m py_compile insurance_claim_temporal/*.py
   ```
4. **Test with worker and starter** - Always test changes end-to-end
5. **Preserve migration references** - Keep Conductor task references in comments

### Customization Points

1. **Activity Implementations**:
   - Replace TODO placeholders in `activities.py`
   - Implement actual database queries and writes
   - Add error handling for business logic failures

2. **Cost Configuration**:
   - Update `DAMAGE_COST_MAP` in `shared.py` with actual damage type costs
   - Adjust `INVESTIGATION_COST_THRESHOLD` to realistic production value ($5,000+)

3. **Timeout Configuration**:
   - Adjust activity timeouts in `workflow.py` based on performance testing
   - Adjust human interaction wait times based on business SLAs

4. **Validation Rules**:
   - Enhance Update handler validation in `workflow.py`
   - Add business-specific validation rules

## Migration Context

This module was automatically migrated from Conductor workflow definition to Temporal Python SDK.

**Original Conductor Workflow**: `conductor-definition/insurance_claim.json`
**Migration Date**: November 23, 2025
**Migration Quality**: HIGH - All complexity successfully translated

**Key Migration Decisions**:
- SIMPLE tasks → Activities with explicit timeouts and retry policies
- INLINE tasks → Pure Python methods in workflow class
- HUMAN tasks → Update handlers with validation
- SWITCH tasks → Native Python if/elif/else statements
- TERMINATE tasks → return WorkflowOutput with distinct status values

**See Also**:
- [CONDUCTOR_COMPARISON.md](../CONDUCTOR_COMPARISON.md) - Side-by-side Conductor vs Temporal code examples
- [CONDUCTOR_MIGRATION_NOTES.md](../CONDUCTOR_MIGRATION_NOTES.md) - Migration decisions and customization recommendations
- [VALIDATION_REPORT.md](../VALIDATION_REPORT.md) - Code quality validation results
- [WORKFLOW_EXECUTION_REPORT.md](../WORKFLOW_EXECUTION_REPORT.md) - End-to-end execution test results

---

**Package Version**: 0.1.0
**Python Requirement**: >=3.11
**Temporal SDK**: >=1.5.0
**Type Checking**: mypy --strict compliant
**Code Quality**: 100% type coverage, all validations passed

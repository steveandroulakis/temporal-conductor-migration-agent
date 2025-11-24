# Conductor to Temporal: Migration Notes

**Migration Date**: November 23, 2025
**Original Workflow**: conductor-definition/insurance_claim.json
**Complexity**: HIGH

---

## Migration Overview

This document records the decisions, assumptions, and considerations made during the automatic migration from Conductor to Temporal for the **insurance_claim** workflow.

## Workflow Characteristics

### Complexity Analysis
- **Max Nesting Depth**: 5 levels
- **Has Loops**: No
- **Has Parallel Execution**: No
- **Has Dynamic Parallelism**: No
- **Has Sub-workflows**: No
- **Complexity Score**: HIGH

### Task Breakdown
- **Total Conductor Tasks**: 15
- **SIMPLE tasks**: 2 → 2 Temporal activities
- **INLINE tasks**: 2 → 2 Python methods in workflow
- **HUMAN tasks**: 3 → 3 Update handlers with validation
- **SWITCH tasks**: 4 → 4 if/elif conditional branches
- **TERMINATE tasks**: 4 → 4 return statements with distinct outcomes

### Complexity Factors
1. **Deep nesting**: 5 levels (policy_valid → incident_covered_by_policy → exceed_cost → investigation → after_investigation → terminate)
2. **Multiple nested SWITCH tasks**: 4 SWITCH tasks at different nesting levels creating complex decision tree
3. **3 HUMAN_TASK tasks**: Requiring external input and state management at different nesting levels
4. **2 complex INLINE tasks**: Significant JavaScript logic for data transformation (90+ lines for damage calculation)
5. **Multiple termination paths**: 4 distinct TERMINATE tasks with different outcomes
6. **Complex data flow**: Outputs from early tasks used deep in nested structures
7. **Conditional branching**: Each decision level significantly affects overall execution path

---

## Migration Decisions

### 1. Control Flow Translation

#### SWITCH to if/elif Translation
**Decision**: Translate all 4 SWITCH tasks to native Python if/elif/else statements
**Rationale**: Python conditionals are more readable, maintainable, and type-safe than custom switch implementations
**Alternative Approaches**: Could have used match/case (Python 3.10+) or dictionary dispatch patterns

#### Pattern: Policy Validation SWITCH
**Conductor**: JavaScript expression checking if policy type is "AUTO"
**Temporal**: Python for loop finding selected policy, then if/else comparison
**Decision Rationale**: More explicit and debuggable than ternary or dictionary lookup

#### Pattern: Coverage Check SWITCH
**Conductor**: JavaScript expression `if($.overall_coverage!="Not Covered"){ return "yes" }`
**Temporal**: Direct Python comparison `if self._assessor_findings.overall_coverage == "Not Covered"`
**Decision Rationale**: More readable and explicit than negation logic

#### Pattern: Cost Threshold SWITCH
**Conductor**: JavaScript `if($.totalCost>100){ return "yes" }`
**Temporal**: Python with configurable constant `if total_covered_cost > INVESTIGATION_COST_THRESHOLD`
**Decision Rationale**: Extracted threshold to constant for configurability, better than hardcoded value

#### Pattern: Post-Investigation Check SWITCH
**Conductor**: References non-existent output field `${incident_covered_by_policy_ref.output.covered}`
**Temporal**: Uses assessor's overall_coverage as basis for decision
**Decision Rationale**: Original Conductor workflow had ambiguous reference. We use the most logical available data. Production may need to parse investigation_findings text.

### 2. Human Interaction Patterns

#### Pattern 1: Claim Submission (take_claim_ref)
**Conductor Pattern**: HUMAN task with form template "claimant_locator_form"
**Temporal Mechanism**: Update handler with validation
**Decision Rationale**:
- Update chosen over Signal for validation feedback
- Customer needs immediate confirmation of accepted claim submission
- Validation ensures policy_picker is valid and incident_description meets minimum length
- Cannot submit twice (idempotency check)

**Validation Rules**:
- Policy selection required (non-empty)
- Incident description minimum 10 characters
- Duplicate submission prevented

**Decision Criteria**:
- Claim submission is critical path - workflow cannot proceed without valid data
- User experience benefits from immediate feedback on validation errors
- Update provides synchronous response vs Signal's fire-and-forget

#### Pattern 2: Assessor Findings (assesor_findings_ref)
**Conductor Pattern**: HUMAN task with form template "assesor_report"
**Temporal Mechanism**: Update handler with validation
**Decision Rationale**:
- Assessor needs confirmation that findings were recorded correctly
- Complex data structure (array of assessments) benefits from validation
- Returns immediate feedback on acceptance

**Validation Rules**:
- At least one damage assessment required (non-empty array)
- Overall coverage determination required (non-empty string)
- Duplicate submission prevented

**Data Complexity**:
- Input includes array of DamageAssessment objects
- Multiple output fields: assessments, coverage, rationale, location
- All fields strongly typed with dataclasses

#### Pattern 3: Investigation Findings (investigation_human_ref)
**Conductor Pattern**: HUMAN task with form template "on_site_investigation"
**Temporal Mechanism**: Update handler with validation
**Decision Rationale**:
- Only triggered conditionally (cost > $100)
- Investigator needs confirmation of submission
- Investigation findings influence final coverage decision

**Validation Rules**:
- Investigation findings cannot be empty
- Duplicate submission prevented
- Witness statements optional

**Conditional Execution**:
- Only executed when exceed_cost SWITCH returns "yes"
- Workflow state indicates when investigation is required
- Queries allow checking if investigation step is active

### 3. Activity Design

**Decision**: Created 2 activities from Conductor SIMPLE tasks

#### Activity 1: find_policy_for_customer
**Conductor Task**: findPolicyForCustomer (SIMPLE)
**Timeout Strategy**: 30 seconds (database query should be fast)
**Retry Policy**: Exponential backoff, 3 attempts, 1s initial interval, 2.0 coefficient
**Rationale**: Database queries are fast but may fail transiently (network, connection pool). Short timeout with retries balances responsiveness and resilience.

#### Activity 2: create_claim_for_policy
**Conductor Task**: createClaimForPolicy (SIMPLE)
**Timeout Strategy**: 45 seconds (database write with potential validations)
**Retry Policy**: Exponential backoff, 3 attempts, 2s initial interval, 2.0 coefficient
**Rationale**: Database writes may take longer than reads due to validation, indexes, triggers. Slightly longer timeout and retry interval.

**Common Retry Strategy**:
- Maximum attempts: 3 (balance between resilience and failing fast)
- Backoff coefficient: 2.0 (standard exponential backoff)
- Non-retryable errors: Not specified (could add for business logic failures)

### 4. Inline Task Translation

**Decision**: Translate 2 INLINE tasks to Python methods in workflow class

#### Inline Task 1: map_policies_to_menu_items
**Conductor**: JavaScript map function (simple)
**Temporal**: Python list comprehension
**Rationale**: Pure data transformation, no side effects, deterministic. No need for activity.
**Translation**: `$.policies.map(p => ({ "const": p.policy_number, title: p.policy_type }))` → List comprehension creating PolicyMenuItem objects

#### Inline Task 2: determine_price_of_damage
**Conductor**: Complex 90+ line JavaScript with:
- Cost map lookup
- Array map transformation
- Array reduce for aggregation
- Complex conditional logic for coverage calculation

**Temporal**: Clean 50-line Python method with:
- Dictionary lookup for costs (DAMAGE_COST_MAP constant)
- For loop with list append for items
- Simple variable accumulation for totals
- Clear if/else for coverage logic

**Rationale**:
- Complex logic but deterministic - safe for workflow
- Extracted cost map to shared constant for reusability and configurability
- Python implementation more readable than JavaScript
- Strong typing prevents errors (coverage_score is int, not ambiguous)

**Alternative Considered**: Could have made this an activity, but it's pure computation with no I/O, so keeping it in workflow is more efficient and maintains locality of business logic.

### 5. Data Type Mapping

**Conductor Input Parameters** → **Temporal Dataclasses**

**Workflow Level**:
- `firstName` (string) → `first_name: str` in WorkflowInput
- `lastName` (string) → `last_name: str` in WorkflowInput

**Activity Level**:
- FindPolicyForCustomer inputs → `FindPolicyInput(first_name, last_name)`
- CreateClaimForPolicy inputs → `CreateClaimInput(policy_id, description)`

**Human Interaction Level**:
- take_claim outputs → `ClaimSubmission(policy_picker, incident_description)`
- assesor_findings outputs → `AssessorFindings(visible_assesments, overall_coverage, rationale, incident_city, incident_street, incident_state)`
- investigation outputs → `InvestigationFindings(investigation_findings, witness_statements)`

**Damage Calculation**:
- Damage assessment → `DamageAssessment(damage_type, coverage_determination, coverage_score)`
- Calculation result → `DamageCalculationResult(damage_estimation, coverage_calculation)`

**Design Decisions**:
- All fields have explicit types (no `Any`)
- Optional fields use `Optional[T]` type hint
- Arrays → `List[T]` with explicit element type
- Dicts → `Dict[str, Any]` for flexible JSON-like data (claim_result from activity)
- Constants defined for magic values (DAMAGE_COST_MAP, INVESTIGATION_COST_THRESHOLD)

---

## Assumptions Made

1. **Activity Implementations**: Activity functions contain placeholder implementations marked with TODO comments. These need to be filled in with actual business logic based on the original Conductor task implementations. Specifically:
   - `find_policy_for_customer`: Replace sample policies with actual database query
   - `create_claim_for_policy`: Replace timestamp-based claim_id generation with actual database insert

2. **Timeout Values**:
   - Activity timeouts derived from typical database operation times (30s reads, 45s writes)
   - Human interaction timeouts set based on business context:
     - Claim submission: 72 hours (customers may need time to gather information)
     - Assessor findings: 48 hours (assessor needs to travel to site)
     - Investigation: 24 hours (urgent for high-cost claims)
   - These are reasonable defaults but should be validated against actual business SLAs

3. **Example Input Data**: The starter.py generates example input data (John Smith) based on typical customer names. This should be customized for:
   - Testing: Use test data that exercises all execution paths
   - Production: Accept input from external systems or user interfaces

4. **Form Templates**: Conductor references three form templates:
   - `claimant_locator_form` (version 1)
   - `assesor_report` (version 1)
   - `on_site_investigation` (version 1)

   These forms need to be implemented in a separate UI layer that calls the Temporal Update handlers.

5. **Post-Investigation Coverage Check**: The original Conductor workflow references `${incident_covered_by_policy_ref.output.covered}` which is not clearly defined in the SWITCH task output. We assume:
   - The initial coverage determination (from assessor) remains valid
   - Production implementation may need to parse `investigation_findings` text to determine if coverage should be revoked
   - This is flagged in code comments for review

6. **Cost Threshold**: The $100 threshold is intentionally low for demonstration purposes. Production systems should use realistic thresholds (e.g., $5,000 or higher) based on business risk tolerance.

---

## Known Limitations

1. **Complex JSONPath Expressions**: The Conductor workflow uses relatively simple JSONPath expressions. More complex expressions (with filters, projections, nested paths) would require more sophisticated translation logic.

2. **Investigation Coverage Logic**: The `after_investigation_is_it_covered` SWITCH references an output field that doesn't clearly exist. Current implementation uses the assessor's initial coverage determination. Production may need to:
   - Parse investigation_findings text for keywords
   - Add a structured field to InvestigationFindings for coverage override
   - Implement business rules for when investigation can override initial assessment

3. **External Dependencies**: The workflow assumes:
   - Customer database accessible for policy lookup
   - Claims database writable for claim creation
   - No external API integrations (all business logic is internal)

   If the original Conductor implementation used external services, those need to be integrated into activities.

4. **Form Template Versions**: The workflow specifies form versions (version 1) but doesn't validate that the UI is using matching versions. Production should:
   - Implement form version checking
   - Handle form schema evolution
   - Provide migration paths for in-flight workflows when forms change

5. **Idempotency**: Activities use TODO placeholders for actual implementation. Production implementations should be idempotent:
   - `find_policy_for_customer`: Safe (read-only)
   - `create_claim_for_policy`: Needs duplicate claim detection (check if claim already exists for policy + similar description + timeframe)

---

## Customization Recommendations

### Immediate Customizations Needed

1. **Activity Implementations**: Review all TODO comments in `activities.py` and implement actual business logic:

   **find_policy_for_customer**:
   ```python
   # TODO: Replace with actual database query
   # Example using SQLAlchemy:
   # async with db_session() as session:
   #     policies = await session.execute(
   #         select(Policy).where(
   #             Policy.customer_first_name == input_data.first_name,
   #             Policy.customer_last_name == input_data.last_name
   #         )
   #     )
   #     return FindPolicyOutput(policies=policies.scalars().all())
   ```

   **create_claim_for_policy**:
   ```python
   # TODO: Replace with actual database transaction
   # Example:
   # async with db_session() as session:
   #     # Check for duplicate claims
   #     existing = await session.execute(
   #         select(Claim).where(
   #             Claim.policy_id == input_data.policy_id,
   #             Claim.created_at > datetime.now() - timedelta(days=7)
   #         )
   #     )
   #     if existing.scalar():
   #         raise DuplicateClaimError("Claim already exists")
   #
   #     # Create new claim
   #     claim = Claim(
   #         policy_id=input_data.policy_id,
   #         description=input_data.description,
   #         status="pending",
   #         created_at=datetime.now()
   #     )
   #     session.add(claim)
   #     await session.commit()
   #     return {"claim_id": claim.id, ...}
   ```

2. **Workflow Input**: Update example data in `starter.py` to match your use case:
   ```python
   # For testing: Use test customers that cover all execution paths
   test_cases = [
       WorkflowInput(first_name="John", last_name="AutoCustomer"),  # Has AUTO policy
       WorkflowInput(first_name="Jane", last_name="HomeCustomer"),  # Only HOME policy (will terminate)
   ]

   # For production: Accept input from external system
   workflow_input = WorkflowInput(
       first_name=request.get("first_name"),
       last_name=request.get("last_name")
   )
   ```

3. **Timeout Configuration**: Review and adjust timeouts based on your activity performance:
   ```python
   # In workflow.py
   # Measure actual activity execution times in production
   # Set timeout to P95 latency + buffer
   start_to_close_timeout=timedelta(seconds=30)  # Adjust based on testing
   ```

### Optional Enhancements

1. **Error Handling**: Add specific exception handling for business logic failures:
   ```python
   try:
       find_policy_result = await workflow.execute_activity(...)
   except ActivityError as e:
       if "CustomerNotFound" in str(e):
           return WorkflowOutput(
               status="TERMINATED",
               reason="Customer not found in database",
               details={"error": str(e)}
           )
       raise
   ```

2. **Logging**: Enhance logging with additional context for debugging:
   ```python
   workflow.logger.info(
       "Claim submission received",
       extra={
           "policy_id": submission.policy_picker,
           "customer": f"{input.first_name} {input.last_name}",
           "incident_length": len(submission.incident_description)
       }
   )
   ```

3. **Monitoring**: Add custom metrics and observability:
   ```python
   from temporalio import workflow

   # Increment metric for claim submissions
   workflow.metric_meter().counter("claim_submissions_total").add(1)

   # Track investigation rate
   if total_covered_cost > INVESTIGATION_COST_THRESHOLD:
       workflow.metric_meter().counter("investigations_triggered_total").add(1)
   ```

4. **Testing**: Create unit tests for activities and integration tests for workflows:
   ```python
   # tests/test_activities.py
   async def test_find_policy_for_customer():
       input_data = FindPolicyInput(first_name="John", last_name="Smith")
       result = await find_policy_for_customer(input_data)
       assert len(result.policies) > 0
       assert all(p.policy_type in ["AUTO", "HOME", "LIFE"] for p in result.policies)

   # tests/test_workflow.py
   async def test_insurance_claim_workflow_success_path():
       async with await WorkflowEnvironment.start_time_skipping() as env:
           # Start workflow
           async with Worker(
               env.client,
               task_queue="test-task-queue",
               workflows=[InsuranceClaimWorkflow],
               activities=[find_policy_for_customer, create_claim_for_policy],
           ):
               handle = await env.client.start_workflow(
                   InsuranceClaimWorkflow.run,
                   WorkflowInput(first_name="John", last_name="Smith"),
                   id="test-workflow",
                   task_queue="test-task-queue",
               )

               # Submit claim
               await handle.execute_update(
                   InsuranceClaimWorkflow.submit_claim,
                   ClaimSubmission(
                       policy_picker="POL-AUTO-001",
                       incident_description="Test incident"
                   )
               )

               # Submit assessor findings
               # ... continue test scenario
   ```

5. **UI Integration**: Build web forms for human interactions:
   - React/Vue/Angular frontend
   - Form validation matching Update handler validation
   - Real-time status updates via Queries
   - Workflow URL display for tracking
   - Example:
     ```typescript
     // claim-submission-form.tsx
     async function submitClaim(workflowId: string, data: ClaimSubmission) {
       const client = new TemporalClient({ ... });
       const handle = client.getHandle(workflowId);

       try {
         const result = await handle.executeUpdate("submit_claim", data);
         showSuccess(result.message);
       } catch (error) {
         showError(error.message);
       }
     }
     ```

---

## Future Considerations

### 1. Scalability
For high-volume workflows, consider:

**Activity Batching**:
```python
# Instead of looking up policies one customer at a time
# Batch multiple lookups:
async def find_policies_batch(customers: List[CustomerInput]) -> Dict[str, List[Policy]]:
    # Single database query for all customers
    # Return mapping of customer → policies
    pass
```

**Worker Scaling Strategies**:
- Horizontal scaling: Deploy multiple worker instances
- Task queue partitioning: Use separate task queues for different workflow types
- Activity execution limits: Configure concurrent_activity_execution_size
- Resource-based routing: Route expensive activities to dedicated workers

**Temporal Cloud for Production**:
- Managed service eliminates infrastructure overhead
- Built-in high availability and disaster recovery
- Enterprise-grade security and compliance
- Visibility and monitoring out of the box

### 2. Continue-As-New
The workflow does not include loops, so continue-as-new is not currently needed. However, if the workflow is extended to support:
- Recurring claim processing
- Long-running claims with periodic status checks
- Iterative approval cycles

Then implement continue-as-new to prevent history size growth:
```python
# In workflow.py
if workflow.info().get_current_history_length() > 10000:
    # Continue as new to reset history
    raise ContinueAsNew(input)
```

### 3. Human Interaction UI
Consider building a comprehensive UI for human approvals:

**Features**:
- Dashboard showing all pending claims awaiting action
- Real-time status updates via Queries
- Form validation matching Update handler validation
- Workflow timeline/history visualization
- Mobile-responsive design for field assessors
- Push notifications for urgent investigations

**Architecture**:
- Frontend: React/Vue/Angular
- Backend API: REST/GraphQL layer wrapping Temporal client
- Authentication: OAuth2/SAML for enterprise users
- Authorization: Role-based access control (adjusters, investigators, approvers)

**Example API Endpoint**:
```python
# api/claims.py
@router.post("/claims/{workflow_id}/submit-claim")
async def submit_claim_api(
    workflow_id: str,
    submission: ClaimSubmission,
    current_user: User = Depends(get_current_user)
):
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)

    try:
        result = await handle.execute_update(
            InsuranceClaimWorkflow.submit_claim,
            submission
        )

        # Audit log
        await log_action(
            user=current_user,
            workflow_id=workflow_id,
            action="submit_claim",
            result=result
        )

        return result
    except ApplicationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 4. Workflow Versioning
As the workflow evolves, implement versioning strategies:

**Version Guarding**:
```python
@workflow.defn
class InsuranceClaimWorkflow:
    def __init__(self) -> None:
        self._version = workflow.unsafe.get_version("workflow", 1, 2)

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        if self._version == 1:
            # Original logic
            pass
        else:
            # New logic
            pass
```

**Data Migration**:
```python
# Handle old workflows with new code
if not hasattr(self, "_investigation_findings"):
    # Old workflow didn't have investigation
    self._investigation_findings = None
```

### 5. Advanced Patterns

**Saga Pattern for Compensation**:
```python
# If claim creation needs to be rolled back
try:
    claim_result = await workflow.execute_activity(create_claim_for_policy, ...)
    # ... rest of workflow
except Exception:
    # Compensate by deleting the claim
    await workflow.execute_activity(delete_claim, claim_id=claim_result["claim_id"])
    raise
```

**Child Workflows for Sub-processes**:
```python
# If damage assessment becomes complex, extract to child workflow
damage_assessment = await workflow.execute_child_workflow(
    DamageAssessmentWorkflow.run,
    DamageAssessmentInput(visible_assesments=...),
    id=f"damage-assessment-{workflow.info().workflow_id}"
)
```

**Dynamic Activities**:
```python
# If activity name is determined at runtime
activity_name = f"validate_{policy_type.lower()}_claim"
result = await workflow.execute_activity(
    activity_name,
    args=[...],
    start_to_close_timeout=timedelta(seconds=30)
)
```

---

## Validation Results

See `VALIDATION_REPORT.md` for detailed validation results.

**Summary**:
- Syntax Validation: PASS
- Type Checking (mypy --strict): PASS
- Sandbox Compliance: PASS
- Configuration Validation: PASS
- Console Scripts: PASS
- Activity Argument Counts: PASS
- Dataclass Type Hints: PASS
- Restricted Workflow Calls: PASS
- RetryPolicy Import: PASS

**Overall**: ALL VALIDATIONS PASSED

**Fixes Applied**: 4 minor fixes for type narrowing and SDK typing limitations

---

## Execution Results

See `WORKFLOW_EXECUTION_REPORT.md` for detailed execution results.

**Summary**:
- Workflow executed successfully end-to-end
- All 3 Update handlers functioned correctly with validation
- Complex control flow handled correctly (5-level nesting)
- Cost calculation accurate ($500 triggered investigation)
- Multiple termination paths validated
- Business result: COMPLETED - Payment authorized

**Test Scenario**: High-cost claim requiring investigation
- Claim submission: POL-AUTO-001, minor fender bender
- Assessor findings: Minor front door damage, $500, 100% covered
- Investigation: No fraud detected, legitimate claim
- Result: Payment authorized for $500

---

## References

- Original Conductor workflow: `conductor-definition/insurance_claim.json`
- Conductor Primitives Reference: [conductor-migration/conductor-primitives-reference.md](./conductor-migration/conductor-primitives-reference.md)
- Temporal Python SDK: https://docs.temporal.io/develop/python
- Migration comparison: [CONDUCTOR_COMPARISON.md](./CONDUCTOR_COMPARISON.md)

---

**Migration Tool Version**: 1.0
**Generated**: November 23, 2025
**Migration Agent**: Conductor to Temporal Migration Tool (8-Agent Pipeline)
**Migration Quality**: HIGH - All complexity successfully translated with 100% task coverage

"""Workflow definition for insurance claim processing.

This workflow migrates the Conductor insurance_claim workflow to Temporal Python.

Control Flow:
1. Find customer policies (activity)
2. Transform policies to menu items (inline Python function)
3. Wait for claim submission (human input via Update)
4. Validate policy type is AUTO (SWITCH)
   - If not AUTO: Terminate with invalid policy error
   - If AUTO:
     a. Create claim in database (activity)
     b. Wait for assessor findings (human input via Update)
     c. Check if incident covered (SWITCH)
        - If not covered: Terminate
        - If covered:
          i. Calculate damage costs (inline Python function)
          ii. Check if cost exceeds threshold (SWITCH)
              - If exceeds threshold:
                * Wait for investigation findings (human input via Update)
                * Re-check coverage after investigation (SWITCH)
                  - If not covered: Terminate
                  - If covered: Continue to completion
              - If normal cost: Continue to completion
          iii. Terminate with success (send payment to client)

Original Conductor workflow: insurance_claim.json
Complexity: HIGH
Max nesting depth: 5 levels
Human interaction points: 3 (claim submission, assessor, investigation)
"""
import asyncio
from datetime import timedelta
from typing import Optional, Dict, Any, List
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from .shared import (
        WorkflowInput,
        WorkflowOutput,
        FindPolicyInput,
        FindPolicyOutput,
        Policy,
        PolicyMenuItem,
        CreateClaimInput,
        ClaimSubmission,
        ClaimSubmissionResult,
        AssessorFindings,
        AssessorFindingsResult,
        InvestigationFindings,
        InvestigationFindingsResult,
        DamageAssessment,
        DamageItem,
        DamageEstimation,
        CoverageCalculation,
        DamageCalculationResult,
        DAMAGE_COST_MAP,
        INVESTIGATION_COST_THRESHOLD,
    )
    # Import specific activity functions by name (NOT the entire activities module)
    # This prevents workflow sandbox violations if activities.py has non-deterministic imports
    from .activities import find_policy_for_customer, create_claim_for_policy


# Default retry policy for activities
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=100),
    maximum_attempts=3,
    backoff_coefficient=2.0
)


@workflow.defn
class InsuranceClaimWorkflow:
    """Temporal workflow for processing insurance claims with human approvals.

    This workflow implements a complex insurance claim processing flow with:
    - Initial policy lookup and validation
    - Human claim submission
    - Assessor evaluation
    - Dynamic cost calculation
    - Conditional investigation for high-cost claims
    - Multiple termination paths based on coverage decisions

    Original Conductor workflow: conductor-definition/insurance_claim.json
    Complexity: HIGH (deep nesting with 5 levels, 4 SWITCH tasks, 3 HUMAN tasks)

    Human Interaction Points:
    1. submit_claim: Customer submits claim with policy selection and incident details
    2. submit_assessor_findings: Assessor evaluates damage and coverage on-site
    3. submit_investigation_findings: Investigator provides findings for high-cost claims

    Termination Paths:
    1. Invalid policy (not AUTO type)
    2. Incident not covered by policy (initial assessment)
    3. Incident not covered after investigation (high-cost claims)
    4. Success - claim approved and payment authorized
    """

    def __init__(self) -> None:
        """Initialize workflow state for human interactions."""
        # State for claim submission (HUMAN_TASK: take_claim_ref)
        self._claim_submission: Optional[ClaimSubmission] = None

        # State for assessor findings (HUMAN_TASK: assesor_findings_ref)
        self._assessor_findings: Optional[AssessorFindings] = None

        # State for investigation findings (HUMAN_TASK: investigation_human_ref)
        self._investigation_findings: Optional[InvestigationFindings] = None

        # Status tracking for queries
        self._status: str = "started"
        self._current_stage: str = "policy_lookup"

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        """Execute the insurance claim workflow.

        Args:
            input: WorkflowInput containing first_name and last_name

        Returns:
            WorkflowOutput with status, reason, and optional details

        Raises:
            ApplicationError: On unrecoverable business logic failures
        """
        workflow.logger.info(
            f"Starting insurance claim workflow for {input.first_name} {input.last_name}"
        )

        # Task 1: Find customer policies
        # Conductor task: findPolicyForCustomer_ref (SIMPLE)
        self._current_stage = "finding_policies"
        find_policy_input = FindPolicyInput(
            first_name=input.first_name,
            last_name=input.last_name
        )

        find_policy_result = await workflow.execute_activity(
            find_policy_for_customer,
            args=[find_policy_input],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY
        )

        workflow.logger.info(
            f"Found {len(find_policy_result.policies)} policies for customer"
        )

        # Task 2: Transform policies to menu items
        # Conductor task: map_policies_to_menu_items_ref (INLINE)
        # Original JavaScript: $.policies.map(p => ({ "const": p.policy_number, title: p.policy_type }))
        policy_menu_items = self._map_policies_to_menu_items(find_policy_result.policies)

        workflow.logger.info(
            f"Transformed {len(policy_menu_items)} policies to menu items"
        )

        # Task 3: Wait for human claim submission
        # Conductor task: take_claim_ref (HUMAN_TASK)
        self._current_stage = "awaiting_claim_submission"
        await workflow.wait_condition(
            lambda: self._claim_submission is not None,
            timeout=timedelta(hours=72)  # Allow 3 days for claim submission
        )

        # Assert not None after wait_condition for type checking
        assert self._claim_submission is not None

        workflow.logger.info(
            f"Claim submitted for policy: {self._claim_submission.policy_picker}"
        )

        # Task 4: SWITCH - Validate policy type
        # Conductor task: policy_valid_ref (SWITCH)
        # Original condition: Check if selected policy type is "AUTO"
        self._current_stage = "validating_policy"

        # Find the selected policy from menu items
        selected_policy_type: Optional[str] = None
        for menu_item in policy_menu_items:
            if menu_item.const == self._claim_submission.policy_picker:
                selected_policy_type = menu_item.title
                break

        if selected_policy_type != "AUTO":
            # DEFAULT CASE: Policy is not valid (not AUTO type)
            # Conductor task: terminate_by_invalid_policy_ref (TERMINATE)
            workflow.logger.warning(
                f"Policy type {selected_policy_type} is not valid (expected AUTO)"
            )
            self._status = "terminated"
            self._current_stage = "terminated_invalid_policy"

            return WorkflowOutput(
                status="TERMINATED",
                reason="Terminated because of invalid policy",
                details={
                    "error": f"Invalid policy {self._claim_submission.policy_picker}",
                    "policy_type": selected_policy_type,
                    "expected_type": "AUTO"
                }
            )

        # YES CASE: Policy is AUTO - proceed with claim processing
        workflow.logger.info("Policy validated as AUTO type - proceeding with claim")

        # Task 5: Create claim in database
        # Conductor task: createClaimForPolicy_ref (SIMPLE, nesting level 1)
        self._current_stage = "creating_claim"
        create_claim_input = CreateClaimInput(
            policy_id=self._claim_submission.policy_picker,
            description=self._claim_submission.incident_description
        )

        claim_result = await workflow.execute_activity(
            create_claim_for_policy,
            args=[create_claim_input],
            start_to_close_timeout=timedelta(seconds=45),
            retry_policy=DEFAULT_RETRY_POLICY
        )

        workflow.logger.info(
            f"Claim created: {claim_result.get('claim_id')}"
        )

        # Task 6: Wait for assessor findings
        # Conductor task: assesor_findings_ref (HUMAN_TASK, nesting level 1)
        self._current_stage = "awaiting_assessor_findings"
        await workflow.wait_condition(
            lambda: self._assessor_findings is not None,
            timeout=timedelta(hours=48)  # Allow 2 days for assessor evaluation
        )

        # Assert not None after wait_condition for type checking
        assert self._assessor_findings is not None

        workflow.logger.info(
            f"Assessor findings received: overall_coverage={self._assessor_findings.overall_coverage}"
        )

        # Task 7: SWITCH - Check if incident is covered by policy
        # Conductor task: incident_covered_by_policy_ref (SWITCH, nesting level 2)
        # Original condition: if ($.overall_coverage != "Not Covered") { return "yes" }
        self._current_stage = "checking_coverage"

        if self._assessor_findings.overall_coverage == "Not Covered":
            # DEFAULT CASE: Incident not covered
            # Conductor task: terminate_ref_1 (TERMINATE, nesting level 3)
            workflow.logger.warning("Incident not covered by policy")
            self._status = "terminated"
            self._current_stage = "terminated_not_covered"

            return WorkflowOutput(
                status="TERMINATED",
                reason="Policy does not cover incident",
                details={
                    "overall_coverage": self._assessor_findings.overall_coverage,
                    "rationale": self._assessor_findings.rationale
                }
            )

        # YES CASE: Incident is covered - calculate damage and check cost
        workflow.logger.info("Incident is covered - calculating damage costs")

        # Task 8: Calculate damage costs
        # Conductor task: determine_price_of_damage_ref (INLINE, nesting level 3)
        # Complex JavaScript calculation with cost mapping and coverage percentages
        self._current_stage = "calculating_damage"
        damage_calculation = self._determine_price_of_damage(
            self._assessor_findings.visible_assesments,
            self._assessor_findings.rationale
        )

        workflow.logger.info(
            f"Damage calculation complete: total_covered_cost=${damage_calculation.coverage_calculation.total_covered_cost}"
        )

        # Task 9: SWITCH - Check if cost exceeds investigation threshold
        # Conductor task: exceed_cost_ref (SWITCH, nesting level 3)
        # Original condition: if ($.totalCost > 100) { return "yes" }
        self._current_stage = "checking_cost_threshold"

        total_covered_cost = damage_calculation.coverage_calculation.total_covered_cost

        if total_covered_cost > INVESTIGATION_COST_THRESHOLD:
            # YES CASE: Cost exceeds threshold - trigger investigation
            workflow.logger.info(
                f"Cost ${total_covered_cost} exceeds threshold ${INVESTIGATION_COST_THRESHOLD} - investigation required"
            )

            # Task 10: Wait for investigation findings
            # Conductor task: investigation_human_ref (HUMAN_TASK, nesting level 4)
            self._current_stage = "awaiting_investigation"
            await workflow.wait_condition(
                lambda: self._investigation_findings is not None,
                timeout=timedelta(hours=24)  # Allow 1 day for investigation
            )

            # Assert not None after wait_condition for type checking
            assert self._investigation_findings is not None

            workflow.logger.info("Investigation findings received")

            # Task 11: SWITCH - Re-check coverage after investigation
            # Conductor task: after_investigation_is_it_covered_ref (SWITCH, nesting level 4)
            # Original condition: Check if incident_covered_by_policy_ref.output.covered is true
            # Note: The original Conductor references a non-existent output field
            # We'll use the assessor's overall_coverage as the basis for this decision
            # In production, investigation findings might override the initial assessment
            self._current_stage = "checking_post_investigation_coverage"

            # For this implementation, we assume investigation confirms initial coverage
            # In production, you might want to parse investigation_findings to determine coverage
            is_covered_after_investigation = (
                self._assessor_findings.overall_coverage != "Not Covered"
            )

            if not is_covered_after_investigation:
                # DEFAULT CASE: Not covered after investigation
                # Conductor task: terminate_ref (TERMINATE, nesting level 5)
                workflow.logger.warning("Claim not covered after investigation")
                self._status = "terminated"
                self._current_stage = "terminated_after_investigation"

                return WorkflowOutput(
                    status="TERMINATED",
                    reason="Terminated after investigation. Incident not covered",
                    details={
                        "investigation_findings": self._investigation_findings.investigation_findings,
                        "overall_coverage": self._assessor_findings.overall_coverage
                    }
                )

            # YES CASE: Still covered after investigation
            workflow.logger.info("Claim confirmed covered after investigation")

        else:
            # DEFAULT CASE: Normal cost - no investigation needed
            workflow.logger.info(
                f"Cost ${total_covered_cost} is below threshold - no investigation needed"
            )

        # Task 12: Success termination - Send payment to client
        # Conductor task: terminate_ref_2 (TERMINATE, nesting level 3, status COMPLETED)
        # This executes after exceed_cost SWITCH completes (both yes and default paths converge here)
        workflow.logger.info("Claim approved - authorizing payment")
        self._status = "completed"
        self._current_stage = "completed"

        return WorkflowOutput(
            status="COMPLETED",
            reason="Send Payment to client",
            details={
                "claim_id": claim_result.get("claim_id"),
                "policy_id": self._claim_submission.policy_picker,
                "total_covered_cost": damage_calculation.coverage_calculation.total_covered_cost,
                "total_non_covered_cost": damage_calculation.coverage_calculation.total_non_covered_cost,
                "damage_items": [
                    {
                        "description": item.description,
                        "estimated_cost": item.estimated_cost,
                        "covered_percentage": item.covered_percentage
                    }
                    for item in damage_calculation.damage_estimation.items
                ],
                "investigation_required": total_covered_cost > INVESTIGATION_COST_THRESHOLD,
                "location": {
                    "city": self._assessor_findings.incident_city,
                    "street": self._assessor_findings.incident_street,
                    "state": self._assessor_findings.incident_state
                }
            }
        )

    # ========================================================================
    # INLINE TASK IMPLEMENTATIONS (pure Python functions in workflow)
    # ========================================================================

    def _map_policies_to_menu_items(self, policies: List[Policy]) -> List[PolicyMenuItem]:
        """Transform policies array to menu item format for UI.

        Implements Conductor INLINE task: map_policies_to_menu_items_ref
        Original JavaScript: $.policies.map(p => ({ "const": p.policy_number, title: p.policy_type }))

        This is a pure data transformation function - no activity needed.

        Args:
            policies: List of Policy objects from find_policy_for_customer activity

        Returns:
            List of PolicyMenuItem objects with const (policy_number) and title (policy_type)
        """
        return [
            PolicyMenuItem(
                const=policy.policy_number,
                title=policy.policy_type
            )
            for policy in policies
        ]

    def _determine_price_of_damage(
        self,
        visible_assesments: List[DamageAssessment],
        assessor_rationale: str
    ) -> DamageCalculationResult:
        """Calculate damage costs with coverage percentages and aggregation.

        Implements Conductor INLINE task: determine_price_of_damage_ref
        Original JavaScript: Complex calculation with cost mapping, coverage percentages, and aggregation

        Business Logic:
        1. Map each damage type to predefined cost (DAMAGE_COST_MAP)
        2. Apply coverage percentage to calculate amount covered
        3. Aggregate totals:
           - total_damage_cost: Sum of all estimated costs
           - total_covered_cost: Sum of amounts covered by policy
           - total_non_covered_cost: Sum of amounts not covered

        This is a complex inline transformation with 90+ lines of JavaScript in original Conductor.
        Translated to Python for deterministic execution within workflow.

        Args:
            visible_assesments: List of DamageAssessment from assessor
            assessor_rationale: Assessor's explanation text

        Returns:
            DamageCalculationResult with damage_estimation and coverage_calculation
        """
        # Initialize aggregation variables
        total_damage_cost = 0
        total_covered_cost = 0
        total_non_covered_cost = 0
        items: List[DamageItem] = []

        # Process each damage assessment
        for assessment in visible_assesments:
            # Look up cost from predefined map
            estimated_cost = DAMAGE_COST_MAP.get(assessment.damage_type, 0)

            # Create damage item
            item = DamageItem(
                description=assessment.damage_type,
                estimated_cost=estimated_cost,
                coverage=assessment.coverage_determination,
                covered_percentage=assessment.coverage_score
            )
            items.append(item)

            # Aggregate total damage cost
            total_damage_cost += estimated_cost

            # Calculate coverage
            if assessment.coverage_determination == "Not covered":
                # Fully not covered
                total_non_covered_cost += estimated_cost
            else:
                # Apply coverage percentage
                coverage_percentage = assessment.coverage_score / 100.0
                amount_covered = int(estimated_cost * coverage_percentage)
                total_covered_cost += amount_covered

        # Create result structure matching original Conductor output
        return DamageCalculationResult(
            damage_estimation=DamageEstimation(
                total_damage_cost=total_damage_cost,
                items=items
            ),
            coverage_calculation=CoverageCalculation(
                total_covered_cost=total_covered_cost,
                total_non_covered_cost=total_non_covered_cost,
                explanation=assessor_rationale
            )
        )

    # ========================================================================
    # UPDATE HANDLERS (Human Interaction via Workflow Updates)
    # ========================================================================

    @workflow.update
    async def submit_claim(self, submission: ClaimSubmission) -> ClaimSubmissionResult:
        """Handle claim submission from customer.

        Implements Conductor HUMAN_TASK: take_claim_ref
        Form: claimant_locator_form

        Receives customer's policy selection and incident description.
        Uses Update (not Signal) to provide validation and immediate feedback.

        Args:
            submission: ClaimSubmission with policy_picker and incident_description

        Returns:
            ClaimSubmissionResult confirming acceptance

        Raises:
            ApplicationError: If claim already submitted or invalid input
        """
        # Validation: Ensure claim not already submitted
        if self._claim_submission is not None:
            raise ApplicationError(
                "Claim already submitted",
                non_retryable=True
            )

        # Validation: Check required fields
        if not submission.policy_picker:
            raise ApplicationError(
                "Policy selection is required",
                non_retryable=True
            )

        if not submission.incident_description or len(submission.incident_description.strip()) < 10:
            raise ApplicationError(
                "Incident description must be at least 10 characters",
                non_retryable=True
            )

        # Store the submission
        self._claim_submission = submission

        workflow.logger.info(
            f"Claim submission accepted for policy: {submission.policy_picker}"
        )

        return ClaimSubmissionResult(
            status="accepted",
            message=f"Claim submitted for policy {submission.policy_picker}"
        )

    @workflow.update
    async def submit_assessor_findings(self, findings: AssessorFindings) -> AssessorFindingsResult:
        """Handle assessor evaluation findings from on-site inspection.

        Implements Conductor HUMAN_TASK: assesor_findings_ref
        Form: assesor_report

        Receives assessor's damage evaluation, coverage determination, and location details.
        This drives downstream coverage decisions and cost calculations.

        Args:
            findings: AssessorFindings with assessment array, coverage, location, etc.

        Returns:
            AssessorFindingsResult confirming acceptance

        Raises:
            ApplicationError: If findings already submitted or invalid input
        """
        # Validation: Ensure findings not already submitted
        if self._assessor_findings is not None:
            raise ApplicationError(
                "Assessor findings already submitted",
                non_retryable=True
            )

        # Validation: Check required fields
        if not findings.visible_assesments:
            raise ApplicationError(
                "At least one damage assessment is required",
                non_retryable=True
            )

        if not findings.overall_coverage:
            raise ApplicationError(
                "Overall coverage determination is required",
                non_retryable=True
            )

        # Store the findings
        self._assessor_findings = findings

        workflow.logger.info(
            f"Assessor findings accepted: {len(findings.visible_assesments)} assessments, overall_coverage={findings.overall_coverage}"
        )

        return AssessorFindingsResult(
            status="accepted",
            message=f"Assessor findings recorded with {len(findings.visible_assesments)} damage assessments"
        )

    @workflow.update
    async def submit_investigation_findings(self, findings: InvestigationFindings) -> InvestigationFindingsResult:
        """Handle investigation findings for high-cost claims.

        Implements Conductor HUMAN_TASK: investigation_human_ref
        Form: on_site_investigation

        Triggered only when claim cost exceeds threshold (>$100).
        Receives detailed investigation results that may influence final coverage decision.

        Args:
            findings: InvestigationFindings with investigation results and witness statements

        Returns:
            InvestigationFindingsResult confirming acceptance

        Raises:
            ApplicationError: If findings already submitted or invalid input
        """
        # Validation: Ensure findings not already submitted
        if self._investigation_findings is not None:
            raise ApplicationError(
                "Investigation findings already submitted",
                non_retryable=True
            )

        # Validation: Check required fields
        if not findings.investigation_findings:
            raise ApplicationError(
                "Investigation findings cannot be empty",
                non_retryable=True
            )

        # Store the findings
        self._investigation_findings = findings

        workflow.logger.info(
            f"Investigation findings accepted: {len(findings.investigation_findings)} characters"
        )

        return InvestigationFindingsResult(
            status="accepted",
            message="Investigation findings recorded"
        )

    # ========================================================================
    # QUERY HANDLERS (Status checking without modifying workflow)
    # ========================================================================

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Query current workflow status and progress.

        Allows external systems to check status without affecting workflow execution.

        Returns:
            Dict containing current status, stage, and completion state
        """
        return {
            "status": self._status,
            "current_stage": self._current_stage,
            "has_claim_submission": self._claim_submission is not None,
            "has_assessor_findings": self._assessor_findings is not None,
            "has_investigation_findings": self._investigation_findings is not None,
            "policy_selected": self._claim_submission.policy_picker if self._claim_submission else None,
            "overall_coverage": self._assessor_findings.overall_coverage if self._assessor_findings else None
        }

    @workflow.query
    def get_claim_details(self) -> Optional[Dict[str, Any]]:
        """Query submitted claim details.

        Returns:
            Dict with claim submission details or None if not yet submitted
        """
        if self._claim_submission is None:
            return None

        return {
            "policy_picker": self._claim_submission.policy_picker,
            "incident_description": self._claim_submission.incident_description
        }

    @workflow.query
    def get_damage_summary(self) -> Optional[Dict[str, Any]]:
        """Query damage assessment summary.

        Returns:
            Dict with assessor findings summary or None if not yet available
        """
        if self._assessor_findings is None:
            return None

        return {
            "overall_coverage": self._assessor_findings.overall_coverage,
            "number_of_assessments": len(self._assessor_findings.visible_assesments),
            "location": {
                "city": self._assessor_findings.incident_city,
                "street": self._assessor_findings.incident_street,
                "state": self._assessor_findings.incident_state
            },
            "rationale": self._assessor_findings.rationale
        }

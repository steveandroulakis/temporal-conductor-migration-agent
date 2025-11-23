"""Workflow definition for schema approval workflow.

Temporal workflow migrated from Conductor workflow: schema_approval

This workflow implements a multi-stage schema review and approval process with:
- DO_WHILE loop that repeats until final approval is received
- FORK_JOIN parallel execution of two initial reviews (Review1.a, Review1.b)
- Three cascading approval checkpoints (Review1Check, Review2Check, Review3Check)
- Human interaction via Updates for approval decisions at each stage
- Complex nested control flow with maximum depth of 5 levels

Control Flow Overview:
1. DO_WHILE loop (continues until approved):
   a. Upload schema
   b. FORK_JOIN: Parallel execution of Review1.a and Review1.b
   c. Review1Check (SWITCH): Check if both reviews passed
      - YES: Continue to Review2
      - NO: Restart loop
   d. Review2 (conditional on Review1Check = YES)
   e. Review2Check (SWITCH): Decide if Review3 is needed
      - YES: Skip Review3, go to CompleteReview_1
      - NO: Continue to Review3
   f. Review3 (conditional on Review2Check = NO)
   g. Review3Check (SWITCH): Final approval check
      - YES: Go to CompleteReview_2
   h. CompleteReview (sets approval flag to exit loop)

Human Interaction:
- submit_review1_approval: Update handler for Review1Check approval decision
- submit_review2_approval: Update handler for Review2Check approval decision
- submit_review3_approval: Update handler for Review3Check approval decision

Original Conductor workflow: EXAMPLE_review_approval.json
Complexity: HIGH
Max nesting depth: 5
"""

import asyncio
from datetime import timedelta, datetime
from typing import Optional, Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

# Import workflow-safe: Import only dataclasses from shared module
with workflow.unsafe.imports_passed_through():
    from .shared import (
        WorkflowInput,
        WorkflowOutput,
        UploadSchemaInput,
        ReviewInput,
        ReviewOutput,
        CompleteReviewInput,
        CompleteReviewOutput,
        ApprovalDecision,
        ApprovalResult,
    )
    # Import specific activity functions by name (NOT entire module)
    # This ensures workflow sandbox compliance
    from .activities import (
        upload_schema,
        review_1a,
        review_1b,
        review_2,
        review_3,
        complete_review,
    )


# Default retry policy for activities
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=100),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)


@workflow.defn
class SchemaApprovalWorkflow:
    """
    Multi-stage schema approval workflow with human review checkpoints.

    This workflow implements a DO_WHILE loop containing a complex approval process
    with parallel reviews, nested conditional checks, and multiple human interaction
    points. The workflow repeats until final approval is achieved.

    The approval process has three stages:
    1. Review1: Two parallel reviews (Review1.a and Review1.b)
    2. Review2: Second-stage review (conditional on Review1 approval)
    3. Review3: Final-stage review (conditional on Review2 decision)

    Each stage has an associated approval checkpoint where human reviewers make
    decisions via workflow Updates.

    Workflow Queries:
    - get_status: Returns current workflow status and review stage
    """

    def __init__(self) -> None:
        """Initialize workflow state variables."""
        # Approval tracking
        self._approved = False
        self._current_stage = "initializing"
        self._iteration = 0

        # Review result storage
        self._review1a_result: Optional[ReviewOutput] = None
        self._review1b_result: Optional[ReviewOutput] = None
        self._review2_result: Optional[ReviewOutput] = None
        self._review3_result: Optional[ReviewOutput] = None

        # Human interaction state - approval decisions at each checkpoint
        self._review1_approval: Optional[ApprovalDecision] = None
        self._review2_approval: Optional[ApprovalDecision] = None
        self._review3_approval: Optional[ApprovalDecision] = None

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        """
        Execute the schema approval workflow.

        Args:
            input: WorkflowInput containing submission details

        Returns:
            WorkflowOutput with final approval status and metadata

        Raises:
            ApplicationError: On validation failures or unrecoverable errors
        """
        workflow.logger.info(
            f"Starting schema approval workflow for submission {input.submission_id}"
        )

        # DO_WHILE loop: Repeat until approval is received
        # Original Conductor task: repeat_until_approved (DO_WHILE)
        # Loop condition: while not self._approved
        # Maximum iterations to prevent infinite loops
        max_iterations = 10
        self._iteration = 0

        while self._iteration < max_iterations and not self._approved:
            self._iteration += 1
            workflow.logger.info(
                f"Starting approval loop iteration {self._iteration}"
            )
            self._current_stage = f"iteration_{self._iteration}"

            # Reset approval decisions for this iteration
            self._review1_approval = None
            self._review2_approval = None
            self._review3_approval = None

            # Execute the approval process for this iteration
            await self._execute_approval_iteration(input)

            # Check if continue-as-new is needed for long-running workflows
            if workflow.info().is_continue_as_new_suggested():
                workflow.logger.info(
                    "Continue-as-new suggested - continuing workflow in new run"
                )
                # Note: In production, pass remaining state to new workflow run
                # workflow.continue_as_new(input)

        # Workflow completion
        if self._approved:
            workflow.logger.info(
                f"Schema approval completed after {self._iteration} iterations"
            )
            return WorkflowOutput(
                status="approved",
                approval_stage=self._current_stage,
                total_iterations=self._iteration,
                completed_at=workflow.now(),  # Use workflow.now() for deterministic time
                final_decision={
                    "approved": True,
                    "iterations": self._iteration,
                },
            )
        else:
            workflow.logger.warning(
                f"Schema approval failed: Maximum iterations ({max_iterations}) reached"
            )
            return WorkflowOutput(
                status="rejected",
                approval_stage="max_iterations_exceeded",
                total_iterations=self._iteration,
                completed_at=workflow.now(),  # Use workflow.now() for deterministic time
                final_decision={
                    "approved": False,
                    "reason": "Maximum iterations exceeded",
                },
            )

    async def _execute_approval_iteration(self, input: WorkflowInput) -> None:
        """
        Execute one iteration of the approval process.

        This method contains all tasks within the DO_WHILE loop body:
        - upload_schema
        - FORK_JOIN (Review1.a, Review1.b)
        - Review1Check (SWITCH)
        - Review2 (conditional)
        - Review2Check (SWITCH)
        - Review3 (conditional)
        - Review3Check (SWITCH)
        - CompleteReview (conditional, sets approval flag)

        Args:
            input: WorkflowInput with submission details
        """
        # Step 1: Upload schema
        # Original Conductor task: upload_schema (SIMPLE)
        workflow.logger.info(f"Step 1: Uploading schema (iteration {self._iteration})")
        self._current_stage = "upload"

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
        workflow.logger.info(f"Schema uploaded: {upload_message}")

        # Step 2: FORK_JOIN - Parallel execution of Review1.a and Review1.b
        # Original Conductor task: fork_join (FORK_JOIN) with JOIN (notification_join)
        workflow.logger.info("Step 2: Executing parallel reviews (Review1.a, Review1.b)")
        self._current_stage = "review1_parallel"

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
            f"Parallel reviews completed: Review1.a={self._review1a_result.status if self._review1a_result else 'unknown'}, "
            f"Review1.b={self._review1b_result.status if self._review1b_result else 'unknown'}"
        )

        # Step 3: Review1Check (SWITCH)
        # Original Conductor task: Review1Check (SWITCH)
        # Evaluates ${user_action.output.approved} via Update
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

    async def _execute_review2_branch(self, input: WorkflowInput) -> None:
        """
        Execute Review2 branch (conditional on Review1Check = YES).

        This helper method handles the nested control flow after Review1 approval:
        - Review2 activity
        - Review2Check SWITCH
        - Conditional execution of Review3 or CompleteReview_1

        Args:
            input: WorkflowInput with submission details
        """
        # Step 4: Review2 (SIMPLE)
        # Original Conductor task: Review2 (SIMPLE)
        # Nesting level: 3
        workflow.logger.info("Step 4: Executing Review2")
        self._current_stage = "review2"

        review2_input = ReviewInput(
            submission_id=input.submission_id,
            schema_data=input.schema_data,
            review_stage="Review2",
            previous_reviews={
                "Review1.a": {
                    "status": self._review1a_result.status if self._review1a_result else None,
                },
                "Review1.b": {
                    "status": self._review1b_result.status if self._review1b_result else None,
                },
            },
        )

        self._review2_result = await workflow.execute_activity(
            review_2,
            review2_input,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        workflow.logger.info(f"Review2 completed with status: {self._review2_result.status}")

        # Step 5: Review2Check (SWITCH)
        # Original Conductor task: Review2Check (SWITCH)
        # Evaluates ${user_action.output.approved} and skip_review3 flag
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

    async def _execute_review3_branch(self, input: WorkflowInput) -> None:
        """
        Execute Review3 branch (conditional on Review2Check = NO).

        This helper method handles the most deeply nested control flow:
        - Review3 activity (nesting level 4)
        - Review3Check SWITCH (nesting level 4)
        - CompleteReview_2 (nesting level 5)

        Args:
            input: WorkflowInput with submission details
        """
        # Step 6: Review3 (SIMPLE)
        # Original Conductor task: Review3 (SIMPLE)
        # Nesting level: 4
        workflow.logger.info("Step 6: Executing Review3")
        self._current_stage = "review3"

        review3_input = ReviewInput(
            submission_id=input.submission_id,
            schema_data=input.schema_data,
            review_stage="Review3",
            previous_reviews={
                "Review1.a": {
                    "status": self._review1a_result.status if self._review1a_result else None,
                },
                "Review1.b": {
                    "status": self._review1b_result.status if self._review1b_result else None,
                },
                "Review2": {
                    "status": self._review2_result.status if self._review2_result else None,
                },
            },
        )

        self._review3_result = await workflow.execute_activity(
            review_3,
            review3_input,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        workflow.logger.info(f"Review3 completed with status: {self._review3_result.status}")

        # Step 7: Review3Check (SWITCH)
        # Original Conductor task: Review3Check (SWITCH)
        # Evaluates ${user_action.output.approved}
        # Nesting level: 4
        workflow.logger.info("Step 7: Waiting for Review3 approval decision")
        self._current_stage = "review3_check"

        # Wait for human approval decision with timeout
        try:
            await workflow.wait_condition(
                lambda: self._review3_approval is not None,
                timeout=timedelta(hours=24),
            )
        except asyncio.TimeoutError:
            workflow.logger.warning("Review3 approval timeout - restarting loop")
            return

        # Process Review3 approval decision (SWITCH logic)
        if self._review3_approval and self._review3_approval.approved:
            # YES case: Final approval, go to CompleteReview_2
            workflow.logger.info("Review3Check: YES - Completing review with final approval")
            await self._execute_complete_review(
                input,
                approval_decisions={
                    "Review1": self._review1_approval.approved if self._review1_approval else False,
                    "Review2": self._review2_approval.approved if self._review2_approval else False,
                    "Review3": self._review3_approval.approved if self._review3_approval else False,
                },
                final_approval=True,
            )
        else:
            # Default case: Approval not granted, restart loop
            workflow.logger.info("Review3Check: NO - Restarting approval loop")
            return

    async def _execute_complete_review(
        self,
        input: WorkflowInput,
        approval_decisions: Dict[str, Any],
        final_approval: bool,
    ) -> None:
        """
        Execute CompleteReview activity and set approval flag.

        This activity is executed at two possible exit points:
        - CompleteReview_1: After Review2Check = YES (skip Review3)
        - CompleteReview_2: After Review3Check = YES (final approval)

        Both paths execute the same activity which sets the approval flag
        to exit the DO_WHILE loop.

        Args:
            input: WorkflowInput with submission details
            approval_decisions: Dict of all approval decisions made
            final_approval: Boolean indicating if workflow should complete
        """
        workflow.logger.info("Executing CompleteReview to finalize approval process")
        self._current_stage = "completing"

        complete_input = CompleteReviewInput(
            submission_id=input.submission_id,
            approval_decisions=approval_decisions,
            final_approval=final_approval,
        )

        complete_result = await workflow.execute_activity(
            complete_review,
            complete_input,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=100),
                maximum_attempts=5,  # Higher retry for critical completion step
                backoff_coefficient=2.0,
            ),
        )

        workflow.logger.info(
            f"CompleteReview finished: {complete_result.status} - {complete_result.message}"
        )

        # Set approval flag to exit DO_WHILE loop
        # This corresponds to setting workflow.variables.approved = true in Conductor
        self._approved = final_approval
        self._current_stage = "completed"

    # Human Interaction Handlers - Update pattern for approval decisions

    @workflow.update
    async def submit_review1_approval(
        self, decision: ApprovalDecision
    ) -> ApprovalResult:
        """
        Handle Review1 approval decision from human reviewer.

        This Update corresponds to the Review1Check SWITCH task in Conductor,
        which evaluates ${user_action.output.approved}.

        Args:
            decision: ApprovalDecision with reviewer info and approval status

        Returns:
            ApprovalResult confirming acceptance and current stage

        Raises:
            ApplicationError: If approval already submitted or workflow not at correct stage
        """
        workflow.logger.info(
            f"Received Review1 approval from {decision.reviewer_id}: approved={decision.approved}"
        )

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

    @workflow.update
    async def submit_review2_approval(
        self, decision: ApprovalDecision
    ) -> ApprovalResult:
        """
        Handle Review2 approval decision from human reviewer.

        This Update corresponds to the Review2Check SWITCH task in Conductor,
        which evaluates ${user_action.output.approved} and skip_review3 flag.

        Args:
            decision: ApprovalDecision with reviewer info, approval status,
                     and skip_review3 flag

        Returns:
            ApprovalResult confirming acceptance and current stage

        Raises:
            ApplicationError: If approval already submitted or workflow not at correct stage
        """
        workflow.logger.info(
            f"Received Review2 approval from {decision.reviewer_id}: "
            f"approved={decision.approved}, skip_review3={decision.skip_review3}"
        )

        # Validation: Check if we're at the correct stage
        if self._current_stage != "review2_check":
            raise ApplicationError(
                f"Cannot submit Review2 approval at stage: {self._current_stage}"
            )

        # Validation: Check for duplicate submission
        if self._review2_approval is not None:
            raise ApplicationError("Review2 approval already submitted for this iteration")

        # Store the approval decision
        self._review2_approval = decision

        # Return result to caller
        next_stage = "complete" if decision.skip_review3 else "review3"
        return ApprovalResult(
            status="accepted",
            message=f"Review2 approval recorded: {'approved' if decision.approved else 'rejected'}. Next: {next_stage}",
            reviewer=decision.reviewer_id,
            current_stage="review2_check",
        )

    @workflow.update
    async def submit_review3_approval(
        self, decision: ApprovalDecision
    ) -> ApprovalResult:
        """
        Handle Review3 approval decision from human reviewer.

        This Update corresponds to the Review3Check SWITCH task in Conductor,
        which evaluates ${user_action.output.approved} for final approval.

        Args:
            decision: ApprovalDecision with reviewer info and approval status

        Returns:
            ApprovalResult confirming acceptance and current stage

        Raises:
            ApplicationError: If approval already submitted or workflow not at correct stage
        """
        workflow.logger.info(
            f"Received Review3 approval from {decision.reviewer_id}: approved={decision.approved}"
        )

        # Validation: Check if we're at the correct stage
        if self._current_stage != "review3_check":
            raise ApplicationError(
                f"Cannot submit Review3 approval at stage: {self._current_stage}"
            )

        # Validation: Check for duplicate submission
        if self._review3_approval is not None:
            raise ApplicationError("Review3 approval already submitted for this iteration")

        # Store the approval decision
        self._review3_approval = decision

        # Return result to caller
        return ApprovalResult(
            status="accepted",
            message=f"Review3 (final) approval recorded: {'approved' if decision.approved else 'rejected'}",
            reviewer=decision.reviewer_id,
            current_stage="review3_check",
        )

    # Query Handlers - Allow external systems to check workflow status

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """
        Query current workflow status and review stage.

        Returns:
            Dict containing:
                - current_stage: Current review stage
                - iteration: Current iteration number
                - approved: Whether final approval has been granted
                - review1_status: Status of Review1 approval
                - review2_status: Status of Review2 approval
                - review3_status: Status of Review3 approval
        """
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
            "review2_status": {
                "review2_completed": self._review2_result is not None,
                "approval_received": self._review2_approval is not None,
                "approved": self._review2_approval.approved if self._review2_approval else None,
                "skip_review3": self._review2_approval.skip_review3 if self._review2_approval else None,
            },
            "review3_status": {
                "review3_completed": self._review3_result is not None,
                "approval_received": self._review3_approval is not None,
                "approved": self._review3_approval.approved if self._review3_approval else None,
            },
        }

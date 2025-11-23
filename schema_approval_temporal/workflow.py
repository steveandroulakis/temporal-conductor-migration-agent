"""Workflow definition for schema approval process.

Temporal workflow migrated from Conductor workflow: schema_approval

This workflow implements a complex multi-stage approval process with:
- DO_WHILE loop: Retry until final approval
- FORK_JOIN: Parallel Review1.a and Review1.b execution
- 3 SWITCH conditionals: Review1Check, Review2Check, Review3Check
- 4 human interaction points via Updates
- Maximum nesting depth: 5 levels

Original Conductor workflow: conductor-definition/EXAMPLE_review_approval.json
Complexity: HIGH (5-level nesting with loops, parallel execution, and conditionals)
"""
import asyncio
from datetime import timedelta, datetime
from typing import Optional, Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

# Import shared types using workflow.unsafe for sandbox compliance
with workflow.unsafe.imports_passed_through():
    from .shared import (
        WorkflowInput,
        WorkflowOutput,
        UploadSchemaInput,
        ApprovalDecision,
        ApprovalResult,
    )
    # CRITICAL: Import specific activity functions by name only
    # DO NOT import entire activities module (causes sandbox violations)
    from .activities import (
        upload_schema,
        review_1a,
        review_1b,
        review_2,
        review_3,
        complete_review_skip_review3,
        complete_review_after_review3,
    )

# Default retry policy for all activities
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=100),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)


@workflow.defn
class SchemaApprovalWorkflow:
    """
    Schema approval workflow with multi-stage review process.

    This workflow implements the following complex control flow:
    1. DO_WHILE loop: Repeats entire review process until approved
    2. FORK_JOIN: Parallel execution of Review1.a and Review1.b
    3. SWITCH Review1Check: Conditional approval after Review1
    4. SWITCH Review2Check: Determines if Review3 is needed
    5. SWITCH Review3Check: Final approval gate

    Control Flow Structure (5-level nesting):
    Level 1: DO_WHILE (repeat_until_approved)
      Level 2: Sequential upload_schema
      Level 2: FORK_JOIN (my_fork_join_ref) → asyncio.gather()
        Level 3: Review1.a (parallel)
        Level 3: Review1.b (parallel)
      Level 2: SWITCH Review1Check (human approval gate #1)
        Level 3: YES branch → Review2 + Review2Check
          Level 4: Review2Check SWITCH (human approval gate #2)
            Level 4: YES branch → CompleteReview_1 (skip Review3 path)
            Level 4: NO branch → Review3 + Review3Check
              Level 5: Review3Check SWITCH (human approval gate #3)
                Level 5: YES branch → CompleteReview_2 (after Review3 path)
                Level 5: NO branch → Loop continues
        Level 3: NO branch → Loop continues

    Human Interaction Patterns:
    - Review1Check: Wait for approval after parallel Review1.a and Review1.b
    - Review2Check: Wait for decision on whether to skip Review3
    - Review3Check: Wait for final approval after Review3
    - All use Update pattern for validation and immediate feedback

    Original Conductor workflow: EXAMPLE_review_approval.json
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        # Instance variables for storing approval decisions at each stage
        self._review1_approval: Optional[ApprovalDecision] = None
        self._review2_approval: Optional[ApprovalDecision] = None
        self._review3_approval: Optional[ApprovalDecision] = None

        # Workflow state tracking
        self._status: str = "started"
        self._iteration: int = 0
        self._approved: bool = False
        self._current_stage: str = "initialization"
        self._authorized_reviewers = {
            "reviewer-1a",
            "reviewer-1b",
            "reviewer-2",
            "reviewer-3",
        }

    @workflow.update
    async def submit_review1_approval(
        self, decision: ApprovalDecision
    ) -> ApprovalResult:
        """
        Handle approval decision from Review1 checkpoint.

        This Update receives approval decisions after Review1.a and Review1.b
        complete in parallel. Corresponds to Conductor's Review1Check SWITCH
        task with decisionCases: YES/NO.

        Args:
            decision: Approval decision with reviewer info
                - decision: "YES" or "NO" matching Conductor SWITCH cases
                - stage: Must be "Review1Check"
                - reviewer_id: Authorized reviewer identifier
                - approved: Boolean approval flag
                - comments: Optional review comments

        Returns:
            ApprovalResult confirming acceptance

        Raises:
            ApplicationError: If approval already submitted or reviewer unauthorized
        """
        # Validate state
        if self._review1_approval is not None:
            raise ApplicationError("Review1 approval already submitted")

        # Validate stage
        if decision.stage != "Review1Check":
            raise ApplicationError(
                f"Invalid stage for Review1 approval: {decision.stage}"
            )

        # Validate reviewer authorization
        if decision.reviewer_id not in self._authorized_reviewers:
            raise ApplicationError(f"Unauthorized reviewer: {decision.reviewer_id}")

        # Store decision
        self._review1_approval = decision
        workflow.logger.info(
            f"Review1 approval received: {decision.decision} from {decision.reviewer_id}"
        )

        # Return result to caller
        return ApprovalResult(
            status="accepted",
            message=f"Review1 approval decision '{decision.decision}' recorded",
            reviewer=decision.reviewer_id,
            workflow_status=self._status,
        )

    @workflow.update
    async def submit_review2_approval(
        self, decision: ApprovalDecision
    ) -> ApprovalResult:
        """
        Handle approval decision from Review2 checkpoint.

        This Update receives decisions about whether to skip Review3. Corresponds
        to Conductor's Review2Check SWITCH task with decisionCases: YES (skip
        Review3) or NO (proceed to Review3).

        Args:
            decision: Approval decision with reviewer info
                - decision: "YES" or "NO" matching Conductor SWITCH cases
                - stage: Must be "Review2Check"
                - skip_review3: Boolean flag for expedited approval path
                - reviewer_id: Authorized reviewer identifier
                - approved: Boolean approval flag
                - comments: Optional review comments

        Returns:
            ApprovalResult confirming acceptance

        Raises:
            ApplicationError: If approval already submitted or reviewer unauthorized
        """
        # Validate state
        if self._review2_approval is not None:
            raise ApplicationError("Review2 approval already submitted")

        # Validate stage
        if decision.stage != "Review2Check":
            raise ApplicationError(
                f"Invalid stage for Review2 approval: {decision.stage}"
            )

        # Validate reviewer authorization
        if decision.reviewer_id not in self._authorized_reviewers:
            raise ApplicationError(f"Unauthorized reviewer: {decision.reviewer_id}")

        # Store decision
        self._review2_approval = decision
        workflow.logger.info(
            f"Review2 approval received: {decision.decision} from {decision.reviewer_id}"
        )

        # Return result to caller
        return ApprovalResult(
            status="accepted",
            message=f"Review2 approval decision '{decision.decision}' recorded",
            reviewer=decision.reviewer_id,
            workflow_status=self._status,
        )

    @workflow.update
    async def submit_review3_approval(
        self, decision: ApprovalDecision
    ) -> ApprovalResult:
        """
        Handle approval decision from Review3 checkpoint (final approval gate).

        This Update receives final approval decisions after Review3 completes.
        Corresponds to Conductor's Review3Check SWITCH task with decisionCases:
        YES (final approval) or NO (loop continues).

        Args:
            decision: Approval decision with reviewer info
                - decision: "YES" or "NO" matching Conductor SWITCH cases
                - stage: Must be "Review3Check"
                - reviewer_id: Authorized reviewer identifier
                - approved: Boolean approval flag
                - comments: Optional review comments

        Returns:
            ApprovalResult confirming acceptance

        Raises:
            ApplicationError: If approval already submitted or reviewer unauthorized
        """
        # Validate state
        if self._review3_approval is not None:
            raise ApplicationError("Review3 approval already submitted")

        # Validate stage
        if decision.stage != "Review3Check":
            raise ApplicationError(
                f"Invalid stage for Review3 approval: {decision.stage}"
            )

        # Validate reviewer authorization
        if decision.reviewer_id not in self._authorized_reviewers:
            raise ApplicationError(f"Unauthorized reviewer: {decision.reviewer_id}")

        # Store decision
        self._review3_approval = decision
        workflow.logger.info(
            f"Review3 approval received: {decision.decision} from {decision.reviewer_id}"
        )

        # Return result to caller
        return ApprovalResult(
            status="accepted",
            message=f"Review3 approval decision '{decision.decision}' recorded",
            reviewer=decision.reviewer_id,
            workflow_status=self._status,
        )

    @workflow.query
    def get_approval_status(self) -> Dict[str, Any]:
        """
        Query current workflow status without modifying state.

        Allows external systems to check approval progress.

        Returns:
            Dictionary containing:
                - status: Current workflow status
                - iteration: Current loop iteration
                - current_stage: Current review stage
                - approved: Final approval flag
                - review1_decision: Review1 approval decision if present
                - review2_decision: Review2 approval decision if present
                - review3_decision: Review3 approval decision if present
        """
        return {
            "status": self._status,
            "iteration": self._iteration,
            "current_stage": self._current_stage,
            "approved": self._approved,
            "review1_decision": (
                self._review1_approval.decision if self._review1_approval else None
            ),
            "review2_decision": (
                self._review2_approval.decision if self._review2_approval else None
            ),
            "review3_decision": (
                self._review3_approval.decision if self._review3_approval else None
            ),
        }

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        """
        Execute the schema approval workflow.

        This implements the complete Conductor DO_WHILE loop with nested
        FORK_JOIN and SWITCH tasks.

        Conductor Control Flow Translation:
        - DO_WHILE loop with loopCondition: if ($.approved) { false; } else { true; }
        - Loop contains: upload_schema, my_fork_join_ref, notification_join_ref, Review1Check
        - Review1Check branches to Review2 + Review2Check (YES) or loop restart (NO)
        - Review2Check branches to CompleteReview_1 (YES) or Review3 + Review3Check (NO)
        - Review3Check branches to CompleteReview_2 (YES) or loop restart (NO)

        Args:
            input: Workflow input parameters containing:
                - schema_id: Unique identifier for schema
                - schema_content: Schema data to review
                - submitter_id: ID of user submitting schema
                - priority: Priority level (default 1)
                - metadata: Optional additional metadata

        Returns:
            WorkflowOutput containing:
                - status: Final workflow status ("approved" or "rejected")
                - approved: Boolean approval flag
                - schema_id: Schema identifier
                - final_approval_stage: Stage where final approval occurred
                - iterations: Number of loop iterations
                - completed_at: Completion timestamp
                - approval_history: History of all approval decisions

        Raises:
            ApplicationError: On max iterations exceeded or unrecoverable errors
        """
        workflow.logger.info(
            f"Starting schema approval workflow for schema: {input.schema_id}"
        )

        # DO_WHILE loop: Conductor loopCondition: if ($.approved) { false; } else { true; }
        # Translation: while not self._approved
        max_iterations = 10  # Prevent infinite loops
        approval_history: list[Dict[str, Any]] = []

        # Conductor DO_WHILE loop begins here
        while self._iteration < max_iterations and not self._approved:
            self._iteration += 1
            workflow.logger.info(
                f"Starting approval iteration {self._iteration} for schema {input.schema_id}"
            )
            self._current_stage = f"iteration_{self._iteration}"

            # Reset approval decisions for this iteration
            self._review1_approval = None
            self._review2_approval = None
            self._review3_approval = None

            # Task 1: upload_schema (SIMPLE task, nesting level 2)
            # First task in DO_WHILE loop body
            self._current_stage = "uploading_schema"
            upload_result = await workflow.execute_activity(
                upload_schema,
                UploadSchemaInput(
                    schema_id=input.schema_id,
                    schema_content=input.schema_content,
                    submitter_id=input.submitter_id,
                    iteration=self._iteration,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY_POLICY,
            )
            workflow.logger.info(
                f"Schema uploaded: {upload_result.upload_id}, status: {upload_result.status}"
            )

            # Task 2: FORK_JOIN (my_fork_join_ref, nesting level 2)
            # Parallel execution of Review1.a and Review1.b
            # Conductor forkTasks: [["Review1.a"], ["Review1.b"]]
            # Translation: asyncio.gather() with two parallel activity executions
            self._current_stage = "parallel_review1"
            workflow.logger.info("Starting parallel Review1.a and Review1.b")

            review1a_result, review1b_result = await asyncio.gather(
                workflow.execute_activity(
                    review_1a,
                    args=[input.schema_id, upload_result.upload_id],
                    start_to_close_timeout=timedelta(seconds=20),
                    retry_policy=DEFAULT_RETRY_POLICY,
                ),
                workflow.execute_activity(
                    review_1b,
                    args=[input.schema_id, upload_result.upload_id],
                    start_to_close_timeout=timedelta(seconds=20),
                    retry_policy=DEFAULT_RETRY_POLICY,
                ),
                return_exceptions=False,  # Both must succeed
            )

            # Task 3: JOIN (notification_join_ref, nesting level 2)
            # No explicit translation needed - asyncio.gather() already waits for both
            workflow.logger.info(
                f"Review1 parallel tasks completed: {review1a_result.reviewer_id}, {review1b_result.reviewer_id}"
            )

            # Task 4: SWITCH Review1Check (nesting level 2)
            # Conductor: evaluatorType: value-param, expression: switchCaseValue
            # inputParameters: switchCaseValue: ${user_action.output.approved}
            # decisionCases: YES: [Review2, Review2Check], NO: []
            # Translation: Wait for human approval Update, then if/else
            self._current_stage = "awaiting_review1_approval"
            workflow.logger.info("Waiting for Review1 approval decision")

            try:
                # Wait for Review1 approval with timeout
                await workflow.wait_condition(
                    lambda: self._review1_approval is not None,
                    timeout=timedelta(hours=24),
                )
            except asyncio.TimeoutError:
                workflow.logger.warning(
                    f"Review1 approval timeout on iteration {self._iteration}"
                )
                approval_history.append(
                    {
                        "iteration": self._iteration,
                        "stage": "Review1Check",
                        "result": "timeout",
                        "timestamp": workflow.now().isoformat(),
                    }
                )
                # NO case: Continue loop (next iteration)
                continue

            # Process Review1 approval decision
            # Conductor SWITCH decisionCases: "YES" or "NO"
            assert self._review1_approval is not None  # Type narrowing for mypy
            approval_history.append(
                {
                    "iteration": self._iteration,
                    "stage": "Review1Check",
                    "decision": self._review1_approval.decision,
                    "reviewer": self._review1_approval.reviewer_id,
                    "approved": self._review1_approval.approved,
                    "timestamp": workflow.now().isoformat(),
                }
            )

            if self._review1_approval.decision == "YES" and self._review1_approval.approved:
                # YES branch: Proceed to Review2 (nesting level 3)
                workflow.logger.info("Review1 approved - proceeding to Review2")
                self._current_stage = "review2"

                # Task 5: Review2 (SIMPLE task, nesting level 3)
                review2_result = await workflow.execute_activity(
                    review_2,
                    args=[
                        input.schema_id,
                        {
                            "review1a": review1a_result.__dict__,
                            "review1b": review1b_result.__dict__,
                        },
                    ],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                workflow.logger.info(
                    f"Review2 completed by {review2_result.reviewer_id}"
                )

                # Task 6: SWITCH Review2Check (nesting level 3)
                # Conductor: evaluatorType: value-param
                # expression: if (skippReview3) return YES; else return NO;
                # decisionCases: YES: [CompleteReview_1], NO: [Review3, Review3Check]
                # Translation: Wait for human approval Update (skip_review3 decision), then if/else
                self._current_stage = "awaiting_review2_approval"
                workflow.logger.info("Waiting for Review2 approval decision")

                try:
                    # Wait for Review2 approval with timeout
                    await workflow.wait_condition(
                        lambda: self._review2_approval is not None,
                        timeout=timedelta(hours=24),
                    )
                except asyncio.TimeoutError:
                    workflow.logger.warning(
                        f"Review2 approval timeout on iteration {self._iteration}"
                    )
                    approval_history.append(
                        {
                            "iteration": self._iteration,
                            "stage": "Review2Check",
                            "result": "timeout",
                            "timestamp": workflow.now().isoformat(),
                        }
                    )
                    # NO case: Continue loop (next iteration)
                    continue

                # Process Review2 approval decision
                assert self._review2_approval is not None  # Type narrowing for mypy
                approval_history.append(
                    {
                        "iteration": self._iteration,
                        "stage": "Review2Check",
                        "decision": self._review2_approval.decision,
                        "reviewer": self._review2_approval.reviewer_id,
                        "approved": self._review2_approval.approved,
                        "skip_review3": self._review2_approval.skip_review3,
                        "timestamp": workflow.now().isoformat(),
                    }
                )

                if (
                    self._review2_approval.decision == "YES"
                    and self._review2_approval.skip_review3
                ):
                    # YES branch: Skip Review3 and complete (nesting level 4)
                    # Expedited approval path
                    workflow.logger.info(
                        "Review2 approved with skip_review3 - completing review"
                    )
                    self._current_stage = "completing_skip_review3"

                    # Task 7: CompleteReview_1 (SIMPLE task, nesting level 4)
                    completion_result = await workflow.execute_activity(
                        complete_review_skip_review3,
                        args=[
                            input.schema_id,
                            {
                                "review1a": review1a_result.__dict__,
                                "review1b": review1b_result.__dict__,
                                "review2": review2_result.__dict__,
                            },
                            True,  # approved
                        ],
                        start_to_close_timeout=timedelta(seconds=20),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    workflow.logger.info(
                        f"Review completed (skip Review3): {completion_result.completion_id}"
                    )

                    # Set approved flag to exit DO_WHILE loop
                    self._approved = True
                    self._status = "approved"
                    self._current_stage = "completed"

                    return WorkflowOutput(
                        status="approved",
                        approved=True,
                        schema_id=input.schema_id,
                        final_approval_stage="Review2Check (skip Review3)",
                        iterations=self._iteration,
                        completed_at=workflow.now(),
                        approval_history=approval_history,
                    )

                else:
                    # NO branch: Proceed to Review3 (nesting level 4)
                    workflow.logger.info(
                        "Review2 requires Review3 - proceeding to Review3"
                    )
                    self._current_stage = "review3"

                    # Task 8: Review3 (SIMPLE task, nesting level 4)
                    review3_result = await workflow.execute_activity(
                        review_3,
                        args=[
                            input.schema_id,
                            {
                                "review1a": review1a_result.__dict__,
                                "review1b": review1b_result.__dict__,
                                "review2": review2_result.__dict__,
                            },
                        ],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=DEFAULT_RETRY_POLICY,
                    )
                    workflow.logger.info(
                        f"Review3 completed by {review3_result.reviewer_id}"
                    )

                    # Task 9: SWITCH Review3Check (nesting level 4)
                    # Conductor: evaluatorType: value-param
                    # expression: if (approved) return YES; else return NO;
                    # decisionCases: YES: [CompleteReview_2], NO: []
                    # Translation: Wait for human approval Update, then if/else
                    self._current_stage = "awaiting_review3_approval"
                    workflow.logger.info("Waiting for Review3 approval decision")

                    try:
                        # Wait for Review3 approval with timeout
                        await workflow.wait_condition(
                            lambda: self._review3_approval is not None,
                            timeout=timedelta(hours=24),
                        )
                    except asyncio.TimeoutError:
                        workflow.logger.warning(
                            f"Review3 approval timeout on iteration {self._iteration}"
                        )
                        approval_history.append(
                            {
                                "iteration": self._iteration,
                                "stage": "Review3Check",
                                "result": "timeout",
                                "timestamp": workflow.now().isoformat(),
                            }
                        )
                        # NO case: Continue loop (next iteration)
                        continue

                    # Process Review3 approval decision
                    assert self._review3_approval is not None  # Type narrowing for mypy
                    approval_history.append(
                        {
                            "iteration": self._iteration,
                            "stage": "Review3Check",
                            "decision": self._review3_approval.decision,
                            "reviewer": self._review3_approval.reviewer_id,
                            "approved": self._review3_approval.approved,
                            "timestamp": workflow.now().isoformat(),
                        }
                    )

                    if (
                        self._review3_approval.decision == "YES"
                        and self._review3_approval.approved
                    ):
                        # YES branch: Complete after Review3 (nesting level 5)
                        # Full review path - maximum nesting depth
                        workflow.logger.info(
                            "Review3 approved - completing review (full path)"
                        )
                        self._current_stage = "completing_after_review3"

                        # Task 10: CompleteReview_2 (SIMPLE task, nesting level 5)
                        completion_result = await workflow.execute_activity(
                            complete_review_after_review3,
                            args=[
                                input.schema_id,
                                {
                                    "review1a": review1a_result.__dict__,
                                    "review1b": review1b_result.__dict__,
                                    "review2": review2_result.__dict__,
                                    "review3": review3_result.__dict__,
                                },
                                True,  # approved
                            ],
                            start_to_close_timeout=timedelta(seconds=20),
                            retry_policy=DEFAULT_RETRY_POLICY,
                        )
                        workflow.logger.info(
                            f"Review completed (after Review3): {completion_result.completion_id}"
                        )

                        # Set approved flag to exit DO_WHILE loop
                        self._approved = True
                        self._status = "approved"
                        self._current_stage = "completed"

                        return WorkflowOutput(
                            status="approved",
                            approved=True,
                            schema_id=input.schema_id,
                            final_approval_stage="Review3Check (full review)",
                            iterations=self._iteration,
                            completed_at=workflow.now(),
                            approval_history=approval_history,
                        )

                    else:
                        # NO branch: Loop continues (rejection at Review3)
                        workflow.logger.info(
                            f"Review3 rejected - restarting approval process (iteration {self._iteration})"
                        )
                        # Continue to next iteration of DO_WHILE loop
                        continue

            else:
                # NO branch: Loop continues (rejection at Review1)
                workflow.logger.info(
                    f"Review1 rejected - restarting approval process (iteration {self._iteration})"
                )
                # Continue to next iteration of DO_WHILE loop
                continue

            # Check if continue-as-new is needed for long-running loops
            # Conductor note: DO_WHILE loop can run indefinitely
            # Temporal best practice: Use continue-as-new to prevent history bloat
            if workflow.info().is_continue_as_new_suggested():
                workflow.logger.info(
                    "Workflow history size threshold reached - using continue-as-new"
                )
                # Continue execution in new workflow run with updated state
                workflow.continue_as_new(input)

        # If we exit the loop without approval, we've hit max iterations
        if not self._approved:
            workflow.logger.error(
                f"Schema approval failed after {max_iterations} iterations"
            )
            raise ApplicationError(
                f"Schema approval process exceeded maximum iterations ({max_iterations}) without approval",
                non_retryable=True,
            )

        # This should not be reached if loop exits with approval
        # (approval paths return directly from within the loop)
        return WorkflowOutput(
            status="error",
            approved=False,
            schema_id=input.schema_id,
            final_approval_stage="unknown",
            iterations=self._iteration,
            completed_at=workflow.now(),
            approval_history=approval_history,
        )

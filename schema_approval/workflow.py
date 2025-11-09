"""Workflow implementation translated from the Conductor schema approval example."""

from __future__ import annotations

from datetime import timedelta
from typing import List

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .activities import (
        complete_review,
        review_primary_a,
        review_primary_b,
        review_secondary,
        review_tertiary,
        upload_schema,
    )
    from .shared import (
        AttemptDetails,
        ReviewDecision,
        ReviewRequest,
        SchemaSubmission,
        SchemaUploadRequest,
        WorkflowInput,
        WorkflowOutput,
    )

PRIMARY_ACTIVITY_TIMEOUT = timedelta(seconds=10)
SECONDARY_ACTIVITY_TIMEOUT = timedelta(seconds=10)
UPLOAD_ACTIVITY_TIMEOUT = timedelta(seconds=15)
COMPLETE_ACTIVITY_TIMEOUT = timedelta(seconds=10)
DEFAULT_RETRY_POLICY = RetryPolicy(maximum_attempts=3)
TASK_QUEUE = "schema-approval-task-queue"


def _review_request(
    submission: SchemaSubmission,
    reviewer: str,
    required_attempts: int,
    attempt: int,
    force_additional_review: bool = False,
) -> ReviewRequest:
    """Helper to instantiate :class:`ReviewRequest`."""

    return ReviewRequest(
        submission=submission,
        reviewer=reviewer,
        required_attempts_for_approval=required_attempts,
        attempt=attempt,
        force_additional_review=force_additional_review,
    )


def _all_approved(decisions: List[ReviewDecision]) -> bool:
    """Return ``True`` when every decision indicates approval."""

    return all(decision.approved for decision in decisions)


@workflow.defn
class SchemaApprovalWorkflow:
    """Temporal workflow migrated from the Conductor ``schema_approval`` definition."""

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        """Execute the schema approval workflow."""

        attempts: List[AttemptDetails] = []
        attempt_counter = 0
        approved = False
        version = input.initial_version
        final_record = None

        while not approved:
            attempt_counter += 1

            submission_request = SchemaUploadRequest(
                schema_name=input.schema_name,
                schema_payload=input.schema_payload,
                target_version=version,
                attempt=attempt_counter,
            )
            submission = await workflow.execute_activity(
                upload_schema,
                submission_request,
                schedule_to_close_timeout=UPLOAD_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_RETRY_POLICY,
            )
            attempt_details = AttemptDetails(attempt=attempt_counter, submission=submission)

            primary_requests = [
                _review_request(
                    submission,
                    "Review1.a",
                    input.required_attempts_for_approval,
                    attempt_counter,
                ),
                _review_request(
                    submission,
                    "Review1.b",
                    input.required_attempts_for_approval,
                    attempt_counter,
                ),
            ]
            primary_futures = [
                workflow.start_activity(
                    review_primary_a,
                    primary_requests[0],
                    schedule_to_close_timeout=PRIMARY_ACTIVITY_TIMEOUT,
                    retry_policy=DEFAULT_RETRY_POLICY,
                ),
                workflow.start_activity(
                    review_primary_b,
                    primary_requests[1],
                    schedule_to_close_timeout=PRIMARY_ACTIVITY_TIMEOUT,
                    retry_policy=DEFAULT_RETRY_POLICY,
                ),
            ]
            primary_decisions = [
                await primary_futures[0],
                await primary_futures[1],
            ]
            attempt_details.decisions.extend(primary_decisions)

            if not _all_approved(primary_decisions):
                attempts.append(attempt_details)
                version += 1
                continue

            secondary_request = _review_request(
                submission,
                "Review2",
                input.required_attempts_for_approval,
                attempt_counter,
                force_additional_review=input.always_require_tertiary_review,
            )
            secondary_decision = await workflow.execute_activity(
                review_secondary,
                secondary_request,
                schedule_to_close_timeout=SECONDARY_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_RETRY_POLICY,
            )
            attempt_details.decisions.append(secondary_decision)

            if not secondary_decision.approved:
                attempts.append(attempt_details)
                version += 1
                continue

            if secondary_decision.skip_additional_review:
                final_record = await workflow.execute_activity(
                    complete_review,
                    submission,
                    attempt_details.decisions,
                    True,
                    schedule_to_close_timeout=COMPLETE_ACTIVITY_TIMEOUT,
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
                attempt_details.finalized = final_record
                attempts.append(attempt_details)
                approved = final_record.approved
                break

            tertiary_request = _review_request(
                submission,
                "Review3",
                input.required_attempts_for_approval,
                attempt_counter,
            )
            tertiary_decision = await workflow.execute_activity(
                review_tertiary,
                tertiary_request,
                schedule_to_close_timeout=SECONDARY_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_RETRY_POLICY,
            )
            attempt_details.decisions.append(tertiary_decision)

            if not tertiary_decision.approved:
                attempts.append(attempt_details)
                version += 1
                continue

            final_record = await workflow.execute_activity(
                complete_review,
                submission,
                attempt_details.decisions,
                True,
                schedule_to_close_timeout=COMPLETE_ACTIVITY_TIMEOUT,
                retry_policy=DEFAULT_RETRY_POLICY,
            )
            attempt_details.finalized = final_record
            attempts.append(attempt_details)
            approved = final_record.approved
            version += 1

        return WorkflowOutput(approved=approved, attempts=attempts, final_record=final_record)

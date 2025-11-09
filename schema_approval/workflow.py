"""Temporal workflow that mirrors the original Conductor definition."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Dict, List

from temporalio import workflow
from temporalio.common import RetryPolicy

from .activities import complete_review, notify_reviewer, record_decision, upload_schema
from .shared import (
    IterationSummary,
    ReviewDecision,
    ReviewRequest,
    SchemaApprovalResult,
    SchemaSubmission,
)

TASK_QUEUE = "schema-approval-task-queue"
DEFAULT_RETRY_POLICY = RetryPolicy(maximum_attempts=3)


@workflow.defn
class SchemaApprovalWorkflow:
    """Implements the approval loop defined in the Conductor workflow."""

    def __init__(self) -> None:
        self._pending_events: Dict[str, workflow.Event] = {}
        self._decisions: Dict[str, ReviewDecision] = {}
        self._summaries: List[IterationSummary] = []
        self._iteration: int = 0
        self._submission: SchemaSubmission | None = None

    @workflow.run
    async def run(self, submission: SchemaSubmission) -> SchemaApprovalResult:
        self._submission = submission
        approved = False

        while not approved:
            self._iteration += 1
            upload_message = await workflow.execute_activity(
                upload_schema,
                args=[submission, self._iteration],
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY_POLICY,
            )
            summary = IterationSummary(
                iteration=self._iteration,
                schema_name=submission.schema_name,
                upload_message=upload_message,
            )

            review1_requests = [
                self._build_request("review1.a", "Peer Review A", "Data Steward"),
                self._build_request("review1.b", "Peer Review B", "Security Analyst"),
            ]
            review1_decisions = await asyncio.gather(
                *(self._await_decision(request) for request in review1_requests)
            )
            summary.decisions.extend(review1_decisions)

            if not all(decision.approved for decision in review1_decisions):
                summary.approved = False
                self._summaries.append(summary)
                continue

            review2_request = self._build_request("Review2", "Lead Architecture Review", "Lead Architect")
            review2_decision = await self._await_decision(review2_request)
            summary.decisions.append(review2_decision)

            if review2_decision.requires_additional_review:
                review3_request = self._build_request(
                    "Review3", "Executive Oversight", "CTO Delegate"
                )
                review3_decision = await self._await_decision(review3_request)
                summary.decisions.append(review3_decision)
                final_decision = review3_decision
            else:
                final_decision = review2_decision

            summary.approved = final_decision.approved

            await workflow.execute_activity(
                complete_review,
                args=[summary],
                schedule_to_close_timeout=timedelta(seconds=10),
                retry_policy=DEFAULT_RETRY_POLICY,
            )

            approved = summary.approved
            self._summaries.append(summary)

        return SchemaApprovalResult(
            schema_name=submission.schema_name,
            iterations=self._iteration,
            approved=approved,
            summaries=self._summaries,
        )

    @workflow.update(name="submit_review_decision")
    def submit_review_decision(self, decision: ReviewDecision) -> None:
        event = self._pending_events.get(decision.review_id)
        if event is None:
            raise workflow.ApplicationError(
                f"No pending review with id {decision.review_id}",
                non_retryable=True,
            )
        if decision.review_id in self._decisions:
            raise workflow.ApplicationError(
                f"Decision for {decision.review_id} already recorded", non_retryable=True
            )
        self._decisions[decision.review_id] = decision
        event.set()

    @workflow.query
    def pending_reviews(self) -> List[str]:
        return list(self._pending_events.keys())

    @workflow.query
    def iteration(self) -> int:
        return self._iteration

    async def _await_decision(self, request: ReviewRequest) -> ReviewDecision:
        event = workflow.Event()
        self._pending_events[request.review_id] = event

        await workflow.execute_activity(
            notify_reviewer,
            args=[request],
            schedule_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        await event.wait()
        decision = self._decisions.pop(request.review_id)
        self._pending_events.pop(request.review_id, None)

        await workflow.execute_activity(
            record_decision,
            args=[decision],
            schedule_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        return decision

    def _build_request(self, ref: str, stage: str, reviewer: str) -> ReviewRequest:
        if self._submission is None:
            raise workflow.ApplicationError("Workflow not initialised", non_retryable=True)
        review_id = f"{ref}:iter-{self._iteration}"
        return ReviewRequest(
            review_id=review_id,
            stage=stage,
            reviewer=reviewer,
            iteration=self._iteration,
            schema_name=self._submission.schema_name,
        )

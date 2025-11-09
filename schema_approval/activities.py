"""Activity implementations for the Schema Approval workflow."""

from __future__ import annotations

import asyncio
from typing import Iterable, List

from temporalio import activity

from .shared import (
    ApprovalRecord,
    ReviewDecision,
    ReviewRequest,
    SchemaSubmission,
    SchemaUploadRequest,
)


def _should_approve(required_attempts: int, attempt: int) -> bool:
    """Return ``True`` when the current attempt meets the approval threshold."""

    return attempt >= required_attempts


@activity.defn
async def upload_schema(request: SchemaUploadRequest) -> SchemaSubmission:
    """Simulate uploading a schema revision for review."""

    activity.logger.info(
        "Uploading schema '%s' version %s (attempt %s)",
        request.schema_name,
        request.target_version,
        request.attempt,
    )
    # Simulate I/O latency
    await asyncio.sleep(0.1)
    return SchemaSubmission(
        schema_name=request.schema_name,
        version=request.target_version,
        payload=request.schema_payload,
        attempt=request.attempt,
    )


def _review_notes(reviewer: str, approved: bool, attempt: int) -> str:
    if approved:
        return f"{reviewer} approved during attempt {attempt}."
    return f"{reviewer} requested revisions in attempt {attempt}."


async def _perform_review(request: ReviewRequest) -> ReviewDecision:
    approved = _should_approve(request.required_attempts_for_approval, request.attempt)
    await asyncio.sleep(0.05)
    notes = _review_notes(request.reviewer, approved, request.attempt)
    return ReviewDecision(
        reviewer=request.reviewer,
        approved=approved,
        notes=notes,
    )


@activity.defn
async def review_primary_a(request: ReviewRequest) -> ReviewDecision:
    """Primary reviewer A decision."""

    activity.logger.info("Review1.a evaluating attempt %s", request.attempt)
    return await _perform_review(request)


@activity.defn
async def review_primary_b(request: ReviewRequest) -> ReviewDecision:
    """Primary reviewer B decision."""

    activity.logger.info("Review1.b evaluating attempt %s", request.attempt)
    return await _perform_review(request)


@activity.defn
async def review_secondary(request: ReviewRequest) -> ReviewDecision:
    """Secondary review decides if tertiary review is required."""

    activity.logger.info("Review2 evaluating attempt %s", request.attempt)
    decision = await _perform_review(request)
    decision.skip_additional_review = decision.approved and not request.force_additional_review
    if decision.skip_additional_review:
        decision.notes = (decision.notes or "") + " Secondary reviewer skipped tertiary review."
    return decision


@activity.defn
async def review_tertiary(request: ReviewRequest) -> ReviewDecision:
    """Final review gate before approval."""

    activity.logger.info("Review3 evaluating attempt %s", request.attempt)
    decision = await _perform_review(request)
    decision.skip_additional_review = False
    return decision


def _summarize_decisions(decisions: Iterable[ReviewDecision]) -> str:
    outcome = [
        f"{decision.reviewer}: {'APPROVED' if decision.approved else 'REVISIONS'}"
        for decision in decisions
    ]
    return ", ".join(outcome)


@activity.defn
async def complete_review(
    submission: SchemaSubmission,
    decisions: List[ReviewDecision],
    approved: bool,
) -> ApprovalRecord:
    """Emit a final review record."""

    activity.logger.info(
        "Completing review for %s version %s with status %s",
        submission.schema_name,
        submission.version,
        "APPROVED" if approved else "REVISIONS",
    )
    await asyncio.sleep(0.05)
    message = _summarize_decisions(decisions)
    return ApprovalRecord(
        schema_name=submission.schema_name,
        version=submission.version,
        attempt=submission.attempt,
        approved=approved,
        message=message,
    )

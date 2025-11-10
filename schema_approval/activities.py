"""Activity implementations for the schema approval workflow."""

from __future__ import annotations

import logging

from temporalio import activity

from .shared import IterationSummary, ReviewDecision, ReviewRequest, SchemaSubmission

logger = logging.getLogger(__name__)


@activity.defn
async def upload_schema(submission: SchemaSubmission, iteration: int) -> str:
    """Pretend to upload the schema for the given iteration."""

    logger.info(
        "Uploading schema %s v%s for iteration %s", submission.schema_name, submission.version, iteration
    )
    await activity.sleep(0.1)
    return (
        "Schema %s version %s uploaded for review iteration %s" %
        (submission.schema_name, submission.version, iteration)
    )


@activity.defn
async def notify_reviewer(request: ReviewRequest) -> None:
    """Simulate notifying a reviewer that their action is required."""

    logger.info(
        "Notifying reviewer %s for %s (%s, iteration %s)",
        request.reviewer,
        request.schema_name,
        request.stage,
        request.iteration,
    )
    await activity.sleep(0.1)


@activity.defn
async def record_decision(decision: ReviewDecision) -> None:
    """Persist a review decision for auditing purposes."""

    logger.info(
        "Recorded decision %s: approved=%s requires_additional_review=%s comments=%s",
        decision.review_id,
        decision.approved,
        decision.requires_additional_review,
        decision.comments,
    )
    await activity.sleep(0.05)


@activity.defn
async def complete_review(summary: IterationSummary) -> bool:
    """Send a completion notification for the review iteration."""

    logger.info(
        "Completing iteration %s for schema %s with approval=%s",
        summary.iteration,
        summary.schema_name,
        summary.approved,
    )
    await activity.sleep(0.1)
    return summary.approved

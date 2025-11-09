"""Workflow starter for the schema approval sample."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from collections.abc import Mapping
from datetime import timedelta
from typing import Dict, List

from temporalio.client import Client, WorkflowHandle

from .shared import ReviewDecision, SchemaSubmission
from .workflow import SchemaApprovalWorkflow, TASK_QUEUE


async def _wait_for_pending(handle: WorkflowHandle, expected: int) -> List[str]:
    for _ in range(60):
        pending: List[str] = await handle.query("pending_reviews")
        if len(pending) >= expected:
            return pending
        await asyncio.sleep(0.5)
    raise TimeoutError("Timed out waiting for pending review tasks")


async def _send_review_decisions(
    handle: WorkflowHandle,
    iteration: int,
    approvals: Mapping[str, bool],
    review2: Mapping[str, object] | None,
    review3: Mapping[str, object] | None,
) -> None:
    await _wait_for_pending(handle, 2)
    for review_ref, approved in approvals.items():
        review_id = f"{review_ref}:iter-{iteration}"
        await handle.execute_update(
            "submit_review_decision",
            ReviewDecision(review_id=review_id, approved=approved),
        )

    if not all(approvals.values()):
        return

    await _wait_for_pending(handle, 1)
    review2_id = f"Review2:iter-{iteration}"
    review2_decision = ReviewDecision(
        review_id=review2_id,
        approved=bool(review2.get("approved", False)) if review2 else False,
        requires_additional_review=bool(review2.get("requires_additional_review", False))
        if review2
        else False,
        comments=str(review2.get("comments")) if review2 and "comments" in review2 else None,
    )
    await handle.execute_update("submit_review_decision", review2_decision)

    if not review2_decision.requires_additional_review:
        return

    if review3 is None:
        raise ValueError("Review3 decision is required when review2 requests additional review")

    await _wait_for_pending(handle, 1)
    review3_id = f"Review3:iter-{iteration}"
    review3_decision = ReviewDecision(
        review_id=review3_id,
        approved=bool(review3.get("approved", False)),
        requires_additional_review=False,
        comments=str(review3.get("comments")) if "comments" in review3 else None,
    )
    await handle.execute_update("submit_review_decision", review3_decision)


async def run_starter(scenario: str) -> None:
    client = await Client.connect("localhost:7233")
    submission = SchemaSubmission(
        schema_name="customer-profile",
        version=1,
        description="Schema used for storing customer profile information.",
        owner_email="owner@example.com",
    )

    handle = await client.start_workflow(
        SchemaApprovalWorkflow.run,
        submission,
        id=f"schema-approval-{uuid.uuid4()}",
        task_queue=TASK_QUEUE,
        execution_timeout=timedelta(minutes=5),
    )

    plans: Dict[str, List[Dict[str, object]]] = {
        "single-pass": [
            {
                "review1": {"review1.a": True, "review1.b": True},
                "review2": {"approved": True, "requires_additional_review": False},
            }
        ],
        "escalation": [
            {
                "review1": {"review1.a": True, "review1.b": False},
            },
            {
                "review1": {"review1.a": True, "review1.b": True},
                "review2": {
                    "approved": False,
                    "requires_additional_review": True,
                    "comments": "Need executive oversight",
                },
                "review3": {"approved": True},
            },
        ],
    }

    iterations = plans.get(scenario)
    if iterations is None:
        raise ValueError(f"Unknown scenario '{scenario}'")

    for index, iteration_plan in enumerate(iterations, start=1):
        await _send_review_decisions(
            handle,
            iteration=index,
            approvals=iteration_plan["review1"],
            review2=iteration_plan.get("review2"),
            review3=iteration_plan.get("review3"),
        )

    result = await handle.result()
    print(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the schema approval workflow")
    parser.add_argument(
        "--scenario",
        choices=["single-pass", "escalation"],
        default="single-pass",
        help="Predefined decision plan to drive the workflow",
    )
    args = parser.parse_args()

    asyncio.run(run_starter(args.scenario))


if __name__ == "__main__":
    main()

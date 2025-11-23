"""Interaction script for schema approval workflow.

This script sends approval updates to a running schema approval workflow
to simulate reviewer decisions at each checkpoint:
- Review1Check: After parallel Review1.a and Review1.b
- Review2Check: Decision to skip Review3 or proceed
- Review3Check: Final approval after Review3

Usage:
    uv run interact <workflow_id> [--approve-all | --reject-at STAGE]

Examples:
    # Approve at all stages (expedited path, skips Review3)
    uv run interact schema-approval-123 --approve-all

    # Approve at Review1 and Review2 (skips Review3)
    uv run interact schema-approval-123 --skip-review3

    # Reject at Review1 (workflow loops)
    uv run interact schema-approval-123 --reject-at Review1Check

    # Full path: approve all including Review3
    uv run interact schema-approval-123 --full-path
"""
import asyncio
import sys
from datetime import datetime
from typing import Optional

from temporalio.client import Client

from schema_approval_temporal.shared import ApprovalDecision, ApprovalResult


async def query_workflow_status(client: Client, workflow_id: str) -> dict:
    """Query the current workflow status.

    Args:
        client: Temporal client
        workflow_id: Workflow ID to query

    Returns:
        Dictionary with current workflow status
    """
    handle = client.get_workflow_handle(workflow_id)

    try:
        status = await handle.query("get_approval_status")
        return status
    except Exception as e:
        print(f"Error querying workflow status: {e}")
        return {}


async def send_review1_approval(
    client: Client,
    workflow_id: str,
    approved: bool,
    comments: Optional[str] = None
) -> ApprovalResult:
    """Send Review1 approval decision.

    Args:
        client: Temporal client
        workflow_id: Workflow ID
        approved: Whether to approve (YES) or reject (NO)
        comments: Optional review comments

    Returns:
        ApprovalResult from the workflow
    """
    handle = client.get_workflow_handle(workflow_id)

    decision = ApprovalDecision(
        reviewer_id="reviewer-1a",
        approved=approved,
        decision="YES" if approved else "NO",
        stage="Review1Check",
        comments=comments or f"Review1 {'approved' if approved else 'rejected'}",
        timestamp=datetime.now(),
        skip_review3=False,
    )

    print(f"\n📤 Sending Review1 approval: {decision.decision}")
    result = await handle.execute_update(
        "submit_review1_approval",
        decision,
    )
    print(f"✅ {result.message}")
    return result


async def send_review2_approval(
    client: Client,
    workflow_id: str,
    approved: bool,
    skip_review3: bool = False,
    comments: Optional[str] = None
) -> ApprovalResult:
    """Send Review2 approval decision.

    Args:
        client: Temporal client
        workflow_id: Workflow ID
        approved: Whether to approve (YES) or reject (NO)
        skip_review3: Whether to skip Review3 (expedited path)
        comments: Optional review comments

    Returns:
        ApprovalResult from the workflow
    """
    handle = client.get_workflow_handle(workflow_id)

    decision = ApprovalDecision(
        reviewer_id="reviewer-2",
        approved=approved,
        decision="YES" if approved else "NO",
        stage="Review2Check",
        comments=comments or f"Review2 {'approved' if approved else 'rejected'}" +
                 (f" (skip Review3: {skip_review3})" if approved else ""),
        timestamp=datetime.now(),
        skip_review3=skip_review3,
    )

    print(f"\n📤 Sending Review2 approval: {decision.decision} (skip_review3={skip_review3})")
    result = await handle.execute_update(
        "submit_review2_approval",
        decision,
    )
    print(f"✅ {result.message}")
    return result


async def send_review3_approval(
    client: Client,
    workflow_id: str,
    approved: bool,
    comments: Optional[str] = None
) -> ApprovalResult:
    """Send Review3 approval decision (final approval).

    Args:
        client: Temporal client
        workflow_id: Workflow ID
        approved: Whether to approve (YES) or reject (NO)
        comments: Optional review comments

    Returns:
        ApprovalResult from the workflow
    """
    handle = client.get_workflow_handle(workflow_id)

    decision = ApprovalDecision(
        reviewer_id="reviewer-3",
        approved=approved,
        decision="YES" if approved else "NO",
        stage="Review3Check",
        comments=comments or f"Review3 final {'approval' if approved else 'rejection'}",
        timestamp=datetime.now(),
        skip_review3=False,
    )

    print(f"\n📤 Sending Review3 approval: {decision.decision}")
    result = await handle.execute_update(
        "submit_review3_approval",
        decision,
    )
    print(f"✅ {result.message}")
    return result


async def approve_all_expedited(client: Client, workflow_id: str) -> None:
    """Approve at all stages with expedited path (skip Review3).

    This tests the Review2Check YES branch → CompleteReview_1 path.

    Args:
        client: Temporal client
        workflow_id: Workflow ID
    """
    print("🚀 Testing expedited approval path (skip Review3)")

    # Wait a bit for workflow to reach Review1Check
    await asyncio.sleep(2)

    # Approve Review1
    await send_review1_approval(client, workflow_id, approved=True)

    # Wait for workflow to reach Review2Check
    await asyncio.sleep(2)

    # Approve Review2 with skip_review3=True
    await send_review2_approval(client, workflow_id, approved=True, skip_review3=True)

    print("\n✅ Expedited approval path completed!")


async def approve_all_full_path(client: Client, workflow_id: str) -> None:
    """Approve at all stages including Review3 (full review path).

    This tests the Review2Check NO branch → Review3 → Review3Check YES branch path.

    Args:
        client: Temporal client
        workflow_id: Workflow ID
    """
    print("🚀 Testing full approval path (including Review3)")

    # Wait a bit for workflow to reach Review1Check
    await asyncio.sleep(2)

    # Approve Review1
    await send_review1_approval(client, workflow_id, approved=True)

    # Wait for workflow to reach Review2Check
    await asyncio.sleep(2)

    # Approve Review2 but don't skip Review3
    await send_review2_approval(client, workflow_id, approved=True, skip_review3=False)

    # Wait for workflow to reach Review3Check
    await asyncio.sleep(2)

    # Approve Review3 (final approval)
    await send_review3_approval(client, workflow_id, approved=True)

    print("\n✅ Full approval path completed!")


async def reject_at_stage(client: Client, workflow_id: str, stage: str) -> None:
    """Reject at a specific stage to test loop behavior.

    Args:
        client: Temporal client
        workflow_id: Workflow ID
        stage: Stage to reject at ("Review1Check", "Review2Check", or "Review3Check")
    """
    print(f"🚀 Testing rejection at {stage}")

    # Wait a bit for workflow to start
    await asyncio.sleep(2)

    if stage == "Review1Check":
        await send_review1_approval(client, workflow_id, approved=False)
        print("\n❌ Rejected at Review1 - workflow will loop")

    elif stage == "Review2Check":
        # First approve Review1
        await send_review1_approval(client, workflow_id, approved=True)
        await asyncio.sleep(2)
        # Then reject at Review2
        await send_review2_approval(client, workflow_id, approved=False)
        print("\n❌ Rejected at Review2 - workflow will loop")

    elif stage == "Review3Check":
        # Approve Review1 and Review2 (without skipping Review3)
        await send_review1_approval(client, workflow_id, approved=True)
        await asyncio.sleep(2)
        await send_review2_approval(client, workflow_id, approved=True, skip_review3=False)
        await asyncio.sleep(2)
        # Then reject at Review3
        await send_review3_approval(client, workflow_id, approved=False)
        print("\n❌ Rejected at Review3 - workflow will loop")

    else:
        print(f"❌ Unknown stage: {stage}")


async def interactive_mode(client: Client, workflow_id: str) -> None:
    """Interactive mode - prompt user for each decision.

    Args:
        client: Temporal client
        workflow_id: Workflow ID
    """
    print("🎮 Interactive mode - you'll be prompted for each decision")

    # Wait for workflow to start
    await asyncio.sleep(2)

    # Review1
    print("\n" + "="*60)
    status = await query_workflow_status(client, workflow_id)
    print(f"Current stage: {status.get('current_stage', 'unknown')}")

    review1_input = input("\nApprove Review1? (y/n): ").strip().lower()
    await send_review1_approval(client, workflow_id, approved=review1_input == 'y')

    if review1_input != 'y':
        print("\n❌ Review1 rejected - workflow will loop")
        return

    # Review2
    await asyncio.sleep(2)
    print("\n" + "="*60)
    status = await query_workflow_status(client, workflow_id)
    print(f"Current stage: {status.get('current_stage', 'unknown')}")

    review2_input = input("\nApprove Review2? (y/n): ").strip().lower()
    if review2_input != 'y':
        await send_review2_approval(client, workflow_id, approved=False)
        print("\n❌ Review2 rejected - workflow will loop")
        return

    skip_review3_input = input("Skip Review3? (y/n): ").strip().lower()
    skip_review3 = skip_review3_input == 'y'

    await send_review2_approval(client, workflow_id, approved=True, skip_review3=skip_review3)

    if skip_review3:
        print("\n✅ Expedited approval - workflow completed!")
        return

    # Review3
    await asyncio.sleep(2)
    print("\n" + "="*60)
    status = await query_workflow_status(client, workflow_id)
    print(f"Current stage: {status.get('current_stage', 'unknown')}")

    review3_input = input("\nApprove Review3 (final)? (y/n): ").strip().lower()
    await send_review3_approval(client, workflow_id, approved=review3_input == 'y')

    if review3_input == 'y':
        print("\n✅ Full approval path - workflow completed!")
    else:
        print("\n❌ Review3 rejected - workflow will loop")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    workflow_id = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--interactive"
    stage = sys.argv[3] if len(sys.argv) > 3 else None

    async def run() -> None:
        # Connect to Temporal server
        client = await Client.connect("localhost:7233")

        print(f"🔗 Connected to Temporal server")
        print(f"🎯 Workflow ID: {workflow_id}")

        # Query initial status
        status = await query_workflow_status(client, workflow_id)
        print(f"📊 Current status: {status}")

        # Execute based on mode
        if mode == "--approve-all" or mode == "--skip-review3":
            await approve_all_expedited(client, workflow_id)
        elif mode == "--full-path":
            await approve_all_full_path(client, workflow_id)
        elif mode == "--reject-at":
            if not stage:
                print("❌ Error: --reject-at requires a stage argument")
                print("   Valid stages: Review1Check, Review2Check, Review3Check")
                sys.exit(1)
            await reject_at_stage(client, workflow_id, stage)
        elif mode == "--interactive":
            await interactive_mode(client, workflow_id)
        else:
            print(f"❌ Unknown mode: {mode}")
            print(__doc__)
            sys.exit(1)

    asyncio.run(run())


if __name__ == "__main__":
    main()

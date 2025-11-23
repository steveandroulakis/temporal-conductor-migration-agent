"""Fixed interaction script for schema approval workflow."""
import asyncio
import sys
from datetime import datetime
from typing import Optional

from temporalio.client import Client

from schema_approval_temporal.shared import ApprovalDecision


async def query_workflow_status(client: Client, workflow_id: str) -> dict:
    """Query the current workflow status."""
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
) -> dict:
    """Send Review1 approval decision."""
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
    # Result is a dict, not ApprovalResult dataclass
    print(f"✅ {result['message']}")
    return result


async def send_review2_approval(
    client: Client,
    workflow_id: str,
    approved: bool,
    skip_review3: bool = False,
    comments: Optional[str] = None
) -> dict:
    """Send Review2 approval decision."""
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
    print(f"✅ {result['message']}")
    return result


async def send_review3_approval(
    client: Client,
    workflow_id: str,
    approved: bool,
    comments: Optional[str] = None
) -> dict:
    """Send Review3 approval decision (final approval)."""
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
    print(f"✅ {result['message']}")
    return result


async def approve_all_expedited(client: Client, workflow_id: str) -> None:
    """Approve at all stages with expedited path (skip Review3)."""
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
    """Approve at all stages including Review3 (full review path)."""
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
    """Reject at a specific stage to test loop behavior."""
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


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python interact_fixed.py <workflow_id> [--approve-all | --full-path | --reject-at STAGE]")
        sys.exit(1)

    workflow_id = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--approve-all"
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
        else:
            print(f"❌ Unknown mode: {mode}")
            sys.exit(1)

    asyncio.run(run())


if __name__ == "__main__":
    main()

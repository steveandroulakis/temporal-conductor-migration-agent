"""Workflow interaction client.

This client allows you to interact with running workflows:
- Send Updates (for human approvals with validation)
- Execute Queries (for checking workflow status)

This workflow implements a multi-stage approval process with three checkpoints:
  1. Review1Check - After parallel reviews (Review1.a, Review1.b)
  2. Review2Check - After second stage review
  3. Review3Check - After third stage review (if needed)

Usage:
    # Send an Update (approval decision)
    uv run interact update <workflow-id> <update-name> <json-args>

    # Execute a Query (check status)
    uv run interact query <workflow-id> <query-name>

Examples:
    # Submit Review1 approval (after Review1.a and Review1.b complete)
    uv run interact update <workflow-id> submit_review1_approval '{"reviewer_id": "reviewer1", "approved": true}'

    # Submit Review2 approval (skip Review3)
    uv run interact update <workflow-id> submit_review2_approval '{"reviewer_id": "reviewer2", "approved": true, "skip_review3": true}'

    # Submit Review2 approval (require Review3)
    uv run interact update <workflow-id> submit_review2_approval '{"reviewer_id": "reviewer2", "approved": true, "skip_review3": false}'

    # Submit Review3 approval (final approval)
    uv run interact update <workflow-id> submit_review3_approval '{"reviewer_id": "reviewer3", "approved": true}'

    # Check workflow status
    uv run interact query <workflow-id> get_status
"""
import asyncio
import json
import sys
from typing import Any
from temporalio.client import Client

from .workflow import SchemaApprovalWorkflow
from .shared import ApprovalDecision


async def send_update(
    workflow_id: str,
    update_name: str,
    args: dict[str, Any]
) -> None:
    """Send an Update to a running workflow."""
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)

    print(f"Sending Update '{update_name}' to workflow {workflow_id}")
    print(f"Arguments: {json.dumps(args, indent=2)}")

    try:
        if update_name == "submit_review1_approval":
            # Review1Check approval - after Review1.a and Review1.b complete
            decision = ApprovalDecision(
                reviewer_id=args.get("reviewer_id", "unknown"),
                approved=args.get("approved", False),
                comments=args.get("comments"),
            )
            result = await handle.execute_update(
                SchemaApprovalWorkflow.submit_review1_approval,
                decision
            )
            print(f"\nUpdate accepted!")
            print(f"Status: {result.status}")
            print(f"Message: {result.message}")
            print(f"Reviewer: {result.reviewer}")
            print(f"Current Stage: {result.current_stage}")

        elif update_name == "submit_review2_approval":
            # Review2Check approval - determines if Review3 is needed
            decision = ApprovalDecision(
                reviewer_id=args.get("reviewer_id", "unknown"),
                approved=args.get("approved", False),
                skip_review3=args.get("skip_review3", False),
                comments=args.get("comments"),
            )
            result = await handle.execute_update(
                SchemaApprovalWorkflow.submit_review2_approval,
                decision
            )
            print(f"\nUpdate accepted!")
            print(f"Status: {result.status}")
            print(f"Message: {result.message}")
            print(f"Reviewer: {result.reviewer}")
            print(f"Current Stage: {result.current_stage}")
            if decision.skip_review3:
                print("NOTE: Review3 will be SKIPPED - workflow will complete after this approval")
            else:
                print("NOTE: Review3 will be REQUIRED - workflow will proceed to Review3")

        elif update_name == "submit_review3_approval":
            # Review3Check approval - final approval checkpoint
            decision = ApprovalDecision(
                reviewer_id=args.get("reviewer_id", "unknown"),
                approved=args.get("approved", False),
                comments=args.get("comments"),
            )
            result = await handle.execute_update(
                SchemaApprovalWorkflow.submit_review3_approval,
                decision
            )
            print(f"\nUpdate accepted!")
            print(f"Status: {result.status}")
            print(f"Message: {result.message}")
            print(f"Reviewer: {result.reviewer}")
            print(f"Current Stage: {result.current_stage}")
            if decision.approved:
                print("NOTE: Final approval granted - workflow will complete")
            else:
                print("NOTE: Approval denied - workflow will restart loop")

        else:
            print(f"Error: Unknown update: {update_name}", file=sys.stderr)
            print(f"Available updates: submit_review1_approval, submit_review2_approval, submit_review3_approval", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: Update failed: {e}", file=sys.stderr)
        sys.exit(1)


async def execute_query(
    workflow_id: str,
    query_name: str
) -> None:
    """Execute a Query on a running workflow."""
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)

    print(f"Executing Query '{query_name}' on workflow {workflow_id}")

    try:
        if query_name == "get_status":
            result = await handle.query(
                SchemaApprovalWorkflow.get_status
            )
            print(f"\nWorkflow Status:")
            print(f"{'='*60}")
            print(json.dumps(result, indent=2, default=str))
            print(f"{'='*60}")

            # Display helpful summary
            print(f"\nSummary:")
            print(f"  Current Stage: {result.get('current_stage')}")
            print(f"  Iteration: {result.get('iteration')}")
            print(f"  Approved: {result.get('approved')}")

            # Review1 status
            review1 = result.get('review1_status', {})
            print(f"\n  Review1 Status:")
            print(f"    Review1.a completed: {review1.get('review1a_completed')}")
            print(f"    Review1.b completed: {review1.get('review1b_completed')}")
            print(f"    Approval received: {review1.get('approval_received')}")
            print(f"    Approved: {review1.get('approved')}")

            # Review2 status
            review2 = result.get('review2_status', {})
            print(f"\n  Review2 Status:")
            print(f"    Review2 completed: {review2.get('review2_completed')}")
            print(f"    Approval received: {review2.get('approval_received')}")
            print(f"    Approved: {review2.get('approved')}")
            print(f"    Skip Review3: {review2.get('skip_review3')}")

            # Review3 status
            review3 = result.get('review3_status', {})
            print(f"\n  Review3 Status:")
            print(f"    Review3 completed: {review3.get('review3_completed')}")
            print(f"    Approval received: {review3.get('approval_received')}")
            print(f"    Approved: {review3.get('approved')}")

            # Provide guidance on next action
            current_stage = result.get('current_stage')
            if current_stage == 'review1_check':
                print(f"\nNext Action:")
                print(f"  Submit Review1 approval decision:")
                print(f"  uv run interact update {workflow_id} submit_review1_approval '{{\"reviewer_id\": \"your_id\", \"approved\": true}}'")
            elif current_stage == 'review2_check':
                print(f"\nNext Action:")
                print(f"  Submit Review2 approval decision:")
                print(f"  uv run interact update {workflow_id} submit_review2_approval '{{\"reviewer_id\": \"your_id\", \"approved\": true, \"skip_review3\": false}}'")
            elif current_stage == 'review3_check':
                print(f"\nNext Action:")
                print(f"  Submit Review3 (final) approval decision:")
                print(f"  uv run interact update {workflow_id} submit_review3_approval '{{\"reviewer_id\": \"your_id\", \"approved\": true}}'")
            elif current_stage == 'completed':
                print(f"\nWorkflow has completed!")
            else:
                print(f"\nWorkflow is in progress (current stage: {current_stage})")

        else:
            print(f"Error: Unknown query: {query_name}", file=sys.stderr)
            print(f"Available queries: get_status", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: Query failed: {e}", file=sys.stderr)
        sys.exit(1)


def print_usage() -> None:
    """Print usage instructions."""
    print("Usage: uv run interact <command> <workflow-id> [args...]")
    print("")
    print("Commands:")
    print("  update <workflow-id> <update-name> <json-args>")
    print("  query <workflow-id> <query-name>")
    print("")
    print("=" * 60)
    print("Available Updates:")
    print("=" * 60)
    print("")
    print("1. submit_review1_approval:")
    print("   Submit approval decision after Review1.a and Review1.b complete")
    print("   Example:")
    print("     uv run interact update <wf-id> submit_review1_approval \\")
    print("       '{\"reviewer_id\": \"reviewer1\", \"approved\": true}'")
    print("")
    print("2. submit_review2_approval:")
    print("   Submit approval decision after Review2, decide if Review3 is needed")
    print("   Example (skip Review3):")
    print("     uv run interact update <wf-id> submit_review2_approval \\")
    print("       '{\"reviewer_id\": \"reviewer2\", \"approved\": true, \"skip_review3\": true}'")
    print("   Example (require Review3):")
    print("     uv run interact update <wf-id> submit_review2_approval \\")
    print("       '{\"reviewer_id\": \"reviewer2\", \"approved\": true, \"skip_review3\": false}'")
    print("")
    print("3. submit_review3_approval:")
    print("   Submit final approval decision after Review3")
    print("   Example:")
    print("     uv run interact update <wf-id> submit_review3_approval \\")
    print("       '{\"reviewer_id\": \"reviewer3\", \"approved\": true}'")
    print("")
    print("=" * 60)
    print("Available Queries:")
    print("=" * 60)
    print("")
    print("1. get_status:")
    print("   Get current workflow status, review progress, and next action")
    print("   Example:")
    print("     uv run interact query <wf-id> get_status")
    print("")


def main() -> None:
    """Console script entry point."""
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    workflow_id = sys.argv[2]

    try:
        if command == "update":
            if len(sys.argv) < 5:
                print("Error: Update requires update-name and json-args", file=sys.stderr)
                print_usage()
                sys.exit(1)
            update_name = sys.argv[3]
            args = json.loads(sys.argv[4])
            asyncio.run(send_update(workflow_id, update_name, args))

        elif command == "query":
            if len(sys.argv) < 4:
                print("Error: Query requires query-name", file=sys.stderr)
                print_usage()
                sys.exit(1)
            query_name = sys.argv[3]
            asyncio.run(execute_query(workflow_id, query_name))

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            print_usage()
            sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

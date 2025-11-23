"""Workflow starter client.

This client:
- Connects to Temporal server
- Creates example workflow input
- Starts the workflow
- Waits for completion
- Displays results

Usage:
    After running 'uv sync', execute:
    uv run starter
"""
import asyncio
import logging
import sys
import uuid
from datetime import timedelta
from temporalio.client import Client

from .workflow import SchemaApprovalWorkflow
from .shared import WorkflowInput


async def run_starter() -> None:
    """Start workflow execution."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # Connect to Temporal server
        client = await Client.connect("localhost:7233")
        logger.info("Connected to Temporal server at localhost:7233")

        # Create workflow input with example data
        # TODO: Customize these values for your use case
        # These are example values generated from the workflow schema
        workflow_input = WorkflowInput(
            submission_id=f"schema-submission-{uuid.uuid4().hex[:8]}",
            schema_data={
                "schema_name": "user_profile_v2",
                "version": "2.0",
                "fields": [
                    {"name": "user_id", "type": "string", "required": True},
                    {"name": "email", "type": "string", "required": True},
                    {"name": "age", "type": "integer", "required": False},
                ],
                "description": "Updated user profile schema with additional fields"
            },
            submitter_email="user@example.com",
            priority=1
        )

        logger.info(f"Workflow input: submission_id={workflow_input.submission_id}, "
                   f"submitter={workflow_input.submitter_email}")

        # Generate unique workflow ID
        workflow_id = f"schema-approval-{uuid.uuid4()}"

        logger.info(f"Starting workflow: {workflow_id}")
        print(f"\nStarting workflow: {workflow_id}")
        print(f"Task queue: schema-approval-task-queue")
        print(f"Submission ID: {workflow_input.submission_id}")

        # Start workflow execution
        # NOTE: This workflow requires human interaction via Updates
        # The workflow will wait at approval checkpoints for external input
        handle = await client.start_workflow(
            SchemaApprovalWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="schema-approval-task-queue",
            execution_timeout=timedelta(hours=24)  # Allow time for human approvals
        )

        # Display workflow URL
        workflow_url = f"http://localhost:8233/namespaces/default/workflows/{handle.id}"
        print(f"\nWorkflow URL: {workflow_url}")
        print(f"\n{'='*60}")
        print("IMPORTANT: This workflow requires human interaction!")
        print("{'='*60}")
        print("\nThe workflow will pause at three approval checkpoints:")
        print("  1. Review1Check - After parallel reviews (Review1.a, Review1.b)")
        print("  2. Review2Check - After second stage review")
        print("  3. Review3Check - After third stage review (if needed)")
        print("\nTo submit approvals, use the interact script:")
        print(f"  uv run interact update {handle.id} submit_review1_approval '{{\"reviewer_id\": \"reviewer1\", \"approved\": true}}'")
        print(f"\nTo check workflow status:")
        print(f"  uv run interact query {handle.id} get_status")
        print("\nSee README.md for complete interaction guide.")
        print(f"{'='*60}\n")

        print(f"Waiting for workflow to complete...")
        print("(This may take a while as it requires human approvals)\n")

        # Wait for workflow to complete
        # NOTE: This will block until all approvals are received and workflow completes
        result = await handle.result()

        # Display result
        print(f"\n{'='*60}")
        print(f"Workflow completed successfully!")
        print(f"{'='*60}")
        print(f"Workflow ID: {handle.id}")
        print(f"Status: {result.status}")
        print(f"Approval Stage: {result.approval_stage}")
        print(f"Total Iterations: {result.total_iterations}")
        print(f"Completed At: {result.completed_at}")
        print(f"Final Decision: {result.final_decision}")
        print(f"{'='*60}\n")

        logger.info(f"Workflow completed: {handle.id}")

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        print(f"\nError: {e}", file=sys.stderr)
        raise


def main() -> None:
    """Console script entry point.

    This function is called when running 'uv run starter'.
    It must be synchronous (not async) for console script compatibility.
    """
    try:
        asyncio.run(run_starter())
    except KeyboardInterrupt:
        print("\nWorkflow starter interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Workflow starter failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

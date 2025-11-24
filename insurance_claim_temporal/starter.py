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

from .workflow import InsuranceClaimWorkflow
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
            first_name="John",
            last_name="Smith"
        )

        logger.info(f"Workflow input: {workflow_input}")

        # Generate unique workflow ID
        workflow_id = f"insurance-claim-{uuid.uuid4()}"

        logger.info(f"Starting workflow: {workflow_id}")
        print(f"\nStarting workflow: {workflow_id}")
        print(f"Task queue: insurance-claim-task-queue")

        # Start workflow execution
        handle = await client.start_workflow(
            InsuranceClaimWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="insurance-claim-task-queue",
            execution_timeout=timedelta(hours=72)  # Allow 3 days for human interactions
        )

        # Display workflow URL
        workflow_url = f"http://localhost:8233/namespaces/default/workflows/{handle.id}"
        print(f"Workflow URL: {workflow_url}")
        print(f"\nWorkflow started and running...")
        print(f"This is an INTERACTIVE workflow with human interaction points.")
        print(f"\nTo interact with the workflow, use the 'interact' command:")
        print(f"  uv run interact update {workflow_id} submit_claim '<json-args>'")
        print(f"\nThe workflow will wait for human input at these stages:")
        print(f"  1. Claim submission (submit_claim)")
        print(f"  2. Assessor findings (submit_assessor_findings)")
        print(f"  3. Investigation findings (submit_investigation_findings) - if cost exceeds threshold")
        print(f"\nMonitor workflow progress at: {workflow_url}")
        print(f"\nPress Ctrl+C to stop monitoring (workflow will continue running)")

        # Wait for workflow to complete (or user to interrupt)
        try:
            result = await handle.result()

            # Display result
            print(f"\n{'='*60}")
            print(f"Workflow completed!")
            print(f"{'='*60}")
            print(f"Workflow ID: {handle.id}")
            print(f"Status: {result.status}")
            print(f"Reason: {result.reason}")
            if result.details:
                print(f"Details: {result.details}")
            print(f"{'='*60}\n")

            logger.info(f"Workflow completed: {handle.id}")

        except KeyboardInterrupt:
            print(f"\n\nStopped monitoring workflow.")
            print(f"Workflow is still running at: {workflow_url}")
            print(f"To check status: temporal workflow describe -w {workflow_id}")

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
        sys.exit(0)
    except Exception as e:
        print(f"Workflow starter failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

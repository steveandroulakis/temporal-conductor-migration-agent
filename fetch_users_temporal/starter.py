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

from .workflow import FetchUsersWorkflow
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
        # Note: This workflow has no input parameters in the original Conductor definition
        workflow_input = WorkflowInput()

        logger.info("Workflow input: (no parameters)")

        # Generate unique workflow ID
        workflow_id = f"fetch_users-{uuid.uuid4()}"

        logger.info(f"Starting workflow: {workflow_id}")
        print(f"\nStarting workflow: {workflow_id}")
        print(f"Task queue: fetch-users-task-queue")

        # Start workflow execution
        handle = await client.start_workflow(
            FetchUsersWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="fetch-users-task-queue",
            execution_timeout=timedelta(hours=1)
        )

        # Display workflow URL
        workflow_url = f"http://localhost:8233/namespaces/default/workflows/{handle.id}"
        print(f"Workflow URL: {workflow_url}")
        print(f"\nWaiting for workflow to complete...")

        # Wait for workflow to complete
        result = await handle.result()

        # Display result
        print(f"\n{'='*60}")
        print(f"Workflow completed successfully!")
        print(f"{'='*60}")
        print(f"Workflow ID: {handle.id}")
        print(f"Result: {len(result.users)} users found")
        print(f"\nFiltered Users:")
        for user in result.users:
            print(f"  - {user.get('name', 'Unknown')} (ID: {user.get('id', 'N/A')})")
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

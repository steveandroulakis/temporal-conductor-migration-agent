"""Workflow starter client.

This client:
- Connects to Temporal server
- Creates example workflow input
- Starts the workflow
- Waits for completion (or timeout)
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

from .workflow import ShoppingCartWorkflow
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
            items=["item1", "item2", "item3"]
        )

        logger.info(f"Workflow input: {workflow_input}")

        # Generate unique workflow ID
        workflow_id = f"shopping-cart-{uuid.uuid4()}"

        logger.info(f"Starting workflow: {workflow_id}")
        print(f"\nStarting workflow: {workflow_id}")
        print(f"Task queue: shopping-cart-task-queue")

        # Start workflow execution
        handle = await client.start_workflow(
            ShoppingCartWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="shopping-cart-task-queue",
            execution_timeout=timedelta(hours=48)  # Extended timeout for human interaction
        )

        # Display workflow URL
        workflow_url = f"http://localhost:8233/namespaces/default/workflows/{handle.id}"
        print(f"Workflow URL: {workflow_url}")
        print(f"\nWorkflow started and waiting for interaction.")
        print(f"\nThis workflow requires human interaction via Updates:")
        print(f"  1. Use 'uv run interact' to send cart updates")
        print(f"  2. Use 'uv run interact' to confirm checkout")
        print(f"\nFor more details, run: uv run interact")
        print(f"\nTo query workflow status, run:")
        print(f"  uv run interact query {workflow_id} get_cart_status")

        logger.info(f"Workflow started: {handle.id}")
        logger.info("Workflow is waiting for human interaction (Updates)")
        logger.info("Use interact.py to send Updates and complete the workflow")

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

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

from check_address_temporal.workflow import CheckAddressWorkflow
from check_address_temporal.shared import WorkflowInput


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
        # These are example values based on the workflow schema
        workflow_input = WorkflowInput(
            street="1600 Pennsylvania Avenue NW",
            city="Washington",
            state="DC",
            zip="20500"
        )

        logger.info(f"Workflow input: {workflow_input}")

        # Generate unique workflow ID
        workflow_id = f"check-address-{uuid.uuid4()}"

        logger.info(f"Starting workflow: {workflow_id}")
        print(f"\nStarting CheckAddress workflow")
        print(f"Workflow ID: {workflow_id}")
        print(f"Task queue: check-address-task-queue")
        print(f"Address: {workflow_input.street}, {workflow_input.city}, {workflow_input.state} {workflow_input.zip}")

        # Start workflow execution
        handle = await client.start_workflow(
            CheckAddressWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="check-address-task-queue",
            execution_timeout=timedelta(hours=1)
        )

        # Display workflow URL
        workflow_url = f"http://localhost:8233/namespaces/default/workflows/{handle.id}"
        print(f"\nWorkflow URL: {workflow_url}")
        print(f"Waiting for workflow to complete...")

        # Wait for workflow to complete
        result = await handle.result()

        # Display result
        print(f"\n{'='*60}")
        if result.success:
            print(f"Workflow completed successfully!")
            print(f"{'='*60}")
            print(f"Workflow ID: {handle.id}")
            print(f"\nValidated Address:")
            if result.parsed_address:
                print(f"  Street: {result.parsed_address.street}")
                print(f"  City:   {result.parsed_address.city}")
                print(f"  State:  {result.parsed_address.state}")
                print(f"  ZIP:    {result.parsed_address.zip}")
        else:
            print(f"Address validation failed")
            print(f"{'='*60}")
            print(f"Workflow ID: {handle.id}")
            print(f"\nError: {result.error_message}")

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

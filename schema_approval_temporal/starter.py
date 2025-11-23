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
            schema_id="example-schema-001",
            schema_content={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "email": {"type": "string", "format": "email"}
                },
                "required": ["name", "email"]
            },
            submitter_id="user-123",
            priority=1,
            metadata={
                "department": "engineering",
                "project": "data-platform",
                "version": "1.0.0"
            }
        )

        logger.info(f"Workflow input: schema_id={workflow_input.schema_id}")

        # Generate unique workflow ID
        workflow_id = f"schema-approval-{uuid.uuid4()}"

        logger.info(f"Starting workflow: {workflow_id}")
        print(f"\nStarting Schema Approval Workflow")
        print(f"{'='*60}")
        print(f"Workflow ID: {workflow_id}")
        print(f"Schema ID: {workflow_input.schema_id}")
        print(f"Submitter: {workflow_input.submitter_id}")
        print(f"Task queue: schema-approval-task-queue")
        print(f"{'='*60}\n")

        # Start workflow execution
        handle = await client.start_workflow(
            SchemaApprovalWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="schema-approval-task-queue",
            execution_timeout=timedelta(hours=24)
        )

        # Display workflow URL
        workflow_url = f"http://localhost:8233/namespaces/default/workflows/{handle.id}"
        print(f"Workflow URL: {workflow_url}")
        print(f"Monitor progress in the Temporal Web UI")
        print(f"\nWaiting for workflow to complete...")
        print(f"(This may take a while as the workflow waits for human approvals)\n")

        # Wait for workflow to complete
        result = await handle.result()

        # Display result
        print(f"\n{'='*60}")
        print(f"Workflow Completed Successfully!")
        print(f"{'='*60}")
        print(f"Workflow ID: {handle.id}")
        print(f"Status: {result.status}")
        print(f"Approved: {result.approved}")
        print(f"Schema ID: {result.schema_id}")
        print(f"Final approval stage: {result.final_approval_stage}")
        print(f"Total iterations: {result.iterations}")
        print(f"Completed at: {result.completed_at}")
        print(f"\nApproval History:")
        for i, approval in enumerate(result.approval_history, 1):
            print(f"  {i}. {approval}")
        print(f"{'='*60}\n")

        logger.info(f"Workflow completed: {handle.id}")

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        print(f"\n{'='*60}")
        print(f"ERROR: Workflow execution failed")
        print(f"{'='*60}")
        print(f"Error: {e}", file=sys.stderr)
        print(f"{'='*60}\n")
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

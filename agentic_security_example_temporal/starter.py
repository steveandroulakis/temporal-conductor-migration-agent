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

from .workflow import AgenticSecurityExampleWorkflow
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
        # Note: This workflow uses mock data by default if alerts not provided
        workflow_input = WorkflowInput(
            notification_channel="email",
            recipient_role="security_team",
            # Optional: Provide custom alert data instead of using mocks
            # security_malsite_alerts=None,
            # security_malware_alerts=None,
        )

        logger.info(f"Workflow input: notification_channel={workflow_input.notification_channel}, "
                   f"recipient_role={workflow_input.recipient_role}")
        logger.info("Using default mock security alert data (no custom alerts provided)")

        # Generate unique workflow ID
        workflow_id = f"agentic-security-example-{uuid.uuid4()}"

        logger.info(f"Starting workflow: {workflow_id}")
        print(f"\nStarting workflow: {workflow_id}")
        print(f"Task queue: agentic-security-example-task-queue")
        print(f"Notification channel: {workflow_input.notification_channel}")

        # Start workflow execution
        handle = await client.start_workflow(
            AgenticSecurityExampleWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="agentic-security-example-task-queue",
            execution_timeout=timedelta(hours=1)
        )

        # Display workflow URL
        workflow_url = f"http://localhost:8233/namespaces/default/workflows/{handle.id}"
        print(f"Workflow URL: {workflow_url}")
        print(f"\nWaiting for workflow to complete...")
        print(f"This workflow will:")
        print(f"  1. Process security alerts (malware + malicious sites)")
        print(f"  2. Analyze threats using LLM (OpenAI GPT-4o-mini)")
        print(f"  3. Validate findings against extracted data")
        print(f"  4. Optionally execute deep scans (if threat clusters found)")
        print(f"  5. Send notification via email")

        # Wait for workflow to complete
        result = await handle.result()

        # Display result
        print(f"\n{'='*60}")
        print(f"Workflow completed successfully!")
        print(f"{'='*60}")
        print(f"Workflow ID: {handle.id}")
        print(f"Notified Channel: {result.notified_channel}")
        print(f"Action Recommendation: {result.action_recommendation}")
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

"""Workflow starter utility for the Schema Approval migration."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import timedelta

from temporalio.client import Client

from .shared import WorkflowInput
from .workflow import SchemaApprovalWorkflow, TASK_QUEUE


async def run_starter() -> None:
    """Connect to Temporal and start the workflow."""

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    client = await Client.connect("localhost:7233")

    workflow_input = WorkflowInput(
        schema_name="inventory-schema",
        schema_payload='{"type": "record", "name": "InventoryItem"}',
        initial_version=1,
        required_attempts_for_approval=2,
        always_require_tertiary_review=False,
    )

    workflow_id = f"schema-approval-{uuid.uuid4()}"
    logger.info("Starting workflow %s", workflow_id)

    handle = await client.start_workflow(
        SchemaApprovalWorkflow.run,
        workflow_input,
        id=workflow_id,
        task_queue=TASK_QUEUE,
        execution_timeout=timedelta(hours=1),
    )

    print(f"Started workflow: {handle.id}")
    print(f"Workflow URL: http://localhost:8233/namespaces/default/workflows/{handle.id}")

    result = await handle.result()
    print("Workflow result:")
    print(result)


def main() -> None:
    """Console script entry point for the starter."""

    asyncio.run(run_starter())


if __name__ == "__main__":
    main()

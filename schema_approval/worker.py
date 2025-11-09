"""Worker entry point for the schema approval workflow."""

from __future__ import annotations

import asyncio
import logging
from typing import Sequence

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import complete_review, notify_reviewer, record_decision, upload_schema
from .workflow import SchemaApprovalWorkflow, TASK_QUEUE

logging.basicConfig(level=logging.INFO)


async def run_worker() -> None:
    client = await Client.connect("localhost:7233")
    activities: Sequence[object] = [
        upload_schema,
        notify_reviewer,
        record_decision,
        complete_review,
    ]

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[SchemaApprovalWorkflow],
        activities=list(activities),
    )
    await worker.run()


def main() -> None:
    """Console script entry point."""

    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

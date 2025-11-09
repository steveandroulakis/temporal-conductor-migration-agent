"""Worker process hosting the Schema Approval workflow."""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from . import activities
from .workflow import SchemaApprovalWorkflow, TASK_QUEUE


async def run_worker() -> None:
    """Connect to Temporal and run the worker."""

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    with open("worker.pid", "w", encoding="utf-8") as pid_file:
        pid_file.write(str(os.getpid()))

    logger.info("Connecting to Temporal service…")
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[SchemaApprovalWorkflow],
        activities=[
            activities.upload_schema,
            activities.review_primary_a,
            activities.review_primary_b,
            activities.review_secondary,
            activities.review_tertiary,
            activities.complete_review,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=5),
    ):
        logger.info("Worker started — polling task queue '%s'", TASK_QUEUE)
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Worker shutdown requested")


def main() -> None:
    """Console script entry point for the worker."""

    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

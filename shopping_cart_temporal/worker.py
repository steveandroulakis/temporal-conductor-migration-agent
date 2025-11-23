"""Worker process that hosts the workflow and activities.

This worker process:
- Connects to Temporal server
- Registers the workflow (no activities required for this workflow)
- Polls the task queue for work
- Executes workflow tasks
- Runs until interrupted (Ctrl+C)

Usage:
    After running 'uv sync', execute:
    uv run worker
"""
import asyncio
import logging
import os
import sys
from temporalio.client import Client
from temporalio.worker import Worker

# Import workflow class
from .workflow import ShoppingCartWorkflow


async def run_worker() -> None:
    """Run the Temporal worker."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Write PID file for process management
    with open("worker.pid", "w") as f:
        f.write(str(os.getpid()))

    logger.info("Worker starting...")
    logger.info(f"Process ID: {os.getpid()}")

    try:
        # Connect to Temporal server
        # Uses localhost:7233 by default
        client = await Client.connect("localhost:7233")
        logger.info("Connected to Temporal server at localhost:7233")

        # Note: This workflow has NO activities (only control flow)
        # All logic is implemented in the workflow class
        logger.info("Registering workflow: ShoppingCartWorkflow")

        # Create and run worker
        async with Worker(
            client,
            task_queue="shopping-cart-task-queue",
            workflows=[ShoppingCartWorkflow],
            activities=[],  # No activities for this workflow
        ):
            logger.info("Worker ready — polling task queue: shopping-cart-task-queue")
            logger.info("Press Ctrl+C to stop")

            # Run until interrupted
            try:
                # Keep worker running
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")

    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        raise
    finally:
        # Cleanup PID file
        if os.path.exists("worker.pid"):
            os.remove("worker.pid")
        logger.info("Worker stopped")


def main() -> None:
    """Console script entry point.

    This function is called when running 'uv run worker'.
    It must be synchronous (not async) for console script compatibility.
    """
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        # Handle graceful shutdown
        print("\nWorker stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Worker failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

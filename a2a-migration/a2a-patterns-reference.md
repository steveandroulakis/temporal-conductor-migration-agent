# A2A + Temporal: Patterns Reference

> **Part of the [A2A Project Generation Guide](./README.md)**

This document provides implementation patterns for A2A + Temporal integration with complete code examples.

---

## Core Patterns

### 1. Agent Card Definition

Every agent needs an Agent Card:

```python
# agent_card.py
from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
    AgentInterface,
)

AGENT_CARD = AgentCard(
    name="RestaurantFinderAgent",
    description="Finds restaurants based on cuisine and location preferences",
    url="http://localhost:8000",
    interfaces=[
        AgentInterface(
            url="http://localhost:8000",
            transport="JSONRPC"
        )
    ],
    capabilities=AgentCapabilities(
        streaming=True,
        pushNotifications=True
    ),
    skills=[
        AgentSkill(
            id="find_restaurant",
            name="Find Restaurant",
            description="Search for restaurants by cuisine type and location",
            inputSchema={
                "type": "object",
                "properties": {
                    "cuisine": {"type": "string", "description": "Type of cuisine"},
                    "location": {"type": "string", "description": "Location to search"},
                    "price_range": {
                        "type": "string",
                        "enum": ["$", "$$", "$$$"],
                        "description": "Price range filter"
                    }
                },
                "required": ["cuisine", "location"]
            }
        )
    ]
)
```

---

### 2. A2A Communication Activities

Activities for calling other A2A agents:

```python
# activities.py
from temporalio import activity
from a2a.client import A2AClient
from a2a.types import SendTaskRequest, Message, TextPart
import json


@activity.defn
async def send_a2a_task(agent_url: str, skill_id: str, params: dict) -> dict:
    """
    Send an A2A task to another agent.

    Args:
        agent_url: The A2A endpoint URL of the target agent
        skill_id: The skill ID to invoke
        params: Parameters for the skill

    Returns:
        The A2A task response including task ID and initial status
    """
    activity.logger.info(f"Sending A2A task to {agent_url}, skill: {skill_id}")

    async with A2AClient(agent_url) as client:
        request = SendTaskRequest(
            message=Message(
                role="user",
                parts=[TextPart(text=json.dumps(params))]
            )
        )
        response = await client.send_task(request)
        return response.model_dump()


@activity.defn
async def poll_a2a_task_status(agent_url: str, task_id: str) -> dict:
    """
    Poll the status of an A2A task.

    Args:
        agent_url: The A2A endpoint URL of the target agent
        task_id: The task ID to check

    Returns:
        The current task status and any available artifacts
    """
    activity.logger.info(f"Polling A2A task {task_id} at {agent_url}")

    async with A2AClient(agent_url) as client:
        response = await client.get_task(task_id)
        return response.model_dump()


@activity.defn
async def fetch_agent_card(agent_url: str) -> dict:
    """
    Fetch an agent's Agent Card for discovery.

    Args:
        agent_url: Base URL of the agent

    Returns:
        The Agent Card as a dictionary
    """
    import httpx

    card_url = f"{agent_url.rstrip('/')}/.well-known/agent.json"
    activity.logger.info(f"Fetching Agent Card from {card_url}")

    async with httpx.AsyncClient() as client:
        response = await client.get(card_url)
        response.raise_for_status()
        return response.json()
```

---

### 3. A2A Handoff Pattern (Durable)

When a workflow needs to call another agent:

```python
# workflow.py
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta

with workflow.unsafe.imports_passed_through():
    from myproject.activities import send_a2a_task, poll_a2a_task_status


@workflow.defn
class RestaurantFinderWorkflow:
    """Workflow that discovers restaurants and can hand off to ordering agents."""

    @workflow.run
    async def run(self, input: RestaurantQuery) -> dict:
        # ... search logic ...

        if input.place_order:
            # Hand off to restaurant's A2A agent
            order_result = await self._handoff_to_agent(
                agent_url=restaurant.agent_url,
                skill_id="place_order",
                params={
                    "items": input.order_items,
                    "customer_name": input.customer_name,
                    "delivery_address": input.delivery_address
                }
            )
            return {"status": "order_placed", "order": order_result}

        return {"status": "found", "restaurant": restaurant}

    async def _handoff_to_agent(
        self,
        agent_url: str,
        skill_id: str,
        params: dict,
        poll_interval: timedelta = timedelta(seconds=5),
        max_wait: timedelta = timedelta(minutes=10)
    ) -> dict:
        """
        Durably hand off to an external A2A agent.

        This pattern:
        1. Sends the A2A task (survives crashes)
        2. Polls for completion (survives crashes)
        3. Returns the result artifacts

        Args:
            agent_url: Target agent's A2A URL
            skill_id: The skill to invoke
            params: Parameters for the skill
            poll_interval: How often to poll for status
            max_wait: Maximum time to wait for completion

        Returns:
            The task artifacts from the completed task
        """
        # Step 1: Send the A2A task
        response = await workflow.execute_activity(
            send_a2a_task,
            args=[agent_url, skill_id, params],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        task_id = response.get("id")
        task_state = response.get("status", {}).get("state", "submitted")

        workflow.logger.info(f"A2A task {task_id} started, state: {task_state}")

        # Step 2: Durable polling loop (survives crashes)
        elapsed = timedelta(0)
        while task_state in ["submitted", "working"]:
            if elapsed >= max_wait:
                raise workflow.ApplicationError(
                    f"A2A task {task_id} timed out after {max_wait}"
                )

            await workflow.sleep(poll_interval)
            elapsed += poll_interval

            status_response = await workflow.execute_activity(
                poll_a2a_task_status,
                args=[agent_url, task_id],
                start_to_close_timeout=timedelta(seconds=30),
            )

            task_state = status_response.get("status", {}).get("state")
            workflow.logger.info(f"A2A task {task_id} state: {task_state}")

        # Step 3: Handle final state
        if task_state == "failed":
            error = status_response.get("status", {}).get("error", {})
            raise workflow.ApplicationError(
                f"A2A task failed: {error.get('message', 'Unknown error')}"
            )

        # Return artifacts from completed task
        return status_response.get("artifacts", [])
```

---

### 4. Gateway Implementation

The gateway bridges A2A to Temporal:

```python
# gateway.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from temporalio.client import Client

from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue
from a2a.types import TaskState, TaskStatus

from myproject.agent_card import AGENT_CARD
from myproject.workflow import MyWorkflow


class TemporalAgentExecutor(AgentExecutor):
    """Routes A2A tasks to Temporal workflows."""

    def __init__(self, temporal_client: Client, task_queue: str):
        self.client = temporal_client
        self.task_queue = task_queue

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue
    ) -> None:
        """Execute an A2A task by starting a Temporal workflow."""
        # Extract parameters from the A2A message
        message = context.message
        params = self._extract_params(message)

        # Start Temporal workflow
        handle = await self.client.start_workflow(
            MyWorkflow.run,
            params,
            id=f"a2a-{context.task_id}",
            task_queue=self.task_queue,
        )

        # Wait for result (in production, may want to background this)
        try:
            result = await handle.result()
            # Send completion event with result
            from a2a.types import TaskArtifactUpdateEvent, DataArtifact
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    append=False,
                    artifacts=[DataArtifact(data=result)]
                )
            )
        except Exception as e:
            # Send error event
            from a2a.types import TaskStatusUpdateEvent
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    status=TaskStatus(
                        state=TaskState.failed,
                        error={"message": str(e)}
                    )
                )
            )

    def _extract_params(self, message) -> dict:
        """Extract parameters from A2A message."""
        import json
        for part in message.parts:
            if hasattr(part, 'text'):
                return json.loads(part.text)
        return {}

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel a running task."""
        # Could cancel the Temporal workflow here
        pass


# Global state for lifespan
temporal_client: Client | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage Temporal client lifecycle."""
    global temporal_client
    temporal_client = await Client.connect("localhost:7233")
    yield
    # Cleanup if needed


def create_app() -> FastAPI:
    """Create the FastAPI application with A2A routes."""
    task_store = InMemoryTaskStore()

    # Will be initialized in lifespan
    executor = TemporalAgentExecutor(
        temporal_client=None,  # Set in first request
        task_queue="my-task-queue"
    )

    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store
    )

    a2a_app = A2AFastAPIApplication(
        agent_card=AGENT_CARD,
        http_handler=handler
    )

    app = a2a_app.build(
        title="My Agent Gateway",
        lifespan=lifespan
    )

    # Inject temporal client into executor after creation
    @app.on_event("startup")
    async def inject_client():
        executor.client = temporal_client

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
```

---

### 5. Worker Registration

Register workflows and activities:

```python
# worker.py
import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from myproject.workflow import MyWorkflow
from myproject.activities import (
    send_a2a_task,
    poll_a2a_task_status,
    my_business_activity,
)

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    """Run the Temporal worker."""
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="my-task-queue",
        workflows=[MyWorkflow],
        activities=[
            send_a2a_task,
            poll_a2a_task_status,
            my_business_activity,
        ],
    )

    logging.info("Starting worker on task queue: my-task-queue")
    await worker.run()


def main_sync() -> None:
    """Synchronous entry point for console script."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 6. Multi-Agent Orchestration

Start all components together:

```python
# run_all.py
import asyncio
import subprocess
import signal
import sys
from typing import List

AGENTS = [
    {"name": "restaurant_finder", "port": 8000, "queue": "restaurant-finder-queue"},
    {"name": "taco_shop", "port": 8001, "queue": "taco-shop-queue"},
]

processes: List[subprocess.Popen] = []


def cleanup(signum, frame):
    """Clean up all processes on shutdown."""
    print("\nShutting down all processes...")
    for p in processes:
        p.terminate()
    for p in processes:
        p.wait()
    sys.exit(0)


def main():
    """Start all workers and gateways."""
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("Starting all agents...")

    for agent in AGENTS:
        # Start worker
        worker_cmd = ["uv", "run", "python", "-m", f"{agent['name']}_agent.worker"]
        print(f"Starting worker: {' '.join(worker_cmd)}")
        p = subprocess.Popen(worker_cmd)
        processes.append(p)

        # Start gateway
        gateway_cmd = ["uv", "run", "python", "-m", f"{agent['name']}_agent.gateway"]
        print(f"Starting gateway: {' '.join(gateway_cmd)}")
        p = subprocess.Popen(gateway_cmd)
        processes.append(p)

    print(f"\nAll {len(AGENTS)} agents started!")
    print("Agent endpoints:")
    for agent in AGENTS:
        print(f"  - {agent['name']}: http://localhost:{agent['port']}")

    print("\nPress Ctrl+C to stop all agents")

    # Wait for processes
    try:
        while True:
            for p in processes:
                if p.poll() is not None:
                    print(f"Process {p.pid} exited with code {p.returncode}")
            asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
    except KeyboardInterrupt:
        cleanup(None, None)


if __name__ == "__main__":
    main()
```

---

### 7. Demo Starter

Demonstrate end-to-end flow:

```python
# starter.py
import asyncio
import httpx
import json


async def main():
    """Run demo of the multi-agent system."""
    print("=== A2A Multi-Agent Demo ===\n")

    # 1. Discover the restaurant finder agent
    print("1. Fetching Restaurant Finder Agent Card...")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/.well-known/agent.json"
        )
        agent_card = response.json()
        print(f"   Agent: {agent_card['name']}")
        print(f"   Skills: {[s['id'] for s in agent_card['skills']]}\n")

    # 2. Send a task to find a restaurant
    print("2. Sending find_restaurant task...")
    async with httpx.AsyncClient() as client:
        request = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "id": "demo-1",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "cuisine": "mexican",
                                "location": "San Francisco",
                                "price_range": "$$"
                            })
                        }
                    ]
                }
            }
        }
        response = await client.post(
            "http://localhost:8000/",
            json=request,
            timeout=60.0
        )
        result = response.json()
        print(f"   Task ID: {result.get('result', {}).get('id')}")
        print(f"   Status: {result.get('result', {}).get('status', {}).get('state')}\n")

    # 3. Poll for result
    task_id = result.get('result', {}).get('id')
    if task_id:
        print("3. Polling for result...")
        for i in range(10):
            await asyncio.sleep(2)
            async with httpx.AsyncClient() as client:
                request = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "id": f"poll-{i}",
                    "params": {"id": task_id}
                }
                response = await client.post(
                    "http://localhost:8000/",
                    json=request
                )
                status = response.json()
                state = status.get('result', {}).get('status', {}).get('state')
                print(f"   Attempt {i+1}: {state}")
                if state == "completed":
                    print("\n   Result:")
                    print(f"   {json.dumps(status.get('result', {}).get('artifacts'), indent=2)}")
                    break
                elif state == "failed":
                    print(f"   Error: {status.get('result', {}).get('status', {}).get('error')}")
                    break

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Pattern Summary

| Pattern | Use Case | Key Components |
|---------|----------|----------------|
| **Agent Card** | Discovery | `AgentCard`, `AgentSkill`, `AgentCapabilities` |
| **A2A Activities** | Cross-agent calls | `send_a2a_task`, `poll_a2a_task_status` |
| **Durable Handoff** | Reliable delegation | Activity + polling loop in workflow |
| **Gateway** | Protocol bridge | `A2AFastAPIApplication`, `AgentExecutor` |
| **Worker** | Task processing | Register workflows + activities |
| **Orchestration** | Multi-agent startup | Process management script |

---

## Related Documentation

- [A2A Architecture](./a2a-architecture.md) - Conceptual overview
- [A2A SDK Integration](./a2a-sdk-integration.md) - SDK details
- [A2A Troubleshooting](./a2a-troubleshooting.md) - Common issues

---

**[← Back to Architecture](./a2a-architecture.md)** | **[→ SDK Integration](./a2a-sdk-integration.md)**

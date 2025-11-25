# A2A SDK Integration Guide

> **Part of the [A2A Project Generation Guide](./README.md)**

This document covers how to use the `a2a-sdk` Python package with Temporal for building robust A2A agents.

---

## SDK Overview

The `a2a-sdk` package provides:

| Module | Purpose |
|--------|---------|
| `a2a.types` | Pydantic models for A2A protocol (AgentCard, Task, etc.) |
| `a2a.client` | Client for calling A2A agents |
| `a2a.server` | Server components for building A2A agents |
| `a2a.server.apps.jsonrpc` | FastAPI/Starlette integration |

---

## Installation

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "temporalio>=1.5.0",
    "a2a-sdk[http-server]>=0.1.0",  # Includes FastAPI
    "httpx>=0.26.0",
]
```

Install:
```bash
uv sync
```

---

## Core Types

### AgentCard

Describes an agent's capabilities:

```python
from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
    AgentInterface,
    AgentProvider,
)

AGENT_CARD = AgentCard(
    # Required fields
    name="MyAgent",
    description="What this agent does",
    url="http://localhost:8000",

    # Interfaces (transport options)
    interfaces=[
        AgentInterface(
            url="http://localhost:8000",
            transport="JSONRPC"
        ),
        # Can add gRPC, REST interfaces too
    ],

    # Capabilities
    capabilities=AgentCapabilities(
        streaming=True,           # Supports streaming responses
        pushNotifications=True,   # Supports push notifications
    ),

    # Skills
    skills=[
        AgentSkill(
            id="my_skill",
            name="My Skill",
            description="What this skill does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                },
                "required": ["param1"]
            },
            examples=["Example prompt 1", "Example prompt 2"]
        )
    ],

    # Optional: Provider info
    provider=AgentProvider(
        organization="My Company",
        url="https://mycompany.com"
    ),
)
```

### Task Types

A2A task lifecycle:

```python
from a2a.types import Task, TaskState, TaskStatus

# Task states
TaskState.submitted   # Task received, not started
TaskState.working     # Task in progress
TaskState.completed   # Task finished successfully
TaskState.failed      # Task failed
TaskState.canceled    # Task was canceled

# Task structure
task = Task(
    id="task-123",
    status=TaskStatus(
        state=TaskState.working,
        progress=0.5,  # Optional progress indicator
    ),
    artifacts=[...],  # Results when completed
)
```

### Message Types

A2A messages:

```python
from a2a.types import Message, TextPart, DataPart, FilePart

# Text message
message = Message(
    role="user",  # or "agent"
    parts=[
        TextPart(text="Find me a restaurant"),
    ]
)

# Data message
message = Message(
    role="user",
    parts=[
        DataPart(data={"cuisine": "mexican", "location": "SF"})
    ]
)
```

---

## Client Usage

### Basic Client

```python
from a2a.client import A2AClient

async def call_agent():
    async with A2AClient("http://localhost:8000") as client:
        # Send a task
        response = await client.send_task(
            message=Message(
                role="user",
                parts=[TextPart(text="Hello")]
            )
        )

        task_id = response.id
        print(f"Task started: {task_id}")

        # Poll for result
        while True:
            status = await client.get_task(task_id)
            if status.status.state == TaskState.completed:
                return status.artifacts
            elif status.status.state == TaskState.failed:
                raise Exception(status.status.error)
            await asyncio.sleep(1)
```

### With Temporal Activities

Wrap client calls in activities for durability:

```python
from temporalio import activity
from a2a.client import A2AClient
from a2a.types import Message, TextPart
import json


@activity.defn
async def send_a2a_task(agent_url: str, skill_id: str, params: dict) -> dict:
    """
    Send A2A task as a Temporal activity.

    This ensures the call is retried on failure and the result
    is durably stored.
    """
    async with A2AClient(agent_url) as client:
        response = await client.send_task(
            message=Message(
                role="user",
                parts=[TextPart(text=json.dumps(params))]
            ),
            skill=skill_id
        )
        return response.model_dump()
```

---

## Server Components

### A2AFastAPIApplication

The main entry point for building A2A servers:

```python
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

# Create task store
task_store = InMemoryTaskStore()

# Create request handler
handler = DefaultRequestHandler(
    agent_executor=my_executor,
    task_store=task_store,
)

# Create A2A application
a2a_app = A2AFastAPIApplication(
    agent_card=AGENT_CARD,
    http_handler=handler,
)

# Build FastAPI app
app = a2a_app.build(
    title="My Agent",
    description="My agent description",
)
```

### AgentExecutor

Implement to handle A2A tasks:

```python
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue
from a2a.types import TaskArtifactUpdateEvent, DataArtifact


class MyExecutor(AgentExecutor):
    """Custom executor that routes to Temporal."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue
    ) -> None:
        """Handle incoming A2A task."""
        # Get task info
        task_id = context.task_id
        message = context.message

        # Do work (e.g., start Temporal workflow)
        result = await self.do_work(message)

        # Send result via event queue
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                artifacts=[DataArtifact(data=result)]
            )
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue
    ) -> None:
        """Handle task cancellation."""
        # Cancel any running work
        pass
```

### Task Store

Store task state:

```python
from a2a.server.tasks import InMemoryTaskStore

# In-memory (for development)
task_store = InMemoryTaskStore()

# For production, implement TaskStore interface
# with database backing
```

---

## Temporal Integration Pattern

### Complete Gateway Example

```python
# gateway.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from fastapi import FastAPI
from temporalio.client import Client

from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    DataArtifact,
    TaskStatus,
    TaskState,
)

from myagent.agent_card import AGENT_CARD
from myagent.workflow import MyWorkflow

logger = logging.getLogger(__name__)


class TemporalAgentExecutor(AgentExecutor):
    """Executor that routes A2A tasks to Temporal workflows."""

    def __init__(self, task_queue: str):
        self.task_queue = task_queue
        self.client: Client | None = None

    def set_client(self, client: Client) -> None:
        """Set the Temporal client after initialization."""
        self.client = client

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue
    ) -> None:
        if not self.client:
            raise RuntimeError("Temporal client not initialized")

        try:
            # Extract parameters from message
            params = self._parse_message(context.message)

            # Start Temporal workflow
            handle = await self.client.start_workflow(
                MyWorkflow.run,
                params,
                id=f"a2a-{context.task_id}",
                task_queue=self.task_queue,
            )

            logger.info(f"Started workflow {handle.id} for task {context.task_id}")

            # Wait for result
            result = await handle.result()

            # Send completion
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    append=False,
                    artifacts=[DataArtifact(data=result)]
                )
            )

        except Exception as e:
            logger.error(f"Task {context.task_id} failed: {e}")
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    status=TaskStatus(
                        state=TaskState.failed,
                        error={"message": str(e)}
                    )
                )
            )

    def _parse_message(self, message) -> dict:
        """Extract parameters from A2A message."""
        import json
        for part in message.parts:
            if hasattr(part, 'text'):
                return json.loads(part.text)
            if hasattr(part, 'data'):
                return part.data
        return {}

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue
    ) -> None:
        """Cancel a running workflow."""
        if self.client:
            try:
                handle = self.client.get_workflow_handle(f"a2a-{context.task_id}")
                await handle.cancel()
            except Exception as e:
                logger.warning(f"Failed to cancel workflow: {e}")


# Create executor (client set later)
executor = TemporalAgentExecutor(task_queue="my-queue")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage Temporal client lifecycle."""
    client = await Client.connect("localhost:7233")
    executor.set_client(client)
    logger.info("Connected to Temporal")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    task_store = InMemoryTaskStore()

    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
    )

    a2a_app = A2AFastAPIApplication(
        agent_card=AGENT_CARD,
        http_handler=handler,
    )

    return a2a_app.build(
        title=AGENT_CARD.name,
        description=AGENT_CARD.description,
        lifespan=lifespan,
    )


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Best Practices

### 1. Use Type Hints

The SDK uses Pydantic v2 - leverage type safety:

```python
from a2a.types import AgentCard, Task

def process_card(card: AgentCard) -> list[str]:
    return [skill.id for skill in card.skills]
```

### 2. Handle Errors Gracefully

```python
async def execute(self, context, event_queue):
    try:
        result = await self.do_work()
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(artifacts=[DataArtifact(data=result)])
        )
    except ValidationError as e:
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                status=TaskStatus(state=TaskState.failed, error={"message": str(e)})
            )
        )
```

### 3. Use Async Context Managers

```python
async with A2AClient(url) as client:
    # Client is properly initialized and cleaned up
    response = await client.send_task(...)
```

### 4. Log Appropriately

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Processing task {context.task_id}")
logger.error(f"Task failed: {error}", exc_info=True)
```

---

## Related Documentation

- [A2A Patterns Reference](./a2a-patterns-reference.md) - Implementation patterns
- [A2A Troubleshooting](./a2a-troubleshooting.md) - Common issues
- [A2A Python SDK Source](../tmp-resources/a2a-python/) - SDK source code

---

**[← Back to Patterns](./a2a-patterns-reference.md)** | **[→ Troubleshooting](./a2a-troubleshooting.md)**

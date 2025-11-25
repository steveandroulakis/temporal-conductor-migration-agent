# A2A + Temporal: Architecture Reference

> **Part of the [A2A Project Generation Guide](./README.md)**

This document explains how A2A (Agent-to-Agent) protocol and Temporal work together to create robust, interoperable multi-agent systems.

---

## The Two Layers

### A2A: The Interoperability Layer

A2A provides a standard protocol for agents to discover and communicate with each other:

| Component | Purpose |
|-----------|---------|
| **Agent Card** | JSON manifest at `/.well-known/agent.json` describing capabilities |
| **Skills** | Discrete functions an agent can perform |
| **Tasks** | Units of work with lifecycle states |
| **JSON-RPC 2.0** | Transport protocol for requests/responses |

### Temporal: The Durability Layer

Temporal provides execution guarantees underneath each agent:

| Component | Purpose |
|-----------|---------|
| **Workflows** | Orchestrate operations, maintain state |
| **Activities** | Execute business logic with retries |
| **Workers** | Process workflow and activity tasks |
| **Event Sourcing** | Full history, automatic recovery |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         External Client                              │
│                    (Another A2A Agent or App)                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ 1. Fetch Agent Card
                                │ 2. Send A2A Task (JSON-RPC)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      A2A Gateway (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ GET /.well-known/agent.json  →  Return AgentCard            │   │
│  │ POST /                        →  Route to Temporal Workflow  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ 3. Start Temporal Workflow
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Temporal Server                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Workflow Execution (Event Sourced)                          │   │
│  │ - Durable state                                              │   │
│  │ - Automatic retries                                          │   │
│  │ - Crash recovery                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ 4. Execute Activities
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Temporal Worker                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Activities:                                                  │   │
│  │ - Business logic (DB, APIs)                                  │   │
│  │ - A2A calls to other agents                                  │   │
│  │ - HTTP requests                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Mapping

### Agent Card → A2A Discovery

Each agent publishes an Agent Card describing its capabilities:

```python
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentInterface

AGENT_CARD = AgentCard(
    name="RestaurantFinderAgent",
    description="Finds restaurants based on cuisine preferences",
    url="http://localhost:8000",
    interfaces=[
        AgentInterface(url="http://localhost:8000", transport="JSONRPC")
    ],
    capabilities=AgentCapabilities(
        streaming=True,
        pushNotifications=True
    ),
    skills=[
        AgentSkill(
            id="find_restaurant",
            name="Find Restaurant",
            description="Search for restaurants by cuisine type",
            inputSchema={
                "type": "object",
                "properties": {
                    "cuisine": {"type": "string"},
                    "location": {"type": "string"}
                }
            }
        )
    ]
)
```

### Skill → Temporal Workflow

Each A2A skill maps to a Temporal workflow:

| A2A Skill | Temporal Workflow |
|-----------|-------------------|
| `find_restaurant` | `RestaurantFinderWorkflow` |
| `place_order` | `TacoOrderWorkflow` |

The gateway routes skill invocations to workflow starts:

```python
SKILL_TO_WORKFLOW = {
    "find_restaurant": RestaurantFinderWorkflow,
    "place_order": TacoOrderWorkflow,
}
```

### A2A Task → Workflow Execution

| A2A Task State | Temporal Workflow State |
|----------------|------------------------|
| `submitted` | Workflow started, not yet running |
| `working` | Workflow executing |
| `completed` | Workflow completed successfully |
| `failed` | Workflow failed or terminated |

---

## Cross-Agent Communication

When Agent A needs to call Agent B:

```
Agent A Workflow
     │
     │ 1. Execute activity: send_a2a_task
     ▼
Agent A Activity (send_a2a_task)
     │
     │ 2. HTTP POST to Agent B's gateway
     ▼
Agent B Gateway
     │
     │ 3. Start Agent B's workflow
     ▼
Agent B Workflow
     │
     │ 4. Execute activities, return result
     ▼
Agent A Activity (poll_a2a_task)
     │
     │ 5. Poll until completed
     ▼
Agent A Workflow (continues)
```

### Why This Pattern?

1. **A2A calls are activities**: HTTP calls happen in activities, not workflows (sandbox compliance)
2. **Polling is durable**: The polling loop is in the workflow, survives crashes
3. **Each call is retryable**: Activity retries handle transient failures

---

## Key Differences from Single-Agent Systems

| Aspect | Single Agent | Multi-Agent A2A |
|--------|--------------|-----------------|
| **Communication** | Direct workflow calls | A2A protocol over HTTP |
| **Discovery** | N/A | Agent Cards |
| **Organization** | Single package | Package per agent |
| **Ports** | Single port | Unique port per agent |
| **Task Queues** | Single queue | Queue per agent |
| **Workers** | Single worker | Worker per agent |

---

## Gateway Architecture

The A2A Gateway bridges A2A protocol to Temporal:

```python
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor

class TemporalAgentExecutor(AgentExecutor):
    """Routes A2A tasks to Temporal workflows."""

    def __init__(self, temporal_client: Client, task_queue: str):
        self.client = temporal_client
        self.task_queue = task_queue
        self.skill_to_workflow = {...}

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        skill_id = context.get_user_input()  # Extract skill from request
        workflow_class = self.skill_to_workflow.get(skill_id)

        # Start Temporal workflow
        handle = await self.client.start_workflow(
            workflow_class.run,
            context.params,
            id=f"a2a-{context.task_id}",
            task_queue=self.task_queue,
        )

        # Wait for result
        result = await handle.result()

        # Send completion event
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                artifacts=[DataArtifact(data=result)]
            )
        )
```

---

## Multi-Agent Project Structure

```
restaurant_system/
├── pyproject.toml
├── shared/
│   ├── __init__.py
│   └── types.py                 # Shared dataclasses
├── restaurant_finder_agent/
│   ├── __init__.py
│   ├── agent_card.py            # AgentCard definition
│   ├── activities.py            # search_restaurants, send_a2a_task, etc.
│   ├── workflow.py              # RestaurantFinderWorkflow
│   ├── gateway.py               # A2AFastAPIApplication on port 8000
│   └── worker.py                # Worker on restaurant-finder-queue
├── taco_shop_agent/
│   ├── __init__.py
│   ├── agent_card.py            # AgentCard definition
│   ├── activities.py            # validate_order, submit_to_kitchen, etc.
│   ├── workflow.py              # TacoOrderWorkflow
│   ├── gateway.py               # A2AFastAPIApplication on port 8001
│   └── worker.py                # Worker on taco-shop-queue
├── run_all.py                   # Start all workers + gateways
└── starter.py                   # Demo end-to-end flow
```

---

## Value Proposition

### A2A Provides

- **Interoperability**: Standard protocol for agent communication
- **Discovery**: Agent Cards for capability advertisement
- **Flexibility**: Agents can be different frameworks, different orgs

### Temporal Provides

- **Durability**: Workflows survive crashes, resume exactly
- **Reliability**: Automatic retries, timeouts, error handling
- **Observability**: Full execution history, debugging

### Together

- **Robust Multi-Agent Systems**: Durable execution + standard protocol
- **Cross-Organization**: Different Temporal clusters, same A2A interface
- **Production Ready**: Enterprise-grade reliability

---

## Related Documentation

- [A2A Patterns Reference](./a2a-patterns-reference.md) - Implementation patterns
- [A2A SDK Integration](./a2a-sdk-integration.md) - Using the SDK
- [A2A Troubleshooting](./a2a-troubleshooting.md) - Common issues

---

**[← Back to Main Guide](./README.md)** | **[→ Patterns Reference](./a2a-patterns-reference.md)**

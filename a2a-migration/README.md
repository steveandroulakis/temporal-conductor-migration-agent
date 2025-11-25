# A2A + Temporal Project Generation Guide

> **Comprehensive documentation for generating Temporal-powered A2A (Agent-to-Agent) projects from natural language specifications**

---

## What This System Does

Given a natural language specification with embedded code examples (like `a2a-temporal-example-spec.md`), this system generates a complete multi-agent Temporal Python project with:

- **Agent Cards** for A2A discovery (`.well-known/agent.json`)
- **Temporal Workflows** for durable execution
- **Activities** for business logic and A2A communication
- **FastAPI Gateways** bridging A2A protocol to Temporal
- **Workers** for each agent
- **Comprehensive documentation**

---

## Quick Start

### Prerequisites

Before using this system:

1. **Understand A2A Protocol**: Read [A2A Architecture](./a2a-architecture.md) for conceptual understanding
2. **Understand Patterns**: Read [A2A Patterns Reference](./a2a-patterns-reference.md) for implementation patterns
3. **Have spec ready**: Prepare a specification file describing your multi-agent system

### Running the Generator

```bash
# Invoke the generation pipeline
/generate-a2a path/to/your-spec.md
```

### What You Get

A complete project structure:
```
{project_name}/
├── pyproject.toml              # Package config with a2a-sdk, temporalio
├── shared/
│   ├── __init__.py
│   └── types.py                # Shared dataclasses
├── {agent1}_agent/
│   ├── __init__.py
│   ├── agent_card.py           # A2A Agent Card configuration
│   ├── activities.py           # Business + A2A activities
│   ├── workflow.py             # Temporal workflow
│   ├── gateway.py              # FastAPI A2A gateway
│   └── worker.py               # Temporal worker
├── {agent2}_agent/
│   └── ...
├── run_all.py                  # Orchestration script
├── starter.py                  # Demo starter
├── setup.sh                    # Automated setup
├── README.md                   # Project documentation
└── SYSTEM_ARCHITECTURE.md      # Architecture overview
```

---

## Documentation Structure

| Document | Purpose | Read First? |
|----------|---------|-------------|
| **[A2A Architecture](./a2a-architecture.md)** | Conceptual overview of A2A + Temporal | Yes |
| **[A2A Patterns Reference](./a2a-patterns-reference.md)** | Implementation patterns and examples | Yes |
| **[A2A SDK Integration](./a2a-sdk-integration.md)** | Using a2a-sdk with Temporal | Reference |
| **[A2A Quality Assurance](./a2a-quality-assurance.md)** | Validation and testing | Reference |
| **[A2A Troubleshooting](./a2a-troubleshooting.md)** | Common issues and solutions | Reference |

---

## Key Concepts

### A2A Protocol

The [A2A (Agent-to-Agent) protocol](https://github.com/a2aproject/A2A) enables interoperability between AI agents:

- **Agent Cards**: JSON manifests describing agent capabilities
- **Skills**: Discrete capabilities an agent can perform
- **Tasks**: Units of work with lifecycle (submitted → working → completed)
- **JSON-RPC 2.0**: Transport protocol for task requests

### Temporal Integration

Temporal provides durable execution guarantees underneath each agent:

- **Workflows**: Orchestrate complex, long-running operations
- **Activities**: Execute business logic with automatic retries
- **Durability**: Survive crashes, resume exactly where left off
- **Observability**: Full visibility into execution state

### The Bridge

The A2A Gateway (`gateway.py`) bridges these two:

```
A2A Client → JSON-RPC Request → Gateway → Temporal Workflow → Durable Execution
```

---

## Input Specification Format

The generator accepts natural language specifications with embedded code. Example structure:

```markdown
# System Name

## Overview
Description of what the system does and how agents interact.

## Architecture
ASCII diagram or description of agent interactions.

## Agents

### Agent 1: AgentName
- **Purpose**: What this agent does
- **Skills**:
  - skill_id: Description
- **Workflows**: Business logic description
- **Activities**: What activities it performs

### Agent 2: AnotherAgent
...

## Data Types
```python
@dataclass
class SomeInput:
    field: str
```

## Example Flow
Step-by-step description of how agents interact.
```

See `a2a-temporal-example-spec.md` for a complete example.

---

## Critical Requirements

### Before Generating

1. **Read the Patterns Reference**: Understand A2A handoff patterns, durable polling
2. **Understand the SDK**: Know `AgentCard`, `A2AFastAPIApplication`, `A2AClient`
3. **Plan Port Allocation**: Each agent needs a unique port

### After Generating

1. **Implement Business Logic**: Replace TODO placeholders in activities
2. **Configure Timeouts**: Adjust based on actual requirements
3. **Add Authentication**: Production systems need auth configuration
4. **Write Tests**: Add unit and integration tests

---

## Success Criteria

A successfully generated project should:

- [ ] All Python files pass syntax validation
- [ ] `mypy --strict` passes with zero errors
- [ ] Agent cards are valid A2A SDK types
- [ ] Gateways start and serve agent cards
- [ ] Workers connect to Temporal
- [ ] Cross-agent communication works end-to-end

---

## Next Steps After Generation

1. **Run setup**: `./setup.sh`
2. **Start Temporal**: `temporal server start-dev`
3. **Start all components**: `uv run python run_all.py`
4. **Run demo**: `uv run python starter.py`
5. **Verify agent cards**: `curl http://localhost:8000/.well-known/agent.json`

---

## Related Documentation

- [Agent Development Guide (AGENTS.md)](../AGENTS.md) - Python development standards
- [Sub-Agent Architecture](../SUBAGENT_ARCHITECTURE.md) - Pipeline architecture
- [A2A Python SDK](../tmp-resources/a2a-python/) - SDK source reference

---

**[→ Start with A2A Architecture](./a2a-architecture.md)**

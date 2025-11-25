# A2A + Temporal Multi-Agent System Generator

**Automatically generate complete A2A (Agent-to-Agent) protocol compatible multi-agent systems powered by Temporal workflows from natural language specifications using Claude Code.**

## What This Does

Given a natural language specification, this Claude Code-powered system:
1. Analyzes the specification to identify agents, skills, and inter-agent communication patterns
2. Generates a complete, production-ready multi-agent Temporal Python project with:
   - Per-agent packages with type-safe code
   - A2A Agent Cards for discovery (using a2a-sdk)
   - FastAPI gateways implementing A2A protocol
   - Temporal workflows and activities for each agent
   - Inter-agent communication via A2A activities
   - System orchestrator for managing all components
3. Validates all generated code across all agents
4. Executes the entire system to verify it works
5. Produces comprehensive documentation

## Quick Start

### Prerequisites
- [Claude Code](https://claude.ai/claude-code)
- Python 3.11+
- [UV package manager](https://github.com/astral-sh/uv)
- [Temporal CLI](https://temporal.io/download)

### Usage

In Claude Code, execute:
```
/generate-a2a path/to/specification.md [optional context]
```

**Example:**
```
/generate-a2a a2a-temporal-example-spec.md This is a food ordering system. Use mock data for restaurant APIs.
```

The pipeline will automatically:
- Analyze your specification
- Generate a complete multi-agent A2A project
- Use your provided context to guide implementations
- Validate and fix any issues
- Create comprehensive documentation

### After Generation

Your generated project will include:
```
{project_name}/
├── shared/
│   └── types.py
├── {agent1}_agent/
│   ├── agent_card.py
│   ├── activities.py
│   ├── workflow.py
│   ├── worker.py
│   └── gateway.py
├── {agent2}_agent/
│   └── ...
├── orchestrator.py
├── pyproject.toml
├── setup.sh
├── README.md
├── A2A_INTEGRATION.md
├── VALIDATION_REPORT.md
└── SYSTEM_EXECUTION_REPORT.md
```

### Running the System

```bash
# Setup
./setup.sh

# Start Temporal
temporal server start-dev

# Start all components
uv run orchestrator start

# Verify
curl http://localhost:8000/.well-known/agent.json
```

## Architecture

See [CLAUDE.md](./CLAUDE.md) for complete pipeline architecture and agent specifications.

- `a2a-migration/` - Comprehensive A2A migration guides
- `claude/` - Subagents and generation command

## The A2A Value Proposition

A2A (Agent-to-Agent) protocol enables:
- **Discovery**: Agents expose capabilities via Agent Cards
- **Interoperability**: Standard JSON-RPC 2.0 communication
- **Cross-boundary communication**: Connect different Temporal systems via HTTP

### The Coordinator-Services Pattern

This generator excels at creating systems where:
- A **COORDINATOR** agent queries multiple **SERVICE** agents in parallel
- Each agent has its own Temporal workflow for durability
- A2A protocol handles inter-system communication

```
┌─────────────────────────────────────────────────────────────────┐
│                    PersonalAssistant                            │
│                   (COORDINATOR Agent)                           │
│                   Temporal Namespace A                          │
└─────────────────────────────────────────────────────────────────┘
         │ A2A Protocol (HTTP)          │ A2A Protocol (HTTP)
         ▼                              ▼
┌─────────────────────┐     ┌─────────────────────┐
│     BurgerBot       │     │     TacoTime        │
│  (SERVICE Agent)    │     │  (SERVICE Agent)    │
│  Temporal NS B      │     │  Temporal NS C      │
└─────────────────────┘     └─────────────────────┘
```

---

**Generated projects are production-ready with type safety, error handling, and comprehensive documentation.**

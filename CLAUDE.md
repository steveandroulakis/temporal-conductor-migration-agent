# A2A + Temporal Multi-Agent System Generator

## Project Purpose

This project is a **Claude Code-powered generation system** that automatically creates complete A2A (Agent-to-Agent) protocol compatible multi-agent systems powered by Temporal workflows from natural language specifications.

### What It Does

Given a natural language specification with embedded code examples, this system:
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
5. Produces comprehensive documentation for using and extending the system

### Why This Exists

Building A2A-compatible multi-agent systems requires:
- Understanding the A2A protocol (JSON-RPC 2.0, Agent Cards, task lifecycle)
- Implementing proper Temporal patterns (workflows, activities, sandbox compliance)
- Setting up FastAPI gateways correctly
- Managing inter-agent communication
- Coordinating multiple workers and gateways

This project automates this complex setup using Claude Code's sub-agent architecture.

---

## Architecture: 11-Agent Sequential Pipeline

The generation system uses a **sequential pipeline** of 11 specialized Claude Code sub-agents. Each agent operates with high autonomy, generating a specific part of the multi-agent system.

### Pipeline Overview

```
User provides Specification (natural language + code)
         ↓
┌────────────────────────────────────────────────────────────────┐
│                    Main Claude Code Agent                      │
│              (Orchestrates pipeline execution)                 │
└────────────────────────────────────────────────────────────────┘
         ↓
    Sequential Pipeline Execution
         ↓
1. Spec Analyzer
   └─> a2a-generation/a2a-analysis.json
         ↓
2. Project Scaffolder
   └─> Multi-agent package structure, shared/types.py
         ↓
3. Agent Card Generator
   └─> {agent}_agent/agent_card.py for each agent
         ↓
4. Activity Generator
   └─> {agent}_agent/activities.py for each agent
         ↓
5. Workflow Generator (MOST COMPLEX)
   └─> {agent}_agent/workflow.py for each agent
         ↓
6. Gateway Generator
   └─> {agent}_agent/gateway.py for each agent
         ↓
7. Infrastructure Generator
   └─> {agent}_agent/worker.py, orchestrator.py
         ↓
8. Code Validator
   └─> Validates & fixes → a2a-generation/VALIDATION_REPORT.md
         ↓
9. System Executor
   └─> Runs all components → a2a-generation/SYSTEM_EXECUTION_REPORT.md
         ↓
10. Streamlit Generator
    └─> streamlit_app.py (human-in-the-loop UI)
         ↓
11. Documentation Generator
    └─> README.md, A2A_INTEGRATION.md, setup.sh
         ↓
    Complete A2A Multi-Agent System
```

---

## Agent Specifications

### 1. Spec Analyzer
**Role**: First agent - parses natural language specification

**Responsibilities**:
- Parse specification file (markdown with embedded code)
- Extract system overview (name, description, purpose)
- Identify all agents and their details
- Parse skills for each agent with input schemas
- Extract workflow logic and activities from prose and code
- Map inter-agent communication patterns
- Assign unique ports and task queues
- Generate structured `a2a-generation/a2a-analysis.json`

**Key Output**: `a2a-generation/a2a-analysis.json` - comprehensive analysis for all downstream agents

---

### 2. Project Scaffolder
**Role**: Creates multi-agent Python project structure

**Responsibilities**:
- Create multi-agent directory structure (`{agent}_agent/` packages)
- Generate `shared/types.py` with dataclasses
- Generate `pyproject.toml` with:
  - Dependencies (temporalio, httpx, a2a-sdk, fastapi, uvicorn)
  - Console scripts for each agent's worker and gateway
  - **CRITICAL**: `[tool.uv]` section with `package = true`
- Create placeholder files for downstream agents

**Key Output**: Complete project structure with all packages

---

### 3. Agent Card Generator
**Role**: Generates A2A Agent Card configurations

**Responsibilities**:
- For EACH agent, generate `agent_card.py`
- Use a2a-sdk types: `AgentCard`, `AgentSkill`, `AgentCapabilities`
- Create proper JSON Schema `inputSchema` for skills
- Ensure URLs match assigned ports

**Key Output**: `{agent}_agent/agent_card.py` for each agent

---

### 4. Activity Generator
**Role**: Generates Temporal activities for each agent

**Responsibilities**:
- For EACH agent, generate `activities.py`
- Create business logic activities based on skills
- Generate `send_a2a_task` activity for inter-agent communication
- Use `httpx.AsyncClient()` for A2A protocol calls
- Complete type hints and docstrings

**Key Output**: `{agent}_agent/activities.py` for each agent

---

### 5. Workflow Generator (MOST COMPLEX)
**Role**: Generates Temporal workflows with A2A patterns

**Responsibilities**:
- For EACH agent, generate `workflow.py`
- Create `@workflow.defn` class
- Map skills to workflow entry points
- Implement A2A handoff patterns via activities
- **CRITICAL**: Ensure workflow sandbox compliance (passthrough imports)
- Configure activity execution with proper timeouts
- Add query handlers for status

**Key Output**: `{agent}_agent/workflow.py` for each agent

**Model**: Sonnet (explicitly specified for complexity)

---

### 6. Gateway Generator
**Role**: Generates FastAPI A2A gateways

**Responsibilities**:
- For EACH agent, generate `gateway.py`
- Use `A2AFastAPIApplication` from a2a-sdk
- Implement `AgentExecutor` to route A2A tasks to Temporal
- Configure `DefaultRequestHandler` with task store
- Handle Temporal client lifecycle with FastAPI lifespan
- Include uvicorn runner

**Key Output**: `{agent}_agent/gateway.py` for each agent

---

### 7. Infrastructure Generator
**Role**: Generates workers and system orchestrator

**Responsibilities**:
- For EACH agent, generate `worker.py` with:
  - Workflow and activity registration
  - **CRITICAL**: Synchronous `main()` for console scripts
- Generate `orchestrator.py` with:
  - Start/stop all workers and gateways
  - Health checks
  - Status display

**Key Output**: `{agent}_agent/worker.py` for each agent, `orchestrator.py`

---

### 8. Code Validator
**Role**: Validates all code and fixes issues

**Responsibilities**:
- Validate syntax across ALL agent packages
- Run type checking with `mypy --strict`
- Verify workflow sandbox compliance
- Check A2A-specific configurations
- Verify port and task queue consistency
- **Autonomously fix issues**
- Generate `a2a-generation/VALIDATION_REPORT.md`

**Key Output**: `a2a-generation/VALIDATION_REPORT.md` with validation results and fixes

---

### 9. System Executor
**Role**: Executes and validates entire system

**Responsibilities**:
- Start Temporal server if needed
- Install dependencies
- Start ALL workers and gateways
- Verify agent cards are accessible
- Test A2A protocol for each agent
- Test inter-agent communication
- Cleanup all processes
- Generate `a2a-generation/SYSTEM_EXECUTION_REPORT.md`

**Key Output**: `a2a-generation/SYSTEM_EXECUTION_REPORT.md` with execution results

---

### 10. Streamlit Generator
**Role**: Generates human-in-the-loop UI for coordinator workflow

**Responsibilities**:
- Read `coordinator_interaction` from `a2a-generation/a2a-analysis.json`
- Generate `streamlit_app.py` with:
  - Form for workflow input (from `workflow_input` schema)
  - Signal buttons for human decisions (from `signals`)
  - Query result display (from `queries`)
  - Real-time status updates
- Use cached Temporal client via `@st.cache_resource`
- Handle session state for workflow_id persistence
- Add streamlit dependency to `pyproject.toml`
- **Validate the app runs correctly**:
  - Syntax validation (`py_compile`)
  - Import validation (no ImportError)
  - Runtime validation (start Streamlit headless, curl HTTP 200)
- **Autonomously fix issues** if validation fails

**Key Output**: `streamlit_app.py` - validated, working interactive UI

---

### 11. Documentation Generator
**Role**: Final agent - creates comprehensive documentation

**Responsibilities**:
- Generate main `README.md` with:
  - ASCII architecture diagram
  - Per-agent documentation
  - Quick start instructions
  - A2A protocol examples
  - Troubleshooting
- Generate `A2A_INTEGRATION.md` with:
  - Agent card examples
  - Task lifecycle documentation
  - Python client example
- Generate `setup.sh` script
- Generate per-agent `README.md` files

**Key Output**: Complete documentation suite

---

## Communication Protocol

### Structured Document: a2a-generation/a2a-analysis.json

All agents communicate through `a2a-generation/a2a-analysis.json`:

```json
{
  "analysis_date": "ISO 8601 timestamp",
  "spec_source": "path to specification",
  "system_metadata": {
    "name": "System Name",
    "description": "What the system does",
    "total_agents": 2
  },
  "project_config": {
    "project_name": "SystemName",
    "project_name_snake": "system_name",
    "base_port": 8000
  },
  "agents": [
    {
      "agent_id": "agent_identifier",
      "name": "AgentDisplayName",
      "port": 8000,
      "task_queue": "agent-queue",
      "package_name": "agent_agent",
      "skills": [...],
      "workflows": [...],
      "activities": [...],
      "calls_agents": ["other_agent_id"]
    }
  ],
  "shared_types": [...],
  "inter_agent_communication": [...]
}
```

---

## Critical Pitfalls & Solutions

### Workflow Sandbox Violations
**Problem**: Importing activity modules with non-deterministic code (httpx)
**Solution**: Use passthrough imports: `with workflow.unsafe.imports_passed_through():`

### Wrong RetryPolicy Import
**Problem**: Importing from `temporalio.workflow` instead of `temporalio.common`
**Solution**: Always use `from temporalio.common import RetryPolicy`

### Console Script Async Main
**Problem**: `async def main()` causes "coroutine was never awaited"
**Solution**: Create synchronous `main()` that calls `asyncio.run()`

### Missing [tool.uv] Configuration
**Problem**: Console scripts not found
**Solution**: Include `[tool.uv] package = true` in pyproject.toml

### A2A SDK Import Errors
**Problem**: Wrong import paths for a2a-sdk types
**Solution**: Import from `a2a.types` and `a2a.server.*`

---

## Usage

### Command

```
/generate-a2a path/to/specification.md [optional context]
```

### Example

```
/generate-a2a a2a-temporal-example-spec.md This is a restaurant booking system with mock data.
```

### What Users Get

A complete A2A multi-agent system with separate generation artifacts:
```
a2a-generation/               # Pipeline artifacts (meta information)
├── a2a-analysis.json         # Analysis driving generation
├── VALIDATION_REPORT.md      # Validation step report
└── SYSTEM_EXECUTION_REPORT.md # Execution test report

{project_name}/               # Clean deliverable project
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
├── streamlit_app.py          # Human-in-the-loop UI
├── pyproject.toml
├── setup.sh
├── README.md
└── A2A_INTEGRATION.md
```

### Running the System

```bash
# Setup
./setup.sh

# Start Temporal
temporal server start-dev

# Start all components
uv run orchestrator start

# Or individually:
uv run {agent}_worker
uv run {agent}_gateway

# Verify
curl http://localhost:8000/.well-known/agent.json

# Launch Human-in-the-Loop UI
streamlit run streamlit_app.py
```

---

## Technical Details

### Dependencies

Generated projects use:
- **Python 3.11+**
- **temporalio**: Temporal Python SDK (≥1.5.0)
- **httpx**: Async HTTP client
- **a2a-sdk**: A2A protocol types and server
- **fastapi**: Web framework for gateways
- **uvicorn**: ASGI server
- **mypy**: Type checking (≥1.7.0)
- **uv**: Fast Python package manager

### A2A Protocol Integration

Each agent exposes:
- `/.well-known/agent.json` - Agent Card for discovery
- `/` - JSON-RPC 2.0 endpoint for tasks/send, tasks/get

### Inter-Agent Communication

Agents call other agents via the `send_a2a_task` activity:
```python
request = A2ATaskRequest(
    target_agent_url="http://localhost:8001",
    skill_id="process_order",
    parameters={"order_id": "123"}
)
response = await workflow.execute_activity(
    send_a2a_task,
    request,
    start_to_close_timeout=timedelta(minutes=5),
)
```

---

## Documentation Reference

All agents have access to:
- `a2a-migration/README.md` - Overview
- `a2a-migration/a2a-architecture.md` - Conceptual guide
- `a2a-migration/a2a-patterns-reference.md` - Implementation patterns
- `a2a-migration/a2a-sdk-integration.md` - SDK usage
- `a2a-migration/a2a-quality-assurance.md` - Validation procedures
- `a2a-migration/a2a-troubleshooting.md` - Common issues

---

## Version Information

**System Version**: 2.0
**A2A SDK**: via tmp-resources/a2a-python
**Temporal Python SDK**: ≥1.5.0
**Python**: ≥3.11

---

**Last Updated**: November 2024

# Sub-Agent Architecture for A2A + Temporal Project Generation

## Overview

This document specifies a **11-agent sequential pipeline** for generating Temporal-powered A2A (Agent-to-Agent) projects from natural language specifications. Each agent operates with high autonomy, performing a distinct phase of the generation process.

## Architecture Principles

- **Sequential Pipeline**: Agents execute in strict order, each building on previous agents' outputs
- **High Autonomy**: Each agent makes decisions independently without asking the main agent for guidance
- **Structured Communication**: Agents communicate via `a2a-analysis.json` (structured analysis document)
- **Documentation-Driven**: Each agent has access to the comprehensive `a2a-migration/` documentation
- **SDK-Integrated**: Generated code uses `a2a-sdk` for protocol compliance
- **Multi-Agent Output**: Generates complete multi-agent systems with gateways and workers

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Main Claude Code Agent                         │
│                     (Orchestrates pipeline execution)                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Spec Analyzer                                                        │
│    Input:  Natural language spec with code examples                     │
│    Output: a2a-analysis.json                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Project Scaffolder                                                   │
│    Input:  a2a-analysis.json                                            │
│    Output: Multi-agent package structure, shared/types.py, pyproject    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Agent Card Generator                                                 │
│    Input:  a2a-analysis.json                                            │
│    Output: {agent}_agent/agent_card.py for each agent                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. Activity Generator                                                   │
│    Input:  a2a-analysis.json, shared/types.py                           │
│    Output: {agent}_agent/activities.py for each agent                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. Workflow Generator (MOST COMPLEX)                                    │
│    Input:  a2a-analysis.json, activities.py files, shared/types.py      │
│    Output: {agent}_agent/workflow.py for each agent                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. Gateway Generator                                                    │
│    Input:  a2a-analysis.json, workflow.py files, agent_card.py files    │
│    Output: {agent}_agent/gateway.py for each agent                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. Infrastructure Generator                                             │
│    Input:  a2a-analysis.json, all agent files                           │
│    Output: {agent}_agent/worker.py, run_all.py, starter.py              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 8. Code Validator                                                       │
│    Input:  All generated Python files                                   │
│    Output: VALIDATION_REPORT.md, fixes applied                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 9. System Executor                                                      │
│    Input:  All generated files, a2a-analysis.json                       │
│    Output: SYSTEM_EXECUTION_REPORT.md, E2E validation                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 10. Streamlit Generator                                                 │
│    Input:  a2a-analysis.json, shared/types.py, execution report         │
│    Output: streamlit_app.py (human-in-the-loop UI)                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 11. Documentation Generator                                             │
│    Input:  All files, a2a-analysis.json, execution report               │
│    Output: README.md, SYSTEM_ARCHITECTURE.md, setup.sh                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### 1. Spec Analyzer

**Filename**: `claude/agents/spec-analyzer.md`

**Agent Configuration**:
```yaml
name: spec-analyzer
description: Analyzes natural language specification with embedded code to extract multi-agent architecture. MUST be invoked first when starting A2A project generation.
tools: Read, Write, Bash, Glob, Grep
model: inherit
```

**Responsibilities**:
- Read and parse natural language specification file
- Extract system overview (name, description, purpose)
- Identify all agents and their roles
- Parse agent skills from prose and code examples
- Extract workflow logic and activity requirements
- Map inter-agent communication patterns
- Identify shared data types from code examples
- Assign unique ports and task queues to each agent
- Generate structured `a2a-analysis.json`

**Input**:
- Natural language specification file (markdown or text)
- May contain embedded Python code examples
- May contain ASCII architecture diagrams

**Output**:
- `a2a-analysis.json` with schema:
  ```json
  {
    "analysis_date": "ISO 8601 timestamp",
    "spec_source": "path to input specification",
    "system_metadata": {
      "name": "system name",
      "description": "system purpose",
      "total_agents": 2
    },
    "project_config": {
      "project_name": "ProjectName",
      "project_name_snake": "project_name",
      "base_port": 8000
    },
    "agents": [
      {
        "agent_id": "agent_identifier",
        "name": "AgentDisplayName",
        "description": "What this agent does",
        "url": "http://localhost:8000",
        "port": 8000,
        "task_queue": "agent-task-queue",
        "package_name": "agent_name_agent",
        "skills": [
          {
            "id": "skill_id",
            "name": "Skill Name",
            "description": "What the skill does",
            "input_schema": {}
          }
        ],
        "capabilities": {
          "streaming": true,
          "push_notifications": true
        },
        "workflows": [
          {
            "name": "WorkflowClassName",
            "triggered_by_skill": "skill_id",
            "description": "What the workflow does"
          }
        ],
        "activities": [
          {
            "name": "activity_function_name",
            "description": "What the activity does",
            "is_a2a_communication": false
          }
        ],
        "calls_agents": ["other_agent_id"]
      }
    ],
    "shared_types": [
      {
        "name": "TypeName",
        "fields": [
          {"name": "field_name", "type": "str", "description": "field purpose"}
        ]
      }
    ],
    "translation_notes": [
      "Note about assumptions made during parsing"
    ]
  }
  ```

**Documentation References**:
- `a2a-migration/README.md` (overview)
- `a2a-migration/a2a-architecture.md` (conceptual understanding)
- `a2a-migration/a2a-patterns-reference.md` (implementation patterns)

**Success Criteria**:
- Valid JSON generated
- All agents identified from specification
- Skills correctly extracted for each agent
- Unique ports assigned (starting from base_port)
- Unique task queues assigned
- Inter-agent communication mapped

---

### 2. Project Scaffolder

**Filename**: `claude/agents/project-scaffolder.md`

**Agent Configuration**:
```yaml
name: project-scaffolder
description: Creates multi-agent Python project structure with shared types. Invoked after spec-analyzer completes.
tools: Read, Write, Bash
model: inherit
```

**Responsibilities**:
- Read `a2a-analysis.json` to understand project requirements
- Create multi-agent directory structure
- Generate `shared/types.py` with dataclasses for:
  - Shared types used across agents
  - Agent-specific input/output types
- Generate `pyproject.toml` with:
  - Package metadata
  - Dependencies (temporalio, a2a-sdk[http-server], httpx, mypy)
  - `[tool.uv]` configuration with `package = true`
  - Console script definitions for each agent's worker
  - Python 3.11+ requirement
- Create `.gitignore` with Python-specific ignores
- Create `__init__.py` in all package directories
- Create placeholder files for each agent package

**Input**:
- `a2a-analysis.json`

**Output**:
- Directory structure:
  ```
  {project_name}/
  ├── pyproject.toml
  ├── .gitignore
  ├── shared/
  │   ├── __init__.py
  │   └── types.py
  ├── {agent1}_agent/
  │   ├── __init__.py
  │   ├── agent_card.py (placeholder)
  │   ├── activities.py (placeholder)
  │   ├── workflow.py (placeholder)
  │   ├── gateway.py (placeholder)
  │   └── worker.py (placeholder)
  ├── {agent2}_agent/
  │   └── ...
  ├── run_all.py (placeholder)
  └── starter.py (placeholder)
  ```

**Documentation References**:
- `a2a-migration/a2a-architecture.md` (project structure)
- `a2a-migration/a2a-sdk-integration.md` (dependencies)
- `AGENTS.md` (Python standards)

**Success Criteria**:
- Package structure follows Python best practices
- All dataclasses in `shared/types.py` have complete type hints
- `pyproject.toml` includes `[tool.uv] package = true`
- Dependencies include `a2a-sdk[http-server]`
- Each agent has its own package directory

---

### 3. Agent Card Generator

**Filename**: `claude/agents/agent-card-generator.md`

**Agent Configuration**:
```yaml
name: agent-card-generator
description: Generates A2A Agent Card configurations for each agent using a2a-sdk types. Invoked after project-scaffolder completes.
tools: Read, Write, Edit
model: inherit
```

**Responsibilities**:
- Read `a2a-analysis.json` for agent details
- Generate `{agent}_agent/agent_card.py` for each agent with:
  - `AgentCard` using a2a-sdk types
  - `AgentSkill` for each skill with proper JSON schemas
  - `AgentCapabilities` configuration
  - `AgentInterface` for JSONRPC transport
- Ensure URLs match assigned ports
- Generate proper `inputSchema` JSON Schemas for each skill

**Input**:
- `a2a-analysis.json`
- `{agent}_agent/agent_card.py` (placeholder)

**Output**:
- Complete `{agent}_agent/agent_card.py` for each agent

**Example Output**:
```python
from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
    AgentInterface,
)

AGENT_CARD = AgentCard(
    name="RestaurantFinderAgent",
    description="Finds restaurants based on cuisine preferences",
    url="http://localhost:8000",
    interfaces=[
        AgentInterface(url="http://localhost:8000", transport="JSONRPC")
    ],
    capabilities=AgentCapabilities(
        streaming=True,
        pushNotifications=True,
    ),
    skills=[
        AgentSkill(
            id="find_restaurant",
            name="Find Restaurant",
            description="Search for restaurants by cuisine type and location",
            inputSchema={
                "type": "object",
                "properties": {
                    "cuisine": {"type": "string"},
                    "location": {"type": "string"}
                },
                "required": ["cuisine", "location"]
            }
        )
    ]
)
```

**Documentation References**:
- `a2a-migration/a2a-sdk-integration.md` (AgentCard types)
- `a2a-migration/a2a-patterns-reference.md` (agent card pattern)

**Success Criteria**:
- All agent cards use a2a-sdk types correctly
- URLs match configured ports
- Skills have valid JSON Schema inputSchema
- All required fields populated

---

### 4. Activity Generator

**Filename**: `claude/agents/activity-generator.md`

**Agent Configuration**:
```yaml
name: activity-generator
description: Generates activities.py with activity functions for each agent. Includes A2A communication activities. Invoked after agent-card-generator completes.
tools: Read, Write, Edit, Bash
model: inherit
```

**Responsibilities**:
- Read `a2a-analysis.json` and `shared/types.py`
- Generate `{agent}_agent/activities.py` for each agent with:
  - Business logic activities from spec
  - A2A communication activities (for agents that call others):
    - `send_a2a_task` - Send task to another agent
    - `poll_a2a_task_status` - Poll for task completion
  - Comprehensive docstrings
  - Complete type hints
  - Activity logging
- Import shared types from `shared.types`
- Use `httpx.AsyncClient()` for HTTP activities
- Use `a2a.client.A2AClient` for A2A activities

**Input**:
- `a2a-analysis.json`
- `shared/types.py`
- `{agent}_agent/activities.py` (placeholder)

**Output**:
- Complete `{agent}_agent/activities.py` for each agent

**Documentation References**:
- `a2a-migration/a2a-patterns-reference.md` (A2A activities pattern)
- `a2a-migration/a2a-sdk-integration.md` (A2AClient usage)
- `AGENTS.md` (Activity Implementation Reference)

**Success Criteria**:
- All activities have `@activity.defn` decorator
- Complete type hints on all functions
- A2A communication activities included for cross-agent callers
- Comprehensive docstrings
- No sandbox violations (activities can use httpx, I/O, etc.)

---

### 5. Workflow Generator

**Filename**: `claude/agents/workflow-generator.md`

**Agent Configuration**:
```yaml
name: workflow-generator
description: Generates workflow.py with Temporal workflow classes for each agent. Implements A2A handoff patterns. MOST COMPLEX agent. Invoked after activity-generator completes.
tools: Read, Write, Edit, Bash, Grep
model: sonnet
```

**Responsibilities** (MOST COMPLEX AGENT):
- Read `a2a-analysis.json`, `activities.py` files, and `shared/types.py`
- Create `@workflow.defn` class for each agent's workflow
- Implement skill-triggered workflow logic
- **Implement A2A Handoff Pattern** for cross-agent calls:
  - Send A2A task via activity
  - Durable polling loop (survives crashes)
  - Handle task states (submitted → working → completed)
- Configure activity execution with timeouts and retry policies
- Use `workflow.unsafe.imports_passed_through()` for activity imports
- Add workflow queries for status checking
- **CRITICAL**: Ensure workflow sandbox compliance

**A2A Handoff Pattern**:
```python
async def _handoff_to_agent(self, agent_url: str, skill_id: str, params: dict) -> dict:
    """Durably hand off to external A2A agent."""
    # Send task via activity (survives crashes)
    response = await workflow.execute_activity(
        send_a2a_task,
        args=[agent_url, skill_id, params],
        start_to_close_timeout=timedelta(seconds=60),
    )
    task_id = response.get("id")
    task_state = response.get("status", {}).get("state")

    # Durable polling loop
    while task_state in ["submitted", "working"]:
        await workflow.sleep(timedelta(seconds=5))
        status = await workflow.execute_activity(
            poll_a2a_task_status,
            args=[agent_url, task_id],
            start_to_close_timeout=timedelta(seconds=30),
        )
        task_state = status.get("status", {}).get("state")

    return response.get("artifacts", [])
```

**Input**:
- `a2a-analysis.json`
- `{agent}_agent/activities.py` (completed)
- `shared/types.py`
- `{agent}_agent/workflow.py` (placeholder)

**Output**:
- Complete `{agent}_agent/workflow.py` for each agent

**Documentation References** (READS ALL DOCS):
- `a2a-migration/a2a-architecture.md` (conceptual understanding)
- `a2a-migration/a2a-patterns-reference.md` (A2A handoff pattern)
- `a2a-migration/a2a-troubleshooting.md` (sandbox violations, common issues)
- `AGENTS.md` (Workflow Implementation Reference, Critical Pitfalls)

**Success Criteria**:
- All workflows have `@workflow.defn` decorator
- A2A handoff pattern implemented for cross-agent calls
- Durable polling loops (in workflow, not inline)
- Activity execution configured with timeouts
- Workflow sandbox compliant (passthrough imports)
- `RetryPolicy` imported from `temporalio.common`
- Type hints complete

---

### 6. Gateway Generator

**Filename**: `claude/agents/gateway-generator.md`

**Agent Configuration**:
```yaml
name: gateway-generator
description: Generates gateway.py with FastAPI A2A gateway for each agent using A2AFastAPIApplication. Invoked after workflow-generator completes.
tools: Read, Write, Edit, Bash
model: inherit
```

**Responsibilities**:
- Read `a2a-analysis.json`, `workflow.py` files, and `agent_card.py` files
- Generate `{agent}_agent/gateway.py` for each agent with:
  - `A2AFastAPIApplication` from a2a-sdk
  - `TemporalAgentExecutor` to route A2A tasks to workflows
  - `DefaultRequestHandler` with task store
  - Skill-to-workflow mapping
  - Lifespan context manager for Temporal client
  - Proper async initialization
  - Uvicorn runner for standalone execution

**Input**:
- `a2a-analysis.json`
- `{agent}_agent/workflow.py` (completed)
- `{agent}_agent/agent_card.py` (completed)
- `{agent}_agent/gateway.py` (placeholder)

**Output**:
- Complete `{agent}_agent/gateway.py` for each agent

**Documentation References**:
- `a2a-migration/a2a-sdk-integration.md` (A2AFastAPIApplication pattern)
- `a2a-migration/a2a-patterns-reference.md` (gateway pattern)

**Success Criteria**:
- Uses `A2AFastAPIApplication` correctly
- Implements `AgentExecutor` for Temporal routing
- Lifespan manages Temporal client lifecycle
- Port matches agent_card URL
- Task store configured

---

### 7. Infrastructure Generator

**Filename**: `claude/agents/infrastructure-generator.md`

**Agent Configuration**:
```yaml
name: infrastructure-generator
description: Generates worker.py for each agent plus run_all.py and starter.py orchestration scripts. Invoked after gateway-generator completes.
tools: Read, Write, Bash
model: inherit
```

**Responsibilities**:
- Read `a2a-analysis.json`, `workflow.py` files, and `activities.py` files
- Generate `{agent}_agent/worker.py` for each agent:
  - Import workflow class and activity functions
  - Create async main function
  - Connect to Temporal server
  - Create Worker with agent's task queue
  - Register workflow and activities
  - **CRITICAL**: Synchronous `main()` for console script
- Generate `run_all.py` orchestration script:
  - Start all workers
  - Start all gateways
  - Handle graceful shutdown
- Generate `starter.py` demo script:
  - Demonstrate end-to-end A2A flow
  - Fetch agent cards
  - Send test tasks
  - Poll for results

**Input**:
- `a2a-analysis.json`
- `{agent}_agent/workflow.py` (completed)
- `{agent}_agent/activities.py` (completed)
- `{agent}_agent/worker.py` (placeholder)
- `run_all.py` (placeholder)
- `starter.py` (placeholder)

**Output**:
- Complete `{agent}_agent/worker.py` for each agent
- Complete `run_all.py`
- Complete `starter.py`

**Documentation References**:
- `a2a-migration/a2a-patterns-reference.md` (worker, orchestration patterns)
- `a2a-migration/a2a-troubleshooting.md` (async main pitfalls)
- `AGENTS.md` (Worker Implementation Reference)

**Success Criteria**:
- Workers register workflow and activities correctly
- Workers have synchronous `main()` for console scripts
- `run_all.py` starts all components
- `starter.py` demonstrates full A2A flow
- Graceful shutdown handling

---

### 8. Code Validator

**Filename**: `claude/agents/code-validator.md`

**Agent Configuration**:
```yaml
name: code-validator
description: Validates all generated code for syntax, types, and A2A/Temporal compliance. Autonomously fixes issues. Invoked after infrastructure-generator completes.
tools: Read, Edit, Bash, Grep, Glob
model: inherit
```

**Responsibilities**:
- Run syntax validation: `python3 -m py_compile` on all Python files
- Run type checking: `mypy --strict` on all packages
- Check workflow sandbox compliance
- Verify `pyproject.toml` has `[tool.uv] package = true`
- **A2A-Specific Validations**:
  - Agent cards use correct a2a-sdk types
  - Skill IDs consistent across card and gateway
  - Port uniqueness across agents
  - Task queue uniqueness
  - URL consistency (card URL matches gateway port)
- **If errors found**: Fix them autonomously and re-validate
- Generate validation report

**Input**:
- All files in project directory
- `a2a-analysis.json` (for context)

**Output**:
- `VALIDATION_REPORT.md` with results
- Fixed code files (if issues found)

**Documentation References**:
- `a2a-migration/a2a-quality-assurance.md` (validation procedures)
- `a2a-migration/a2a-troubleshooting.md` (common issues)
- `AGENTS.md` (Critical Pitfalls section)

**Success Criteria**:
- All syntax validation passes
- `mypy --strict` passes with zero errors
- Workflow sandbox imports succeed
- All A2A-specific validations pass
- Validation report generated

---

### 9. System Executor

**Filename**: `claude/agents/system-executor.md`

**Agent Configuration**:
```yaml
name: system-executor
description: Executes and validates the complete multi-agent A2A system end-to-end. Invoked after code-validator, before streamlit-generator.
tools: Read, Write, Bash
model: inherit
```

**Responsibilities**:
- Check if Temporal server is running (ports 7233/8233), start if needed
- Install dependencies via `uv sync`
- Start ALL workers (one per agent)
- Start ALL gateways (one per agent)
- **A2A Verification**:
  - Fetch agent cards from all agents
  - Verify cards are valid JSON
  - Send test A2A tasks
  - Verify task lifecycle (submitted → working → completed)
- **Cross-Agent Testing** (if applicable):
  - Test inter-agent communication
  - Verify durable handoff works
- Handle failures autonomously:
  - Parse error logs
  - Identify error types
  - Invoke code-validator to fix issues
  - Retry execution up to 3 times
- Cleanup all processes
- Generate comprehensive `SYSTEM_EXECUTION_REPORT.md`

**Input**:
- `a2a-analysis.json`
- All files in project directory
- `VALIDATION_REPORT.md`

**Output**:
- `SYSTEM_EXECUTION_REPORT.md` with:
  - Execution summary (PASS/FAIL)
  - Agent card verification results
  - Task execution results
  - Worker and gateway logs
  - Any errors and fixes applied

**Documentation References**:
- `a2a-migration/a2a-troubleshooting.md` (runtime errors)
- `a2a-migration/a2a-quality-assurance.md` (E2E testing)

**Success Criteria**:
- Temporal server is running
- All workers start without errors
- All gateways start without errors
- Agent cards accessible at `/.well-known/agent.json`
- A2A tasks can be sent and received
- Execution report documents all results

---

### 10. Streamlit Generator

**Filename**: `claude/agents/streamlit-generator.md`

**Agent Configuration**:
```yaml
name: streamlit-generator
description: Generates streamlit_app.py for human-in-the-loop interaction with coordinator workflow. Invoked after system-executor passes validation.
tools: Read, Write, Edit, Bash, Glob, Grep
model: inherit
```

**Responsibilities**:
- Read `a2a-analysis.json` to get `coordinator_interaction` schema
- Read `shared/types.py` for dataclass definitions
- Read `SYSTEM_EXECUTION_REPORT.md` for port and system info
- Generate `streamlit_app.py` with:
  - Form for workflow input fields (from `workflow_input` schema)
  - Signal buttons for human decisions (from `signals`)
  - Query result display (from `queries`)
  - Real-time status updates via polling
- Use `@st.cache_resource` for Temporal client
- Use `st.session_state` for workflow_id persistence
- Add streamlit dependency to `pyproject.toml`
- **Validate the app runs correctly**:
  - Syntax validation (`py_compile`)
  - Import validation (no ImportError)
  - Runtime validation (start headless, curl HTTP 200)
- **Autonomously fix issues** and retry validation up to 3 times

**Input**:
- `a2a-analysis.json`
- `shared/types.py`
- `SYSTEM_EXECUTION_REPORT.md`
- `pyproject.toml`

**Output**:
- `streamlit_app.py` at project root
- Updated `pyproject.toml` (adds streamlit dependency)

**Documentation References**:
- `streamlit-ui-guide.md` (Streamlit patterns)
- `a2a-migration/a2a-patterns-reference.md` (Temporal signal/query patterns)

**Validation Process**:
1. Syntax check: `python3 -m py_compile streamlit_app.py`
2. Import check: `python3 -c "import streamlit_app"`
3. Runtime check: Start Streamlit headless, curl localhost:8502, verify HTTP 200
4. Cleanup: Kill Streamlit process

**Success Criteria**:
- Streamlit app generates forms from `coordinator_interaction.workflow_input`
- Signal buttons created for each signal in `coordinator_interaction.signals`
- Query display created for each query in `coordinator_interaction.queries`
- Session state persists workflow_id across reruns
- **Syntax validation passes**
- **Import validation passes**
- **Runtime validation passes (HTTP 200)**
- **Process cleanup succeeds (no zombies)**

---

### 11. Documentation Generator

**Filename**: `claude/agents/documentation-generator.md`

**Agent Configuration**:
```yaml
name: documentation-generator
description: Generates comprehensive documentation for the multi-agent A2A system. Invoked after streamlit-generator completes.
tools: Read, Write, Bash
model: inherit
```

**Responsibilities**:
- Read all generated files and `a2a-analysis.json`
- Generate comprehensive `README.md`:
  - System overview
  - Architecture diagram (ASCII)
  - Prerequisites (UV, Python 3.11+, Temporal server)
  - Quick start instructions
  - Project structure explanation
  - How to run all components
  - How to test the system
  - Agent-by-agent documentation
  - A2A protocol reference
  - Configuration options
  - Troubleshooting section
- Generate `SYSTEM_ARCHITECTURE.md`:
  - Detailed architecture explanation
  - Agent interaction diagrams
  - Data flow documentation
- Create `setup.sh` script:
  - Install dependencies
  - Run validation commands
  - Display success message with next steps

**Input**:
- `a2a-analysis.json`
- All files in project directory
- `VALIDATION_REPORT.md`
- `SYSTEM_EXECUTION_REPORT.md`

**Output**:
- `README.md` (project root)
- `SYSTEM_ARCHITECTURE.md`
- `setup.sh` (executable)

**Documentation References**:
- `a2a-migration/README.md` (documentation template)
- `a2a-migration/a2a-architecture.md` (architecture concepts)

**Success Criteria**:
- README is comprehensive and easy to follow
- Architecture diagram included
- Running instructions are clear
- All agents documented
- setup.sh is executable and functional

---

## Communication Protocol

### a2a-analysis.json Schema

This structured document serves as the primary communication medium between agents. All agents downstream of the analyzer read this file to understand the project requirements.

**Location**: Project root directory

**Schema**: See Agent 1 (Spec Analyzer) output specification above.

**Usage**:
- **Agent 1** (Spec Analyzer): Writes this file
- **Agents 2-11**: Read this file for context and requirements
- **Main Agent**: Can inspect this file to track pipeline progress

---

## Implementation Guidelines

### Directory Structure for Sub-Agents

All sub-agent definitions are placed in:
```
claude/agents/
├── spec-analyzer.md
├── project-scaffolder.md
├── agent-card-generator.md
├── activity-generator.md
├── workflow-generator.md
├── gateway-generator.md
├── infrastructure-generator.md
├── code-validator.md
├── system-executor.md
├── streamlit-generator.md
└── documentation-generator.md
```

### Sub-Agent File Format

Each sub-agent markdown file follows this structure:

```markdown
---
name: agent-name
description: When this agent should be invoked (clear trigger conditions)
tools: Tool1, Tool2, Tool3
model: inherit
---

You are a [role description].

## Your Responsibilities

[Detailed bullet list of what this agent does]

## Inputs

[What files/data you need to read]

## Outputs

[What files/data you will create or modify]

## Documentation to Reference

Before starting, read these documentation files:
- `path/to/doc1.md`
- `path/to/doc2.md`

## Process

1. [Step-by-step process this agent follows]
2. [Be very specific and detailed]
3. [Include verification steps]

## Success Criteria

- [Criteria 1]
- [Criteria 2]
- [How to verify success]

## Critical Pitfalls to Avoid

[Specific common mistakes this agent must not make]

## Example

[Optional: Show example input/output for this agent]
```

### Invoking the Pipeline

Main agent workflow:

```python
# Main agent orchestrates the pipeline
user: "Generate an A2A project from spec.md"

main_agent:
  1. Invoke spec-analyzer sub-agent
  2. Wait for a2a-analysis.json
  3. Invoke project-scaffolder sub-agent
  4. Wait for package structure
  5. Invoke agent-card-generator sub-agent
  6. Wait for agent_card.py files
  7. Invoke activity-generator sub-agent
  8. Wait for activities.py files
  9. Invoke workflow-generator sub-agent
  10. Wait for workflow.py files
  11. Invoke gateway-generator sub-agent
  12. Wait for gateway.py files
  13. Invoke infrastructure-generator sub-agent
  14. Wait for worker.py, run_all.py, starter.py
  15. Invoke code-validator sub-agent
  16. If validation FAILS: halt and report errors
  17. If validation PASSES: invoke system-executor sub-agent
  18. Wait for execution results
  19. If execution FAILS: review errors, possibly re-run validator
  20. If execution PASSES: invoke streamlit-generator sub-agent
  21. Wait for streamlit_app.py
  22. Invoke documentation-generator sub-agent
  23. Report completion to user with summary
```

### Error Handling

- **Agents 1-7** (Generators): If cannot proceed, write error to `GENERATION_ERRORS.md` and halt
- **Agent 8** (Validator): Autonomously fix errors, re-validate, report unfixable errors
- **Agent 9** (Executor): Autonomously fix runtime errors, retry execution, report if unfixable
- **Agent 10** (Streamlit Generator): Generates UI after execution passes
- **Agent 11** (Documentation): Always runs after streamlit-generator completes

---

## Key Reference Files

| File | Why Important |
|------|---------------|
| `tmp-resources/a2a-python/src/a2a/types.py` | A2A SDK types |
| `tmp-resources/a2a-python/src/a2a/server/apps/jsonrpc/fastapi_app.py` | A2AFastAPIApplication |
| `tmp-resources/a2a-python/src/a2a/client/client.py` | A2AClient for calls |
| `a2a-temporal-example-spec.md` | Example input format |
| `a2a-migration/*.md` | All migration documentation |

---

## Notes

- **Workflow Generator** is the most complex and critical agent - uses Sonnet model
- **Code Validator** and **System Executor** have autonomy to fix issues without human intervention
- **a2a-analysis.json** schema may evolve as agents reveal additional needs
- All agents should follow user's global Python standards (type hints, pytest, ruff, mypy strict)
- Consider adding **test-generator** agent in future for creating pytest test suites

---

**Last Updated**: November 2024

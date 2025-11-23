# Sub-Agent Architecture for Conductor-to-Temporal Migration

## Overview

This document specifies an **8-agent sequential pipeline** for converting Netflix Conductor workflows to Temporal Python SDK applications. Each agent operates with high autonomy, performing a distinct phase of the migration process.

## Architecture Principles

- **Sequential Pipeline**: Agents execute in strict order, each building on previous agents' outputs
- **High Autonomy**: Each agent makes decisions independently without asking the main agent for guidance
- **Structured Communication**: Agents communicate via `conductor-analysis.json` (structured analysis document)
- **Documentation-Driven**: Each agent has access to the comprehensive `conductor-migration/` documentation
- **Test-First**: Dedicated validation agent ensures code quality before finalization

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Main Claude Code Agent                         │
│                     (Orchestrates pipeline execution)                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. Conductor Analyzer                                                   │
│    Input:  conductor-definition/*.json                                  │
│    Output: conductor-analysis.json                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. Project Scaffolder                                                   │
│    Input:  conductor-analysis.json                                      │
│    Output: Package structure, shared.py, pyproject.toml                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Activity Generator                                                   │
│    Input:  conductor-analysis.json, shared.py                           │
│    Output: activities.py                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. Workflow Generator (MOST COMPLEX)                                    │
│    Input:  conductor-analysis.json, activities.py, shared.py            │
│    Output: workflow.py                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. Infrastructure Generator                                             │
│    Input:  conductor-analysis.json, workflow.py, activities.py          │
│    Output: worker.py, starter.py, interact.py                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. Code Validator                                                       │
│    Input:  All generated Python files                                   │
│    Output: Validation report, fixes applied                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6.5 Workflow Executor (NEW)                                             │
│    Input:  All generated files, conductor-analysis.json                 │
│    Output: WORKFLOW_EXECUTION_REPORT.md, execution validation           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. Documentation Generator                                              │
│    Input:  All files, conductor-analysis.json, execution report         │
│    Output: README.md, comparison docs, setup.sh                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### 1. Conductor Analyzer

**Filename**: `subagents/conductor-analyzer.md`

**Agent Configuration**:
```yaml
name: conductor-analyzer
description: Analyzes Conductor workflow JSON and creates structured analysis document. MUST be invoked first when starting Conductor-to-Temporal migration.
tools: Read, Write, Bash, Glob, Grep
model: inherit
```

**Responsibilities**:
- Parse and validate Conductor workflow JSON from `conductor-definition/` directory
- Extract workflow metadata (name, version, description, inputs, outputs)
- Analyze all tasks and identify their types (SIMPLE, HTTP, FORK_JOIN, SWITCH, DO_WHILE, DYNAMIC_FORK, SUB_WORKFLOW, WAIT, HUMAN_TASK)
- Map control flow patterns (sequential, parallel, conditional, loops)
- Identify human interaction patterns (HUMAN_TASK, WAIT, expressions like `${user_action.output.*}`)
- Analyze data flow and dependencies between tasks
- Detect nested control flow structures (e.g., SWITCH within DO_WHILE within FORK_JOIN)
- Generate structured `conductor-analysis.json` with complete analysis

**Input**:
- Conductor workflow JSON file(s) in `conductor-definition/` directory

**Output**:
- `conductor-analysis.json` with schema:
  ```json
  {
    "workflow_metadata": {
      "name": "string",
      "version": "number",
      "description": "string",
      "inputs": ["field1", "field2"],
      "outputs": ["field1", "field2"]
    },
    "tasks": [
      {
        "name": "string",
        "type": "SIMPLE|HTTP|FORK_JOIN|SWITCH|DO_WHILE|...",
        "reference_name": "string",
        "description": "string",
        "inputs": {},
        "dependencies": ["ref1", "ref2"],
        "control_flow": {
          "is_conditional": "boolean",
          "is_loop": "boolean",
          "is_parallel": "boolean",
          "nesting_level": "number"
        }
      }
    ],
    "human_interaction_patterns": [
      {
        "task_reference": "string",
        "pattern_type": "approval|wait|notification",
        "signal_or_update": "signal|update",
        "data_flow": ["${user_action.output.field}"]
      }
    ],
    "control_flow_summary": {
      "max_nesting_depth": "number",
      "has_loops": "boolean",
      "has_parallel_execution": "boolean",
      "has_dynamic_parallelism": "boolean",
      "complexity_score": "low|medium|high"
    },
    "recommended_patterns": {
      "human_interaction": "Updates recommended for X tasks, Signals for Y tasks",
      "error_handling": "Retry policies needed for X activities",
      "special_considerations": ["consideration1", "consideration2"]
    }
  }
  ```

**Documentation References**:
- `conductor-migration/conductor-migration-guide.md` (Phase 1.1)
- `conductor-migration/conductor-primitives-reference.md` (all task types)
- `conductor-migration/conductor-human-interaction.md` (human patterns)
- `conductor-migration/conductor-architecture.md` (architectural differences)

**Success Criteria**:
- Valid JSON generated
- All tasks identified and categorized
- Human interaction patterns correctly classified
- Control flow complexity accurately assessed

---

### 2. Project Scaffolder

**Filename**: `subagents/project-scaffolder.md`

**Agent Configuration**:
```yaml
name: project-scaffolder
description: Creates Python project structure, shared types, and configuration files. Invoked after conductor-analyzer completes.
tools: Read, Write, Bash
model: inherit
```

**Responsibilities**:
- Read `conductor-analysis.json` to understand workflow requirements
- Create Python package directory structure (`{workflow_name}_temporal/`)
- Generate `shared.py` with dataclasses for:
  - Workflow input/output types (from workflow metadata)
  - Activity-specific input/output types (from tasks analysis)
  - Human interaction data types (from human_interaction_patterns)
- Generate `pyproject.toml` with:
  - Package metadata
  - Dependencies (temporalio, httpx if HTTP tasks detected)
  - Console script definitions for worker and starter
  - `[tool.uv]` configuration with `package = true`
  - Python 3.11+ requirement
- Create `.gitignore` with Python-specific ignores
- Create `__init__.py` in package directory
- Create empty placeholder files for next agents: `activities.py`, `workflow.py`, `worker.py`, `starter.py`

**Input**:
- `conductor-analysis.json`

**Output**:
- Directory structure:
  ```
  {workflow_name}_temporal/
  ├── __init__.py
  ├── shared.py
  ├── activities.py (empty placeholder)
  ├── workflow.py (empty placeholder)
  ├── worker.py (empty placeholder)
  └── starter.py (empty placeholder)
  ```
- `pyproject.toml`
- `.gitignore`

**Documentation References**:
- `conductor-migration/conductor-migration-guide.md` (Phase 1.2)
- `AGENTS.md` (Project Structure section)
- `conductor-migration/conductor-troubleshooting.md` (pyproject.toml pitfalls)

**Success Criteria**:
- Package structure follows Python best practices
- All dataclasses in `shared.py` have complete type hints
- `pyproject.toml` includes `[tool.uv] package = true`
- Console script definitions use synchronous entry points (not async)

---

### 3. Activity Generator

**Filename**: `subagents/activity-generator.md`

**Agent Configuration**:
```yaml
name: activity-generator
description: Generates activities.py with activity functions translated from Conductor tasks. Invoked after project-scaffolder completes.
tools: Read, Write, Edit, Bash
model: inherit
```

**Responsibilities**:
- Read `conductor-analysis.json` and `shared.py`
- Translate SIMPLE tasks to `@activity.defn` functions
- Translate HTTP tasks to `@activity.defn` functions with `httpx` async client
- Generate activity-specific input/output dataclasses in `shared.py` (if not already present)
- Add comprehensive docstrings to each activity:
  - Purpose and business logic
  - Input parameters with types
  - Return value with type
  - Timeout and retry recommendations
- Use complete type hints (no `Any` type)
- Follow modern Pythonic patterns
- Add imports: `from temporalio import activity`, `import httpx` (if needed)
- Handle activity context logging: `activity.logger.info()`

**Input**:
- `conductor-analysis.json`
- `{workflow_name}_temporal/shared.py`
- Empty `{workflow_name}_temporal/activities.py`

**Output**:
- Complete `{workflow_name}_temporal/activities.py`
- Updated `{workflow_name}_temporal/shared.py` (with any additional dataclasses)

**Documentation References**:
- `conductor-migration/conductor-migration-guide.md` (Phase 2.1)
- `conductor-migration/conductor-primitives-reference.md` (SIMPLE and HTTP task examples)
- `AGENTS.md` (Activity Implementation Reference)

**Success Criteria**:
- All activities have `@activity.defn` decorator
- Complete type hints on all functions
- Comprehensive docstrings with timeout/retry guidance
- HTTP tasks use `httpx.AsyncClient()` properly
- No sandbox violations (activities can use httpx, I/O, etc.)

---

### 4. Workflow Generator

**Filename**: `subagents/workflow-generator.md`

**Agent Configuration**:
```yaml
name: workflow-generator
description: Generates workflow.py with complete control flow translation. MOST COMPLEX agent. Invoked after activity-generator completes.
tools: Read, Write, Edit, Bash, Grep
model: sonnet
```

**Responsibilities** (MOST COMPLEX AGENT):
- Read `conductor-analysis.json`, `activities.py`, and `shared.py`
- Create `@workflow.defn` class
- Translate control flow patterns:
  - Sequential tasks → `await` chain
  - FORK_JOIN + JOIN → `asyncio.gather()`
  - SWITCH → `if/elif/else` statements
  - DO_WHILE → `while` loop (with `continue-as-new` for long-running loops)
  - DYNAMIC_FORK → list comprehension + `asyncio.gather()`
  - SUB_WORKFLOW → `workflow.execute_child_workflow()`
- Implement human interaction patterns:
  - WAIT tasks → Signal + `workflow.wait_condition()`
  - HUMAN_TASK → Update/Signal + `workflow.wait_condition()`
  - Implement update handlers: `@workflow.update` with validation
  - Implement signal handlers: `@workflow.signal`
  - Handle data flow: `${user_action.output.approved}` → `self._user_action.approved`
- Configure activity execution:
  - `workflow.execute_activity()` with proper argument passing
  - Set timeouts: `start_to_close_timeout`, `schedule_to_close_timeout`
  - Configure retry policies: `RetryPolicy(initial_interval, maximum_attempts, ...)`
- Translate data passing:
  - `${workflow.input.field}` → `input.field`
  - `${task_ref.output.field}` → `result_variable.field`
- Handle nested control flow (preserve execution order, add detailed comments)
- Add workflow queries for status checking: `@workflow.query`
- **CRITICAL**: Ensure workflow sandbox compliance:
  - Import activities by name: `from {package}.activities import activity1, activity2`
  - NEVER import entire activities module
  - No non-deterministic code in workflow
- Add comprehensive docstrings and inline comments for complex logic

**Input**:
- `conductor-analysis.json`
- `{workflow_name}_temporal/activities.py`
- `{workflow_name}_temporal/shared.py`
- Empty `{workflow_name}_temporal/workflow.py`

**Output**:
- Complete `{workflow_name}_temporal/workflow.py`

**Documentation References** (READS ALL DOCS):
- `conductor-migration/conductor-migration-guide.md` (Phase 2.2)
- `conductor-migration/conductor-primitives-reference.md` (ALL task types with examples)
- `conductor-migration/conductor-human-interaction.md` (Signals vs Updates, wait patterns)
- `conductor-migration/conductor-architecture.md` (control flow patterns)
- `conductor-migration/conductor-troubleshooting.md` (sandbox violations, RetryPolicy imports)
- `AGENTS.md` (Workflow Implementation Reference, Critical Pitfalls)

**Success Criteria**:
- All control flow correctly translated
- Human interaction uses appropriate pattern (Signal vs Update)
- Activity execution configured with timeouts and retries
- Workflow sandbox compliant (specific imports, no non-deterministic code)
- `RetryPolicy` imported from `temporalio.common` (NOT `temporalio.workflow`)
- Activity function argument counts match execute_activity calls
- Type hints complete (no `Any`)
- Comprehensive docstrings and comments for complex logic

---

### 5. Infrastructure Generator

**Filename**: `subagents/infrastructure-generator.md`

**Agent Configuration**:
```yaml
name: infrastructure-generator
description: Generates worker.py and starter.py for workflow execution. Invoked after workflow-generator completes.
tools: Read, Write, Bash
model: inherit
```

**Responsibilities**:
- Read `conductor-analysis.json`, `workflow.py`, and `activities.py`
- Generate `worker.py`:
  - Import workflow class and activity functions (by name, not module)
  - Create async main function
  - Connect to Temporal server (localhost:7233 default)
  - Create Worker with task queue
  - Register workflow and activities
  - Add logging configuration
  - Add PID file management
  - Run worker until interrupted
- Generate `starter.py`:
  - Import workflow class and input dataclass
  - Create synchronous main function (NOT async - console script requirement)
  - Connect to Temporal client
  - Generate example input data (from workflow metadata)
  - Start workflow execution with `client.execute_workflow()`
  - Display results and workflow URL
  - Add error handling

**Input**:
- `conductor-analysis.json`
- `{workflow_name}_temporal/workflow.py`
- `{workflow_name}_temporal/activities.py`
- `{workflow_name}_temporal/shared.py`
- Empty `{workflow_name}_temporal/worker.py`
- Empty `{workflow_name}_temporal/starter.py`

**Output**:
- Complete `{workflow_name}_temporal/worker.py`
- Complete `{workflow_name}_temporal/starter.py`

**Documentation References**:
- `conductor-migration/conductor-migration-guide.md` (Phase 2.3, 2.4)
- `AGENTS.md` (Worker and Starter Implementation References)
- `conductor-migration/conductor-troubleshooting.md` (async main pitfalls)

**Success Criteria**:
- Worker registers workflow and activities correctly
- Worker imports by name (not module) to avoid sandbox issues
- Starter has synchronous main function (console script compatible)
- Starter generates valid example input data
- Both files have proper error handling and logging

---

### 6. Code Validator

**Filename**: `subagents/code-validator.md`

**Agent Configuration**:
```yaml
name: code-validator
description: Validates all generated code for syntax, types, and Temporal compliance. Invoked after infrastructure-generator completes.
tools: Read, Edit, Bash, Grep, Glob
model: inherit
```

**Responsibilities**:
- Run syntax validation: `python3 -m py_compile` on all Python files
- Run type checking: `mypy --strict` on package directory
- Check workflow sandbox compliance: `python3 -c "from {package}.workflow import {WorkflowClass}"`
- Verify `pyproject.toml` has `[tool.uv] package = true`
- Check console script configuration (synchronous entry points)
- Verify activity argument counts match execute_activity calls
- Check RetryPolicy import (from temporalio.common, not temporalio.workflow)
- Verify all dataclasses have type hints
- Check for common pitfalls from troubleshooting guide
- **If errors found**: Fix them autonomously and re-validate
- Generate validation report with:
  - Syntax validation: PASS/FAIL
  - Type checking: PASS/FAIL (with error details if failed)
  - Sandbox compliance: PASS/FAIL
  - Issues found and fixed
  - Remaining issues (if any)

**Input**:
- All files in `{workflow_name}_temporal/` directory
- `pyproject.toml`
- `conductor-analysis.json` (for context)

**Output**:
- `VALIDATION_REPORT.md` with results
- Fixed code files (if issues found)

**Documentation References**:
- `conductor-migration/conductor-migration-guide.md` (Phase 3)
- `conductor-migration/conductor-quality-assurance.md` (validation procedures, success criteria)
- `conductor-migration/conductor-troubleshooting.md` (all common issues)
- `AGENTS.md` (Critical Pitfalls section)

**Success Criteria**:
- All syntax validation passes
- `mypy --strict` passes with zero errors
- Workflow sandbox import succeeds
- No common pitfalls detected
- Validation report generated

---

### 6.5 Workflow Executor

**Filename**: `subagents/workflow-executor.md`

**Agent Configuration**:
```yaml
name: workflow-executor
description: Executes and validates the generated workflow end-to-end. Invoked after code-validator, before documentation-generator.
tools: Read, Write, Bash
model: inherit
```

**Responsibilities**:
- Check if Temporal server is running (ports 7233/8233), start if needed
- Install dependencies via `uv sync`
- Analyze workflow type (simple vs. interactive with handlers)
- Execute end-to-end test:
  - Start worker process in background
  - Execute workflow via starter
  - For simple workflows: Wait for COMPLETED status (30-60s timeout)
  - For interactive workflows: Send test interactions via `uv run interact`, verify responses
- Validate execution using Temporal CLI commands (`temporal workflow show`)
- Handle failures autonomously:
  - Parse error logs (worker.log, starter.log)
  - Identify error types (imports, sandbox violations, activity failures)
  - Invoke other agents to fix issues (code-validator, infrastructure-generator)
  - Retry execution up to 3 times with fixes applied
- Cleanup processes and PID files
- Generate comprehensive `WORKFLOW_EXECUTION_REPORT.md`

**Input**:
- `conductor-analysis.json`
- All files in `{workflow_name}_temporal/` directory
- `pyproject.toml`
- `VALIDATION_REPORT.md`

**Output**:
- `WORKFLOW_EXECUTION_REPORT.md` with:
  - Execution summary (PASS/FAIL)
  - Workflow ID and Web UI link
  - Worker and starter logs
  - Validation results
  - Any errors and fixes applied
  - Temporal CLI commands used

**Documentation References**:
- `tmp-workflow-running-guide.md` (ALL sections - server, worker, workflows, interactions, troubleshooting)
- `conductor-migration/conductor-troubleshooting.md` (runtime errors)
- `AGENTS.md` (understanding generated code structure)

**Success Criteria**:
- Temporal server is running
- Worker starts without errors
- Workflow executes without immediate failures
- For simple workflows: Reaches COMPLETED status
- For interactive workflows: Reaches RUNNING state, responds to test interactions
- No workflow task failures in execution history
- Worker logs show no crashes or critical errors
- Execution report documents all results

**Critical Considerations**:
- This agent **proves the workflow works** before documentation claims it does
- Uses autonomous fix-and-retry strategy (up to 3 rounds)
- Distinguishes between simple and interactive workflows for different success criteria
- Manages Temporal server, worker lifecycle, and cleanup
- Can invoke other agents (code-validator, infrastructure-generator) to fix runtime issues

---

### 7. Documentation Generator

**Filename**: `subagents/documentation-generator.md`

**Agent Configuration**:
```yaml
name: documentation-generator
description: Generates comprehensive documentation and setup scripts. Invoked after code-validator passes validation.
tools: Read, Write, Bash
model: inherit
```

**Responsibilities**:
- Read all generated files and `conductor-analysis.json`
- Generate comprehensive `README.md`:
  - Project overview (generated from Conductor workflow X)
  - Prerequisites (UV, Python 3.11+, Temporal server)
  - Quick start instructions
  - Project structure explanation
  - How to run the worker
  - How to run the starter
  - How to interact with workflow (if human interaction present)
  - Configuration options
  - Troubleshooting section
- Generate `CONDUCTOR_COMPARISON.md`:
  - Side-by-side comparison of Conductor JSON and Temporal Python
  - Show how each Conductor task translates to Temporal code
  - Highlight key differences and patterns used
- Generate `CONDUCTOR_MIGRATION_NOTES.md`:
  - Migration decisions made
  - Patterns chosen (Signal vs Update decisions)
  - Any assumptions or considerations
  - Future customization recommendations
- Create `setup.sh` script:
  - Install dependencies: `uv venv && uv sync --all-extras`
  - Run validation commands
  - Display success message
- Update package `README.md` (inside package directory) with module documentation

**Input**:
- `conductor-analysis.json`
- All files in `{workflow_name}_temporal/` directory
- `pyproject.toml`
- `VALIDATION_REPORT.md`

**Output**:
- `README.md` (project root)
- `CONDUCTOR_COMPARISON.md`
- `CONDUCTOR_MIGRATION_NOTES.md`
- `setup.sh` (executable)
- `{workflow_name}_temporal/README.md` (module docs)

**Documentation References**:
- `conductor-migration/conductor-migration-guide.md` (Phase 4)
- `README.md` (template structure to follow)
- Example workflows for comparison format

**Success Criteria**:
- README is comprehensive and easy to follow
- Comparison doc shows clear Conductor → Temporal mappings
- Migration notes document all key decisions
- setup.sh script is executable and functional
- Documentation matches quality standards

---

## Communication Protocol

### conductor-analysis.json Schema

This structured document serves as the primary communication medium between agents. All agents downstream of the analyzer read this file to understand the workflow requirements.

**Location**: Project root directory

**Schema**: See Agent 1 (Conductor Analyzer) output specification above.

**Usage**:
- **Agent 1** (Analyzer): Writes this file
- **Agents 2-7 (plus 6.5)**: Read this file for context and requirements
- **Main Agent**: Can inspect this file to track pipeline progress

---

## Implementation Guidelines

### Directory Structure for Sub-Agents

All sub-agent definitions should be placed in:
```
subagents/
├── conductor-analyzer.md
├── project-scaffolder.md
├── activity-generator.md
├── workflow-generator.md
├── infrastructure-generator.md
├── code-validator.md
├── workflow-executor.md
└── documentation-generator.md
```

When ready to use, copy or symlink to `.claude/agents/`.

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

[Specific common mistakes this agent must not make, from troubleshooting docs]

## Example

[Optional: Show example input/output for this agent]
```

### Invoking the Pipeline

Main agent workflow:

```python
# Main agent orchestrates the pipeline
user: "Convert the Conductor workflow to Temporal"

main_agent:
  1. Invoke conductor-analyzer sub-agent
  2. Wait for conductor-analysis.json
  3. Invoke project-scaffolder sub-agent
  4. Wait for package structure
  5. Invoke activity-generator sub-agent
  6. Wait for activities.py
  7. Invoke workflow-generator sub-agent
  8. Wait for workflow.py
  9. Invoke infrastructure-generator sub-agent
  10. Wait for worker.py, starter.py, and interact.py
  11. Invoke code-validator sub-agent
  12. If validation FAILS: halt and report errors
  13. If validation PASSES: invoke workflow-executor sub-agent
  14. Wait for execution results and WORKFLOW_EXECUTION_REPORT.md
  15. If execution FAILS: review errors, possibly re-run validator or other agents
  16. If execution PASSES: invoke documentation-generator
  17. Report completion to user with summary including execution results
```

### Error Handling

- **Agent 1-5** (Generators): If cannot proceed, write error to `MIGRATION_ERRORS.md` and halt
- **Agent 6** (Validator): Autonomously fix errors, re-validate, report unfixable errors
- **Agent 6.5** (Executor): Autonomously fix runtime errors, retry execution, report if unfixable
- **Agent 7** (Documentation): Always runs if executor passes (or if user decides to proceed despite execution failures)

### Context Window Management

Each sub-agent operates in its own context window, preventing pollution of the main conversation. Key benefits:

- **Analyzer** can read large Conductor JSON without bloating main context
- **Workflow Generator** can read all primitives documentation without impacting main agent
- **Validator** can read all generated code and run multiple validation passes
- Each agent returns concise summary to main agent

---

## Migration from Single-Agent System

### Current Documentation Split

The comprehensive `conductor-migration/` documentation will be referenced by sub-agents as follows:

| Documentation File | Primary Readers |
|--------------------|-----------------|
| `conductor-migration-guide.md` | All agents (high-level process) |
| `conductor-primitives-reference.md` | Analyzer, Activity Generator, **Workflow Generator** (critical) |
| `conductor-human-interaction.md` | Analyzer, **Workflow Generator** (critical) |
| `conductor-architecture.md` | Analyzer, Workflow Generator |
| `conductor-quality-assurance.md` | **Code Validator** (critical) |
| `conductor-troubleshooting.md` | Code Validator, all generators (pitfall awareness) |
| `AGENTS.md` | All agents (reference implementations) |

### Testing the Pipeline

Test with the example workflow:
```bash
# Provided: conductor-definition/EXAMPLE_review_approval.json
# Complex workflow with DO_WHILE + FORK_JOIN + nested SWITCH + HUMAN_TASK

# Expected output:
review_approval_temporal/
├── __init__.py
├── shared.py
├── activities.py
├── workflow.py
├── worker.py
└── starter.py

# Plus documentation and validation report
```

---

## Advantages Over Single-Agent Approach

1. **Focused Expertise**: Each agent specializes in one phase
2. **Context Efficiency**: Sub-agents have their own context windows
3. **Parallel Potential**: Future optimization could parallelize independent generators
4. **Error Isolation**: Validation catches issues before documentation phase
5. **Maintainability**: Easy to update one agent without affecting others
6. **Scalability**: Can add new agents (e.g., "performance-optimizer", "test-generator") without restructuring

---

## Next Steps

1. **Implement each sub-agent** by creating markdown files in `subagents/` directory
2. **Split AGENTS.md guidance** into relevant sub-agent system prompts
3. **Test pipeline** with EXAMPLE_review_approval.json
4. **Iterate** based on results
5. **Optimize** workflow generator (most complex, may need decomposition)

---

## Notes

- **Workflow Generator** is the most complex and critical agent - may need most iteration
- **Code Validator** must have autonomy to fix issues without human intervention
- **conductor-analysis.json** schema may evolve as agents reveal additional needs
- Consider adding **test-generator** agent in future for creating pytest test suites
- All agents should follow user's global Python standards (type hints, pytest, ruff, mypy strict)

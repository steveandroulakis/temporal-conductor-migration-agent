# Temporal Conductor Migration Agent

## Project Purpose

This project is a **Claude Code-powered migration system** that automatically converts Netflix Conductor workflow definitions (JSON-based orchestration) to Temporal Python SDK projects (code-based orchestration).

### What It Does

Given a Conductor JSON workflow definition, this system:
1. Analyzes the workflow structure, control flow, and task dependencies
2. Generates a complete, production-ready Temporal Python project with:
   - Type-safe dataclasses for workflow inputs/outputs
   - Activity implementations with proper error handling
   - Workflow orchestration with correct control flow translation
   - Worker and starter scripts for execution
   - Comprehensive documentation and setup scripts
3. Validates all generated code for syntax, types, and Temporal compliance
4. Produces migration documentation with side-by-side comparisons

### Why This Exists

Conductor and Temporal are both workflow orchestration systems, but they use fundamentally different approaches:
- **Conductor**: JSON-based workflow definitions with runtime interpretation
- **Temporal**: Code-first workflows with compile-time type safety

Migrating between these systems requires deep understanding of:
- Conductor primitives (SIMPLE, HTTP, FORK_JOIN, SWITCH, DO_WHILE, DYNAMIC_FORK, SUB_WORKFLOW, HUMAN_TASK, WAIT)
- Temporal patterns (activities, workflows, signals, updates, queries)
- Control flow translation (JSON operators → Python constructs)
- Human-in-the-loop patterns (approvals, signals, updates)
- Temporal-specific constraints (workflow sandbox, deterministic execution)

This project automates this complex translation using Claude Code's sub-agent architecture.

---

## Architecture: 8-Agent Sequential Pipeline

The migration system uses a **sequential pipeline** of 8 specialized Claude Code sub-agents. Each agent operates with high autonomy, performing a distinct phase of the migration process.

### Pipeline Overview

```
User provides Conductor JSON
         ↓
┌────────────────────────────────────────────────────────────────┐
│                    Main Claude Code Agent                      │
│              (Orchestrates pipeline execution)                 │
└────────────────────────────────────────────────────────────────┘
         ↓
    Sequential Pipeline Execution
         ↓
1. Conductor Analyzer
   └─> conductor-analysis.json
         ↓
2. Project Scaffolder
   └─> Package structure, shared.py, pyproject.toml
         ↓
3. Activity Generator
   └─> activities.py
         ↓
4. Workflow Generator (MOST COMPLEX)
   └─> workflow.py
         ↓
5. Infrastructure Generator
   └─> worker.py, starter.py, interact.py
         ↓
6. Code Validator
   └─> Validates & fixes → VALIDATION_REPORT.md
         ↓
6.5 Workflow Executor (NEW)
   └─> Runs & validates → WORKFLOW_EXECUTION_REPORT.md
         ↓
7. Documentation Generator
   └─> README.md, comparison docs, setup.sh
         ↓
    Complete Temporal Project
```

---

## Agent Specifications

### 1. Conductor Analyzer
**Role**: First agent - parses and deeply analyzes Conductor JSON

**Responsibilities**:
- Parse Conductor workflow JSON from `conductor-definition/` directory
- Extract workflow metadata (name, version, inputs, outputs)
- Analyze all tasks and identify types (SIMPLE, HTTP, FORK_JOIN, SWITCH, DO_WHILE, etc.)
- Map control flow patterns (sequential, parallel, conditional, loops)
- Identify human interaction patterns (HUMAN_TASK, WAIT, external data references)
- Analyze data flow and dependencies
- Calculate complexity (nesting depth, loops, parallelism)
- Generate structured `conductor-analysis.json`

**Key Output**: `conductor-analysis.json` - comprehensive analysis that all downstream agents depend on

**Model**: Inherit

---

### 2. Project Scaffolder
**Role**: Creates Python project structure and configuration

**Responsibilities**:
- Read `conductor-analysis.json` for requirements
- Create Python package directory structure
- Generate `shared.py` with dataclasses for:
  - Workflow input/output types
  - Activity-specific types
  - Human interaction data types
- Generate `pyproject.toml` with:
  - Package metadata
  - Dependencies (temporalio, httpx if needed, mypy)
  - **CRITICAL**: Console script definitions with `[tool.uv]` section
- Create `.gitignore`, `__init__.py`
- Create placeholder files for next agents

**Key Output**: Complete project structure with shared types

**Model**: Inherit

---

### 3. Activity Generator
**Role**: Translates Conductor tasks to Temporal activities

**Responsibilities**:
- Identify which Conductor tasks become activities (SIMPLE, HTTP)
- Generate `@activity.defn` functions with:
  - Complete type hints
  - Comprehensive docstrings
  - Activity logging
  - Timeout/retry recommendations
- Translate HTTP tasks to use `httpx.AsyncClient()`
- Update `shared.py` with additional dataclasses if needed

**Key Output**: `activities.py` with all activity implementations

**Model**: Inherit

---

### 4. Workflow Generator (MOST COMPLEX)
**Role**: Translates Conductor control flow to Temporal Python workflow

**Responsibilities**:
- Create `@workflow.defn` class
- Translate ALL control flow patterns:
  - Sequential → `await` chain
  - FORK_JOIN → `asyncio.gather()`
  - SWITCH → `if/elif/else`
  - DO_WHILE → `while` loop (with continue-as-new)
  - DYNAMIC_FORK → list comprehension + `asyncio.gather()`
  - SUB_WORKFLOW → `workflow.execute_child_workflow()`
- Implement human interaction:
  - WAIT tasks → Signal + `workflow.wait_condition()`
  - HUMAN_TASK → Update/Signal with validation
- Configure activity execution with timeouts and retry policies
- **CRITICAL**: Ensure workflow sandbox compliance (import activities by name, not module)
- Handle nested control flow with helper methods
- Add workflow queries for status checking

**Key Output**: `workflow.py` with complete workflow implementation

**Model**: Sonnet (explicitly specified for complexity)

**Critical Considerations**:
- Workflow sandbox violations are the #1 error source
- RetryPolicy must be imported from `temporalio.common` (not `temporalio.workflow`)
- Activity argument counts must match function signatures
- Non-deterministic code forbidden in workflows

---

### 5. Infrastructure Generator
**Role**: Creates worker and starter execution infrastructure

**Responsibilities**:
- Generate `worker.py`:
  - Worker registration with workflows and activities
  - Connection to Temporal server
  - Logging and PID file management
  - **CRITICAL**: Synchronous `main()` for console script compatibility
- Generate `starter.py`:
  - Workflow execution client
  - Example input data generation
  - Display workflow URL
  - **CRITICAL**: Synchronous `main()` for console script compatibility
- Ensure task queue names match between worker and starter

**Key Output**: `worker.py` and `starter.py` ready for execution

**Model**: Inherit

**Critical Consideration**: Console scripts require synchronous `main()` functions, not async

---

### 6. Code Validator
**Role**: Validates all generated code and autonomously fixes issues

**Responsibilities**:
- Run syntax validation on all Python files
- Run type checking with `mypy --strict`
- Verify workflow sandbox compliance
- Check `pyproject.toml` configuration (`[tool.uv]` section present)
- Verify console script setup (synchronous main functions)
- Check activity argument counts
- Verify RetryPolicy imports
- **Autonomously fix issues** when found
- Re-validate after fixes
- Generate comprehensive validation report

**Key Output**: `VALIDATION_REPORT.md` with validation results and fixes applied

**Model**: Inherit

**Autonomous Behavior**: This agent FIXES issues, doesn't just report them. It will attempt up to 3 fix-and-revalidate rounds.

---

### 6.5 Workflow Executor
**Role**: Executes and validates the generated workflow end-to-end

**Responsibilities**:
- Check/start Temporal server (verify ports 7233/8233, start if needed)
- Install dependencies via `uv sync`
- Analyze workflow type (simple vs. interactive with handlers)
- Execute end-to-end test:
  - Start worker in background
  - Execute workflow via starter
  - For simple workflows: Wait for COMPLETED status
  - For interactive workflows: Send test interactions, verify responses
- Validate execution using Temporal CLI (`temporal workflow show`)
- Handle failures autonomously:
  - Parse error logs
  - Identify error types (imports, sandbox, activities)
  - Invoke other agents to fix (code-validator, infrastructure-generator)
  - Retry execution up to 3 times
- Cleanup processes and PID files
- Generate `WORKFLOW_EXECUTION_REPORT.md`

**Key Output**: `WORKFLOW_EXECUTION_REPORT.md` with execution results, logs, and any fixes applied

**Model**: Inherit

**Critical Consideration**: This agent proves the workflow works before documentation claims it does. Uses techniques from `tmp-workflow-running-guide.md` for all Temporal CLI operations.

**Autonomous Behavior**: This agent RUNS the workflow and FIXES issues found during execution. Up to 3 retry rounds with autonomous fixes.

---

### 7. Documentation Generator
**Role**: Final agent - creates comprehensive documentation

**Responsibilities**:
- Generate comprehensive `README.md`:
  - Project overview (migrated from Conductor)
  - Prerequisites and setup instructions
  - Running instructions (worker and starter)
  - Human interaction guide (if applicable)
  - Configuration options
  - Troubleshooting section
- Generate `CONDUCTOR_COMPARISON.md`:
  - Side-by-side Conductor JSON vs Temporal Python
  - Task type mappings with actual code
  - Control flow translation examples
- Generate `CONDUCTOR_MIGRATION_NOTES.md`:
  - Migration decisions and rationale
  - Assumptions made
  - Customization recommendations
- Create executable `setup.sh` script:
  - Dependency installation
  - Validation commands
  - Success messages with next steps
- Generate package-level `README.md`

**Key Output**: Complete documentation suite for end users

**Model**: Inherit

---

## Communication Protocol

### Structured Document: conductor-analysis.json

All agents communicate through `conductor-analysis.json`, a structured analysis document created by Agent 1 and read by Agents 2-7 (plus 6.5).

**Schema includes**:
- `workflow_metadata`: Name, version, description, inputs, outputs
- `project_config`: Derived project name, package name, task queue
- `tasks`: Complete analysis of each Conductor task
- `human_interaction_patterns`: Identified approval/wait patterns
- `control_flow_summary`: Complexity assessment
- `recommended_patterns`: Implementation guidance

This document serves as the "single source of truth" for the entire pipeline.

---

## Agent Autonomy & Decision-Making

### High Autonomy Design

Each agent operates with **high autonomy**:
- Makes implementation decisions independently
- Reads comprehensive documentation for self-education
- Fixes issues without asking the main agent
- Documents decisions and assumptions

### Documentation-Driven Agents

All agents have access to comprehensive migration documentation:
- `conductor-migration/conductor-migration-guide.md` - Phase-by-phase migration process
- `conductor-migration/conductor-primitives-reference.md` - Complete Conductor→Temporal task mapping
- `conductor-migration/conductor-human-interaction.md` - Signals vs Updates, approval patterns
- `conductor-migration/conductor-architecture.md` - Architectural differences
- `conductor-migration/conductor-quality-assurance.md` - Validation procedures
- `conductor-migration/conductor-troubleshooting.md` - Common issues and solutions
- `AGENTS.md` - Python development standards and reference implementations

Agents read relevant documentation before starting work, enabling informed decisions.

---

## Critical Pitfalls & Solutions

The system is designed to avoid common migration errors:

### Workflow Sandbox Violations
**Problem**: Importing activity modules with non-deterministic code (httpx, random, etc.)
**Solution**: Workflow Generator imports activities by name only: `from .activities import activity1, activity2`

### Wrong RetryPolicy Import
**Problem**: Importing from `temporalio.workflow` instead of `temporalio.common`
**Solution**: Workflow Generator uses correct import, Code Validator checks and fixes

### Console Script Async Main
**Problem**: `async def main()` causes "coroutine was never awaited" errors
**Solution**: Infrastructure Generator creates synchronous `main()` wrapping async functions

### Missing [tool.uv] Configuration
**Problem**: Console scripts not found without `package = true`
**Solution**: Project Scaffolder includes this section, Code Validator verifies it

### Activity Argument Count Mismatches
**Problem**: Passing wrong number of arguments to activities
**Solution**: Code Validator checks function signatures against execute_activity calls

---

## Quality Standards

### Generated Code Quality

All generated code meets strict standards:
- **Type hints**: Complete type annotations (mypy --strict compliance)
- **Docstrings**: Comprehensive documentation for all functions
- **Error handling**: Proper exception handling in activities
- **Logging**: Activity and workflow logging for debugging
- **Timeouts**: All activities have appropriate timeouts
- **Retry policies**: Configured based on Conductor task settings

### Migration Faithfulness

The system preserves Conductor workflow semantics:
- Control flow execution order maintained
- Data passing patterns preserved
- Human interaction patterns correctly translated
- Error handling behavior replicated
- Nested structures handled with helper methods

---

## Usage Workflow

### For End Users

1. **Prepare Conductor JSON**: Place workflow definition in `conductor-definition/` directory
2. **Run migration command**: Execute Claude Code command (slash command) to start pipeline
3. **Wait for completion**: Pipeline executes autonomously through all 7 agents
4. **Review generated project**: Complete Temporal Python project ready to customize
5. **Run setup**: Execute `./setup.sh` to install dependencies
6. **Start workflow**: Run `uv run worker` and `uv run starter`

### What Users Get

A complete Temporal Python project with:
- ✅ Type-safe Python code (mypy --strict compliant)
- ✅ All activities implemented (with TODOs for business logic)
- ✅ Workflow with correct control flow
- ✅ Worker and starter scripts
- ✅ Comprehensive documentation
- ✅ Automated setup script
- ✅ Validation report
- ✅ Migration notes and comparison guide

### Customization Required

Users need to:
1. **Implement activity business logic**: Replace TODO placeholders in `activities.py`
2. **Customize workflow input**: Update example data in `starter.py`
3. **Adjust timeouts**: Tune based on actual performance
4. **Add tests**: Create unit and integration tests
5. **Configure production settings**: Update Temporal server addresses

---

## Technical Details

### Dependencies

Generated projects use:
- **Python 3.11+**: Modern Python with async/await
- **temporalio**: Temporal Python SDK (≥1.5.0)
- **httpx**: Async HTTP client (if HTTP tasks present)
- **mypy**: Type checking (≥1.7.0)
- **uv**: Fast Python package manager

### Project Structure

Generated projects follow this structure:
```
{workflow_name}_temporal/
├── __init__.py
├── shared.py          # Dataclasses
├── activities.py      # Activity implementations
├── workflow.py        # Workflow orchestration
├── worker.py          # Worker registration
└── starter.py         # Workflow starter

pyproject.toml         # Package configuration
setup.sh               # Automated setup
README.md              # Main documentation
CONDUCTOR_COMPARISON.md    # Migration comparison
CONDUCTOR_MIGRATION_NOTES.md  # Migration decisions
VALIDATION_REPORT.md   # Code validation results
.gitignore
```

### Console Scripts

Projects use UV console scripts for easy execution:
- `uv run worker` - Start the Temporal worker
- `uv run starter` - Execute the workflow

Configured in `pyproject.toml`:
```toml
[project.scripts]
worker = "package.worker:main"
starter = "package.starter:main"

[tool.uv]
package = true  # CRITICAL for console scripts to work
```

---

## Extending the Pipeline

### Adding New Agents

To add new agents to the pipeline:
1. Create new agent markdown file with YAML frontmatter
2. Define clear input/output contract
3. Specify which documentation to reference
4. Define success criteria and verification commands
5. Document critical pitfalls specific to that phase

### Potential Future Agents

Consider adding:
- **Test Generator**: Create pytest test suites for activities and workflows
- **Performance Optimizer**: Analyze and optimize activity batching, worker scaling
- **Monitoring Generator**: Add observability and custom metrics
- **UI Generator**: Create approval UI for human-in-the-loop workflows

---

## Key Advantages

### Over Manual Migration

- **Speed**: Complete migration in minutes vs hours/days
- **Consistency**: Same quality standards applied every time
- **Completeness**: Never forgets validation, documentation, or error handling
- **Best practices**: Built-in knowledge of Temporal patterns and pitfalls

### Over Simple Code Generation

- **Deep analysis**: Understands workflow complexity and nesting
- **Autonomous fixing**: Validates and fixes issues without manual intervention
- **Documentation-driven**: Agents self-educate from comprehensive guides
- **Quality assurance**: Multi-stage validation ensures working code

### Sequential Pipeline Benefits

- **Focused expertise**: Each agent specializes in one phase
- **Context efficiency**: Each agent has its own context window
- **Error isolation**: Validation catches issues before documentation
- **Maintainability**: Easy to update one agent without affecting others
- **Transparent progress**: Clear pipeline stages for user visibility

---

## Success Metrics

A successful migration produces:
- ✅ **Syntax-valid code**: All Python files compile without errors
- ✅ **Type-safe code**: mypy --strict passes with zero errors
- ✅ **Sandbox-compliant workflow**: No non-deterministic imports
- ✅ **Executable project**: Worker and starter run without errors
- ✅ **Complete documentation**: README, comparison guide, migration notes
- ✅ **Automated setup**: One-command installation via setup.sh

---

## Notes for Claude Code Development

### Agent Invocation

Agents are invoked sequentially by the main Claude Code agent using the Task tool with appropriate sub-agent names.

### Agent Context

Each agent receives:
- Full conversation history before invocation (has access to current context)
- Access to all documentation files
- Ability to read, write, edit files
- Bash execution for validation commands

### Error Handling

Agents follow this error handling strategy:
1. **Try to fix**: Attempt autonomous repair when issues found
2. **Re-validate**: Verify fixes work
3. **Document**: Record all fixes in reports
4. **Escalate**: After 3 attempts, report to main agent for manual intervention

### Reporting Back

Each agent reports concise summary to main agent:
- What was accomplished
- Key metrics (tasks analyzed, activities generated, errors fixed)
- Status (PASS/FAIL)
- Next agent readiness

---

## Version Information

**Migration System Version**: 1.0
**Claude Code Version**: Latest (as of deployment)
**Temporal Python SDK**: ≥1.5.0
**Python**: ≥3.11

---

**Last Updated**: November 2024
**Maintained by**: Temporal Migration Team

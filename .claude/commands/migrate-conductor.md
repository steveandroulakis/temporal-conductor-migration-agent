---
description: Migrate a Netflix Conductor workflow JSON to a complete Temporal Python project
---

You are orchestrating the Conductor-to-Temporal migration pipeline described in CLAUDE.md.

## Task

Execute the 8-agent sequential pipeline to migrate the Conductor workflow to Temporal:

1. **conductor-analyzer**: Analyze the Conductor JSON and create conductor-analysis.json
2. **project-scaffolder**: Create Python package structure and shared types
3. **activity-generator**: Generate activities.py from Conductor tasks
4. **workflow-generator**: Generate workflow.py with control flow translation (use sonnet model)
5. **infrastructure-generator**: Generate worker.py, starter.py, and interact.py
6. **code-validator**: Validate all code, fix issues autonomously, generate VALIDATION_REPORT.md
7. **workflow-executor**: Execute workflow end-to-end, validate it works, generate WORKFLOW_EXECUTION_REPORT.md
8. **documentation-generator**: Generate README.md, comparison docs, setup.sh

## Input

Conductor JSON file location: `conductor-definition/` directory (locate the .json file automatically)

## Process

**Invoke each agent sequentially using the Task tool**, waiting for each to complete before starting the next. Each agent:
- Reads documentation autonomously (AGENTS.md, conductor-migration/)
- Makes decisions independently
- Reports completion with summary

**After all agents complete**, provide the user with:
- Location of generated Temporal project
- Summary of what was created
- Workflow execution results (from WORKFLOW_EXECUTION_REPORT.md)
- Next steps: run `./setup.sh`, then `uv run worker` and `uv run starter`

## Important

- **Do not duplicate logic** - agents have complete instructions in their definition files
- **Sequential execution** - each agent depends on previous outputs
- **Autonomous agents** - they make decisions, you orchestrate
- **workflow-generator uses sonnet model** - specify in Task tool invocation
- Let agents handle errors and fixing - they are designed for autonomy

Start the pipeline now.

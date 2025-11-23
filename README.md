# Temporal Conductor Migration Agent Template

**Automatically convert Netflix Conductor workflows to Temporal Python projects using Claude Code.**

**⚠️ NOTE:** This agent can run for 30+ minutes and cost many Anthropic tokens!

**⚠️ NOTE:** The agent will ask you to approve _many_ tools and code generations along the way. I would _never_ recommend doing this outside of a sandbox environment but _if you wanted to_, run `claude --dangerously-skip-permissions` to ensure the agent cooks without interruption 🍳.

[See this branch for an example of a migrated project](https://github.com/steveandroulakis/temporal-conductor-migration-agent/blob/claude_test2/PROJECT_README.md). Based off the Conductor [document approvals example](https://github.com/conductor-sdk/conductor-examples/tree/main/document_approvals).

## What the agent does

This Claude Code project provides a 8-agent sequential pipeline that:
1. Analyzes Conductor JSON workflow definitions
2. Generates complete, production-ready Temporal Python projects with:
   - Type-safe activities and workflows
   - Worker and starter scripts
   - Comprehensive documentation
   - Automated setup scripts
3. Validates all generated code, runs it, and autonomously fixes issues

## Quick Start

### Prerequisites
- [Claude Code](https://claude.ai/claude-code)
- Python 3.11+
- [UV package manager](https://github.com/astral-sh/uv)
- [Temporal CLI](https://temporal.io/download)

### Step 1: Create Your Repository

1. Click the **"Use this template"** button at the top of this repository
2. Give your new repository a name (e.g., `migrate-my-workflow`)
3. Clone your new repository locally

### Step 2: Add your Conductor Workflow
Place your Conductor JSON workflow in:
   ```bash
   cd conductor-definition
   # Add your Conductor workflow.json here
   # REPLACE the example json
   # ENSURE YOU HAVE A SINGLE JSON CONDUCTOR WORKFLOW IN THIS DIRECTORY
   ```

### Step 3: Run Migration Command
In Claude Code, execute:
```
/migrate-conductor # it will find any json in this directory and migrate it to Temporal
```

The pipeline will automatically:
- Analyze your Conductor workflow
- Generate a complete Temporal Python project
- Validate and fix any issues
- Create comprehensive documentation

### After Migration
Your generated project will include:
- `{workflow_name}_temporal/` - Complete Python package
- `setup.sh` - Automated setup script
- ...and comprehensive markdown documentation on running the project.

## Architecture

See [CLAUDE.md](./CLAUDE.md) for complete pipeline architecture and agent specifications.

## Documentation

- `CLAUDE.md` - Complete system architecture
- `AGENTS.md` - Python development standards
- `conductor-migration/` - Comprehensive migration guides
- `.claude/` - Subagents and migration command

## Future work
- Refinements to subagents (maybe speed it up a bit?)
- Test with many more conductor workflow types
- I should generate tests!
- Ensure the resulting docs aren't written all over the repo (better file organization)

---

**Generated projects are production-ready with type safety, error handling, and comprehensive documentation.**

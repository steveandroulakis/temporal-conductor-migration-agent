# Temporal Conductor Migration Agent

**Automatically convert Netflix Conductor workflows to Temporal Python projects using Claude Code.**

## What It Does

This Claude Code project provides a 7-agent sequential pipeline that:
1. Analyzes Conductor JSON workflow definitions
2. Generates complete, production-ready Temporal Python projects with:
   - Type-safe activities and workflows
   - Worker and starter scripts
   - Comprehensive documentation
   - Automated setup scripts
3. Validates all generated code and autonomously fixes issues

## Quick Start

### Prerequisites
- [Claude Code](https://claude.ai/claude-code)
- Python 3.11+
- [UV package manager](https://github.com/astral-sh/uv)
- [Temporal CLI](https://temporal.io/download)

### Setup
Place your Conductor JSON workflow in:
   ```bash
   mkdir -p conductor-definition
   # Add your workflow.json here
   ```

### Run Migration
In Claude Code, execute:
```
/migrate-conductor
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
- `README.md` - Setup and usage instructions
- `CONDUCTOR_COMPARISON.md` - Side-by-side migration guide
- `VALIDATION_REPORT.md` - Code quality report

Run the generated project:
```bash
./setup.sh              # Install dependencies
uv run worker           # Start Temporal worker
uv run starter          # Execute workflow
```

## Architecture

See [CLAUDE.md](./CLAUDE.md) for complete pipeline architecture and agent specifications.

## Documentation

- `CLAUDE.md` - Complete system architecture
- `AGENTS.md` - Python development standards
- `conductor-migration/` - Comprehensive migration guides
- `subagents/` - Individual agent specifications

---

**Generated projects are production-ready with type safety, error handling, and comprehensive documentation.**

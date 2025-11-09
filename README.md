# Temporal Conductor Migration Agent Template

This template repository helps you migrate Netflix Conductor workflows to the Temporal Python SDK using AI coding agents like Codex, Claude Code, or other web-based code writing tools.

## Purpose

The goal of this repository is to provide a structured environment where AI coding agents can automatically convert a Netflix Conductor workflow definition (JSON) into a working Temporal Python application.

**Key Features:**
- Uses AI agents to generate production-ready Temporal Python code
- Includes comprehensive migration guides and best practices
- Supports complex workflow patterns (loops, conditionals, parallel execution, human-in-the-loop)
- No internet access required - agents work entirely from local documentation
- Supports Temporal Python SDK only

## How to Use This Template

### Step 1: Create Your Repository

1. Click the **"Use this template"** button at the top of this repository
2. Give your new repository a name (e.g., `migrate-my-workflow`)
3. Clone your new repository locally

### Step 2: Add Your Conductor Workflow

1. Place your Conductor workflow JSON file in the `./conductor-definition/` directory
2. You can replace the example file (`EXAMPLE_review_approval.json`) or add your own alongside it
3. Commit and push your changes

### Step 3: Use an AI Coding Agent

Add your repository to one of these AI coding platforms:

- **[Codex](https://codex.com)** - Web-based AI coding assistant
- **[Claude Code](https://claude.ai/code)** - Anthropic's AI coding tool
- **GitHub Copilot Workspace** - GitHub's AI development environment
- Any other web-based code writing agent that can access repositories

### Step 4: Prompt the Agent

Once your repository is loaded in the AI agent, use this prompt:

```
Your goal is to create a Temporal Python SDK version of the Conductor workflow
in this repo (found inside `./conductor-definition`). There is a guide linked
from AGENTS.md as well as a Conductor migration guide in the conductor-migration/
directory. Please follow the migration guide carefully and create a complete,
working Temporal application.
```

The agent will:
- Analyze your Conductor workflow JSON
- Read the migration guides in `conductor-migration/`
- Follow the instructions in `AGENTS.md`
- Generate Python code for activities, workflows, workers, and starters
- Create proper project structure with dependencies
- Handle complex patterns like human-in-the-loop, loops, and parallel execution

### Step 5: Review and Test

The AI agent will typically create a Pull Request with the generated code. To fetch and review:

```bash
# Clone your repository if you haven't already
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>

# Fetch the PR created by the agent (example branch name)
git fetch origin codex/create-temporal-python-sdk-for-conductor-workflow
git checkout codex/create-temporal-python-sdk-for-conductor-workflow

# Review the generated code
# The agent should have created:
# - activities.py (activity definitions)
# - workflows.py (workflow logic)
# - worker.py (worker configuration)
# - starter.py (workflow starter)
# - pyproject.toml (dependencies)
```

## What's Included

- **`AGENTS.md`** - Comprehensive instructions for AI agents performing the migration
- **`conductor-definition/`** - Directory for your Conductor workflow JSON files
  - `EXAMPLE_review_approval.json` - Example complex workflow demonstrating approval loops, parallel reviews, and human interaction
- **`conductor-migration/`** - Complete migration guide documentation
  - `README.md` - Migration guide entry point
  - `conductor-migration-guide.md` - 8-phase migration process
  - `conductor-primitives-reference.md` - Detailed Conductor→Temporal mappings
  - `conductor-human-interaction.md` - Human-in-the-loop patterns
  - `conductor-architecture.md` - Architecture comparison
  - `conductor-quality-assurance.md` - QA standards
  - `conductor-troubleshooting.md` - Common issues and solutions

## Important Notes

- **Python SDK Only**: This template supports Temporal Python SDK migrations only
- **No Internet Required**: The repository is self-contained. AI agents can complete the migration using only the documentation provided in this repo
- **No Execution**: This template focuses on code generation. The generated code is not executed in the repository - you'll need to test it in your own Temporal environment
- **Complex Workflows Supported**: The migration guides handle advanced patterns including:
  - DO_WHILE loops → Python while loops
  - FORK_JOIN → asyncio.gather for parallel execution
  - SWITCH statements → if/elif/else conditionals
  - HUMAN_TASK → Temporal Updates or Signals
  - WAIT → workflow.sleep
  - Dynamic forks and conditional branching

## Example Workflows

The included `EXAMPLE_review_approval.json` demonstrates:
- Multi-stage approval process
- DO_WHILE loop for retry-until-approved pattern
- Parallel review branches (FORK_JOIN)
- Nested SWITCH statements for complex conditional logic
- Human interaction points for approval gathering

## Support and Documentation

For detailed migration guidance, AI agents should:
1. Start with `AGENTS.md` for overall instructions
2. Follow `conductor-migration/README.md` for the migration process
3. Reference `conductor-primitives-reference.md` for specific task type mappings
4. Use `conductor-human-interaction.md` for workflows requiring human input

## Contributing

If you find issues with the migration guides or have suggestions for improvements, please open an issue in the original template repository.

## License

This template is provided as-is for educational and development purposes.

"""Workflow interaction client.

This client allows you to interact with running workflows:
- Execute Queries (for checking workflow status)

Note: This workflow is fully automated and does NOT have any Update or Signal handlers.
It processes security alerts end-to-end without human interaction.

Usage:
    # Execute a Query
    uv run interact query <workflow-id> <query-name>

Examples:
    # Check workflow status
    uv run interact query agentic-security-example-123 get_status
"""
import asyncio
import json
import sys
from typing import Any
from temporalio.client import Client

from .workflow import AgenticSecurityExampleWorkflow


async def execute_query(
    workflow_id: str,
    query_name: str
) -> None:
    """Execute a Query on a running workflow."""
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)

    print(f"Executing Query '{query_name}' on workflow {workflow_id}")

    try:
        if query_name == "get_status":
            result = await handle.query(
                AgenticSecurityExampleWorkflow.get_status
            )
            print(f"\n✓ Query result:")
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"❌ Unknown query: {query_name}", file=sys.stderr)
            print(f"Available queries: get_status", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"❌ Query failed: {e}", file=sys.stderr)
        sys.exit(1)


def print_usage() -> None:
    """Print usage instructions."""
    print("Usage: uv run interact <command> <workflow-id> [args...]")
    print("")
    print("Commands:")
    print("  query <workflow-id> <query-name>")
    print("")
    print("Available Queries:")
    print("  get_status:")
    print("    Get current workflow processing stage and statistics")
    print("    uv run interact query <wf-id> get_status")
    print("")
    print("Note: This workflow is fully automated with NO Updates or Signals.")
    print("      It processes security alerts without human interaction.")


def main() -> None:
    """Console script entry point."""
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    workflow_id = sys.argv[2]

    try:
        if command == "query":
            if len(sys.argv) < 4:
                print("Error: Query requires query-name", file=sys.stderr)
                print_usage()
                sys.exit(1)
            query_name = sys.argv[3]
            asyncio.run(execute_query(workflow_id, query_name))

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            print("Note: This workflow only supports 'query' (no updates or signals)", file=sys.stderr)
            print_usage()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

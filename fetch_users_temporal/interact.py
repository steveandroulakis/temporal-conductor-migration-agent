"""Workflow interaction client.

This workflow does not define any Signal or Update handlers beyond the standard
get_status Query. The workflow is fully automated with no human interaction points.

For workflows with human-in-the-loop patterns, this file would contain:
- Update handlers for approvals and decisions
- Signal handlers for notifications
- Query handlers for status checking

Available Queries:
- get_status: Returns current workflow status and description

Usage:
    # Query workflow status
    uv run interact query <workflow-id> get_status

Example:
    uv run interact query fetch_users-abc123 get_status
"""
import asyncio
import json
import sys
from typing import Any
from temporalio.client import Client

from .workflow import FetchUsersWorkflow


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
                FetchUsersWorkflow.get_status
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
    print("    uv run interact query <workflow-id> get_status")
    print("")
    print("Note: This workflow has no Signal or Update handlers.")
    print("It is a fully automated workflow with no human interaction.")


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
            print("This workflow only supports 'query' command (no signals or updates).")
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

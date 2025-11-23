"""Workflow interaction client.

This client allows you to interact with running workflows via:
- Queries (for checking workflow status)

Note: This workflow (CheckAddress) has minimal interaction patterns.
It only defines a status query and no Signal or Update handlers,
as it is a straightforward request-response workflow without human interaction.

Usage:
    # Query workflow status
    uv run interact query <workflow-id> get_status

Example:
    uv run interact query check-address-abc123 get_status
"""
import asyncio
import json
import sys
from temporalio.client import Client

from check_address_temporal.workflow import CheckAddressWorkflow


async def execute_query(workflow_id: str, query_name: str) -> None:
    """Execute a Query on a running workflow."""
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)

    print(f"Executing Query '{query_name}' on workflow {workflow_id}")

    try:
        if query_name == "get_status":
            result = await handle.query(CheckAddressWorkflow.get_status)
            print(f"\nQuery result:")
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"Unknown query: {query_name}", file=sys.stderr)
            print(f"Available queries: get_status", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Query failed: {e}", file=sys.stderr)
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
    print("    Returns the current status of the workflow")
    print("    uv run interact query <workflow-id> get_status")
    print("")
    print("Note: This workflow does not define Signal or Update handlers")
    print("      as it follows a simple request-response pattern without")
    print("      human interaction requirements.")


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

        elif command in ["update", "signal"]:
            print(f"Error: This workflow does not support {command}s", file=sys.stderr)
            print("The CheckAddress workflow is a simple request-response workflow")
            print("without human interaction patterns (no Signals or Updates).")
            sys.exit(1)

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
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

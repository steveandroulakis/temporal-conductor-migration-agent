"""Workflow interaction client.

This client allows you to interact with running workflows:
- Send Updates (for cart updates and checkout confirmation)
- Execute Queries (for checking workflow status)

Usage:
    # Send a cart update during shopping
    uv run interact update <workflow-id> update_cart '{"cart": "shopping", "cart_items": "item1, item2, item3, item4"}'

    # Move to checkout
    uv run interact update <workflow-id> update_cart '{"cart": "checkout", "cart_items": "item1, item2"}'

    # Confirm successful checkout
    uv run interact update <workflow-id> confirm_checkout '{"success": "success"}'

    # Confirm failed checkout (will reset to shopping)
    uv run interact update <workflow-id> confirm_checkout '{"success": "checkout_failed"}'

    # Query workflow status
    uv run interact query <workflow-id> get_cart_status

Examples:
    # Complete workflow flow:
    # 1. Start workflow (in another terminal: uv run starter)
    # 2. Add items to cart:
    uv run interact update shopping-cart-abc123 update_cart '{"cart": "shopping", "cart_items": "apple, banana, orange"}'

    # 3. Move to checkout:
    uv run interact update shopping-cart-abc123 update_cart '{"cart": "checkout", "cart_items": "apple, banana"}'

    # 4. Confirm checkout success:
    uv run interact update shopping-cart-abc123 confirm_checkout '{"success": "success"}'

    # Check status at any time:
    uv run interact query shopping-cart-abc123 get_cart_status
"""
import asyncio
import json
import sys
from typing import Any
from temporalio.client import Client

from .workflow import ShoppingCartWorkflow
from .shared import CartUpdate, CheckoutConfirmation, CheckoutConfirmationResult


async def send_update(
    workflow_id: str,
    update_name: str,
    args: dict[str, Any]
) -> None:
    """Send an Update to a running workflow."""
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)

    print(f"Sending Update '{update_name}' to workflow {workflow_id}")
    print(f"Arguments: {json.dumps(args, indent=2)}")

    try:
        if update_name == "update_cart":
            # Update cart during shopping phase
            cart_update = CartUpdate(**args)
            result = await handle.execute_update(
                ShoppingCartWorkflow.update_cart,
                cart_update
            )
            print(f"\n{chr(10003)} Update accepted!")
            print(f"Status: {result.status}")
            print(f"Message: {result.message}")
            print(f"Current cart: {result.current_cart}")
            print(f"Current items: {result.current_items}")

        elif update_name == "confirm_checkout":
            # Confirm checkout completion
            confirmation = CheckoutConfirmation(**args)
            checkout_result: CheckoutConfirmationResult = await handle.execute_update(
                ShoppingCartWorkflow.confirm_checkout,
                confirmation
            )
            print(f"\n{chr(10003)} Update accepted!")
            print(f"Status: {checkout_result.status}")
            print(f"Message: {checkout_result.message}")
            print(f"Checkout status: {checkout_result.checkout_status}")

        else:
            print(f"{chr(10005)} Unknown update: {update_name}", file=sys.stderr)
            print(f"Available updates: update_cart, confirm_checkout", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"{chr(10005)} Update failed: {e}", file=sys.stderr)
        sys.exit(1)


async def execute_query(
    workflow_id: str,
    query_name: str
) -> None:
    """Execute a Query on a running workflow."""
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)

    print(f"Executing Query '{query_name}' on workflow {workflow_id}")

    try:
        if query_name == "get_cart_status":
            result = await handle.query(
                ShoppingCartWorkflow.get_cart_status
            )
            print(f"\n{chr(10003)} Query result:")
            print(json.dumps(result, indent=2, default=str))

        else:
            print(f"{chr(10005)} Unknown query: {query_name}", file=sys.stderr)
            print(f"Available queries: get_cart_status", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"{chr(10005)} Query failed: {e}", file=sys.stderr)
        sys.exit(1)


def print_usage() -> None:
    """Print usage instructions."""
    print("Usage: uv run interact <command> <workflow-id> [args...]")
    print("")
    print("Commands:")
    print("  update <workflow-id> <update-name> <json-args>")
    print("  query <workflow-id> <query-name>")
    print("")
    print("Available Updates:")
    print("")
    print("  update_cart:")
    print("    Send cart updates during shopping phase")
    print("    Arguments: {\"cart\": \"shopping|checkout\", \"cart_items\": \"item1, item2, ...\"}")
    print("")
    print("    Example - Add items while shopping:")
    print("      uv run interact update <wf-id> update_cart '{\"cart\": \"shopping\", \"cart_items\": \"apple, banana, orange\"}'")
    print("")
    print("    Example - Move to checkout:")
    print("      uv run interact update <wf-id> update_cart '{\"cart\": \"checkout\", \"cart_items\": \"apple, banana\"}'")
    print("")
    print("  confirm_checkout:")
    print("    Confirm checkout completion after sub-workflow")
    print("    Arguments: {\"success\": \"success|checkout_failed\"}")
    print("")
    print("    Example - Successful checkout:")
    print("      uv run interact update <wf-id> confirm_checkout '{\"success\": \"success\"}'")
    print("")
    print("    Example - Failed checkout (reset to shopping):")
    print("      uv run interact update <wf-id> confirm_checkout '{\"success\": \"checkout_failed\"}'")
    print("")
    print("Available Queries:")
    print("")
    print("  get_cart_status:")
    print("    Get current cart status without modifying workflow")
    print("")
    print("    Example:")
    print("      uv run interact query <wf-id> get_cart_status")
    print("")
    print("Complete Workflow Example:")
    print("  1. Start worker:         uv run worker")
    print("  2. Start workflow:       uv run starter")
    print("  3. Add items:            uv run interact update <wf-id> update_cart '{\"cart\": \"shopping\", \"cart_items\": \"apple\"}'")
    print("  4. Check status:         uv run interact query <wf-id> get_cart_status")
    print("  5. Go to checkout:       uv run interact update <wf-id> update_cart '{\"cart\": \"checkout\", \"cart_items\": \"apple\"}'")
    print("  6. Confirm checkout:     uv run interact update <wf-id> confirm_checkout '{\"success\": \"success\"}'")


def main() -> None:
    """Console script entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    # Handle help flag
    if sys.argv[1] in ["-h", "--help", "help"]:
        print_usage()
        sys.exit(0)

    if len(sys.argv) < 3:
        print("Error: Missing workflow-id", file=sys.stderr)
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    workflow_id = sys.argv[2]

    try:
        if command == "update":
            if len(sys.argv) < 5:
                print("Error: Update requires update-name and json-args", file=sys.stderr)
                print_usage()
                sys.exit(1)
            update_name = sys.argv[3]
            args = json.loads(sys.argv[4])
            asyncio.run(send_update(workflow_id, update_name, args))

        elif command == "query":
            if len(sys.argv) < 4:
                print("Error: Query requires query-name", file=sys.stderr)
                print_usage()
                sys.exit(1)
            query_name = sys.argv[3]
            asyncio.run(execute_query(workflow_id, query_name))

        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            print_usage()
            sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

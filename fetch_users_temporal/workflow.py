"""Workflow definition for fetch_users workflow.

This workflow is migrated from Conductor workflow: fetch_users (version 11).

Control Flow:
This is a simple sequential data pipeline workflow:
1. fetch_users: HTTP GET request to JSONPlaceholder API
2. jq_filter_users: Filter users whose name starts with 'C'
3. Return filtered user list as workflow output

Original Conductor workflow: conductor-definition/OSS_HTTP_workflow_example.json
Complexity: LOW (simple sequential workflow with 2 tasks)
Max nesting depth: 0
"""
import asyncio
from datetime import timedelta
from typing import Dict, Any, List
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

# Import shared dataclasses with workflow sandbox safety
with workflow.unsafe.imports_passed_through():
    from .shared import (
        WorkflowInput,
        WorkflowOutput,
    )
    # CRITICAL: Import activities by name only (not module) for sandbox compliance
    # activities.py contains httpx import which is non-deterministic
    from .activities import (
        fetch_users,
        jq_filter_users,
    )


# Default retry policy for activities with potential transient failures
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)


@workflow.defn
class FetchUsersWorkflow:
    """Temporal workflow migrated from Conductor workflow: fetch_users.

    This workflow fetches user data from the JSONPlaceholder API and filters
    it to only include users whose name starts with the letter 'C'.

    Control Flow:
    This is a simple sequential data pipeline with no branching, loops, or
    parallel execution:

    1. HTTP Task (fetch_users_ref):
       - GET request to https://jsonplaceholder.typicode.com/users
       - Returns list of user objects with status code and headers
       - Network operation with retry policy for transient failures

    2. JSON_JQ_TRANSFORM Task (jq_filter_users_ref):
       - Filters user list based on name pattern
       - Original JQ expression: [.users[] | select(.name | test("^C"))]
       - Translated to Python regex filtering

    3. Workflow Output:
       - Returns filtered user list
       - Output field: users

    Original Conductor workflow: OSS_HTTP_workflow_example.json
    Complexity: LOW
    - Simple sequential workflow with only 2 tasks
    - No conditional branching
    - No loops or iterations
    - No parallel execution
    - Straightforward data pipeline: fetch → transform → output

    Human Interaction: None (fully automated workflow)

    Data Flow:
    - Conductor: ${fetch_users_ref.output.response.body}
    - Temporal: fetch_result["body"] (direct Python dict access)
    """

    def __init__(self) -> None:
        """Initialize workflow state.

        This workflow has no complex state management as it's a simple
        sequential pipeline. No instance variables needed for human
        interaction or status tracking.
        """
        pass

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        """Execute the fetch_users workflow.

        This workflow demonstrates a simple data pipeline pattern:
        fetch data from external API, transform it, and return results.

        Args:
            input: Workflow input parameters. Note: Original Conductor workflow
                   has no input parameters, but we maintain the input dataclass
                   for consistency and future extensibility.

        Returns:
            WorkflowOutput containing:
                - users: List of user dictionaries matching the filter criteria
                         (names starting with 'C')

        Raises:
            ApplicationError: On unrecoverable business logic failures
            ActivityError: If activities fail after retry attempts exhausted

        Workflow Execution:
            1. Fetch users from JSONPlaceholder API (HTTP GET)
            2. Filter users by name pattern (starts with 'C')
            3. Return filtered list
        """
        workflow.logger.info("Starting fetch_users workflow")

        # Task 1: fetch_users (HTTP task)
        # Original Conductor task: fetch_users_ref
        # HTTP GET to https://jsonplaceholder.typicode.com/users
        workflow.logger.info("Executing fetch_users HTTP activity")

        fetch_result: Dict[str, Any] = await workflow.execute_activity(
            fetch_users,
            # Activity accepts 2 parameters: uri and method (both have defaults)
            # We'll use defaults, so no args needed
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=5,  # Network operations need more retries
                backoff_coefficient=2.0,
            ),
        )

        workflow.logger.info(
            f"fetch_users completed with status code: {fetch_result['status_code']}"
        )

        # Extract users list from HTTP response body
        # Conductor reference: ${fetch_users_ref.output.response.body}
        # The API returns a list of users directly in the response body
        users_list: List[Dict[str, Any]] = fetch_result["body"]

        workflow.logger.info(f"Fetched {len(users_list)} users from API")

        # Task 2: jq_filter_users (JSON_JQ_TRANSFORM task)
        # Original Conductor task: jq_filter_users_ref
        # Original JQ expression: [.users[] | select(.name | test("^C"))]
        # Filters to users whose name starts with 'C'
        workflow.logger.info("Executing jq_filter_users filtering activity")

        filtered_users: List[Dict[str, Any]] = await workflow.execute_activity(
            jq_filter_users,
            args=[users_list, "^C"],  # 2 parameters: users list and name pattern
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=5),
                maximum_attempts=2,  # Pure computation, minimal retries needed
                backoff_coefficient=1.0,
            ),
        )

        workflow.logger.info(
            f"Filtering complete: {len(filtered_users)} users match pattern '^C'"
        )

        # Workflow output
        # Conductor output: { "users": "${jq_filter_users_ref.output}" }
        result = WorkflowOutput(users=filtered_users)

        workflow.logger.info(
            f"fetch_users workflow completed successfully with {len(filtered_users)} filtered users"
        )

        return result

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Query current workflow status.

        This query allows external systems to check the workflow state
        without modifying it.

        Returns:
            Dict containing:
                - workflow_type: Type identifier for this workflow
                - description: Human-readable description

        Note: This is a simple workflow with no complex state tracking.
              For workflows with human interaction or long-running loops,
              this query would return more detailed state information.
        """
        return {
            "workflow_type": "fetch_users",
            "description": "Sequential data pipeline: fetch users and filter by name",
        }

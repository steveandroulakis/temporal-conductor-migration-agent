"""Activity implementations.

This module contains activity functions migrated from Conductor tasks.
Each activity is decorated with @activity.defn and implements a specific
business operation or external service call.

Activities can:
- Perform I/O operations (file, network, database)
- Call external APIs and services
- Execute long-running computations
- Send notifications

Activities MUST NOT:
- Make workflow decisions (use workflows for orchestration)
- Directly call other activities (orchestrate through workflows)
"""
from typing import Dict, Any, List
import httpx
from temporalio import activity


@activity.defn
async def fetch_users(
    uri: str = "https://jsonplaceholder.typicode.com/users",
    method: str = "GET",
) -> Dict[str, Any]:
    """HTTP activity migrated from Conductor HTTP task: fetch_users.

    Fetches user data from JSONPlaceholder API via HTTP GET request.
    This activity performs an external HTTP call to retrieve a list of users.

    Args:
        uri: Target endpoint URL. Defaults to JSONPlaceholder users API.
        method: HTTP method to use. Defaults to "GET".

    Returns:
        Dict containing:
            - status_code: HTTP response status code (e.g., 200)
            - body: Response body parsed as JSON (list of user objects)
            - headers: Response headers as dictionary

    Recommended Configuration:
        - Timeout: 60 seconds (network operations require reasonable timeout)
        - Retry Policy: Exponential backoff for transient network failures
        - Maximum Attempts: 3-5 (HTTP requests can fail due to network issues)

    Raises:
        httpx.HTTPError: On network or HTTP protocol errors
        httpx.TimeoutException: On request timeout

    Original Conductor Task Reference: fetch_users_ref
    """
    activity.logger.info(f"HTTP {method} request to {uri}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=uri,
                timeout=60.0  # 60 second timeout
            )
            response.raise_for_status()  # Raise exception for 4xx/5xx status codes

            # Parse response body as JSON
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                response_body = response.json()
            else:
                response_body = response.text

            result = {
                "status_code": response.status_code,
                "body": response_body,
                "headers": dict(response.headers)
            }

            activity.logger.info(
                f"HTTP request completed successfully: {response.status_code}"
            )
            return result

        except httpx.TimeoutException as e:
            activity.logger.error(f"HTTP request timeout: {uri}")
            raise
        except httpx.HTTPError as e:
            activity.logger.error(f"HTTP request failed: {e}")
            raise


@activity.defn
async def jq_filter_users(
    users: List[Dict[str, Any]],
    name_pattern: str = "^C"
) -> List[Dict[str, Any]]:
    """JSON filtering activity migrated from Conductor JSON_JQ_TRANSFORM task: jq_filter_users.

    Filters user list to only include users whose name starts with specified pattern.
    This is a pure data transformation activity that translates the JQ expression
    '[.users[] | select(.name | test("^C"))]' to Python list comprehension.

    Business Logic:
    - Takes a list of user objects (from HTTP response)
    - Filters based on name field matching a regex pattern
    - Returns filtered list of users

    Args:
        users: List of user dictionaries to filter. Each user should have
               a 'name' field. Expected structure from JSONPlaceholder API:
               [{"id": 1, "name": "Clementine Bauch", ...}, ...]
        name_pattern: Regex pattern for filtering user names. Defaults to "^C"
                     which matches names starting with 'C'. Can be customized
                     to other patterns like "^A", "Smith$", etc.

    Returns:
        List[Dict[str, Any]]: Filtered list of user dictionaries matching the pattern.
                             Structure is identical to input, just filtered.

    Recommended Configuration:
        - Timeout: 10 seconds (in-memory data processing, should be fast)
        - Retry Policy: Fixed retry with 2 attempts (pure computation, no external dependencies)
        - Maximum Attempts: 2

    Examples:
        Input: [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]
        Pattern: "^C"
        Output: [{"name": "Charlie"}]

        Input: [{"name": "Clementine Bauch"}, {"name": "Ervin Howell"}]
        Pattern: "^C"
        Output: [{"name": "Clementine Bauch"}]

    Original Conductor Task Reference: jq_filter_users_ref
    Original JQ Expression: [.users[] | select(.name | test("^C"))]
    """
    activity.logger.info(
        f"Filtering {len(users)} users with name pattern: {name_pattern}"
    )

    # Translate JQ expression to Python list comprehension
    # JQ: [.users[] | select(.name | test("^C"))]
    # Python: Filter users where name matches pattern
    import re

    pattern_regex = re.compile(name_pattern)
    filtered_users = [
        user for user in users
        if 'name' in user and pattern_regex.search(user['name'])
    ]

    activity.logger.info(
        f"Filtering complete: {len(filtered_users)} users match pattern '{name_pattern}'"
    )

    return filtered_users

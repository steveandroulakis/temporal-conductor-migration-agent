"""Activity implementations.

This module contains activity functions migrated from Conductor tasks.
Activities are decorated with @activity.defn and implement business operations
or external service calls.

WORKFLOW ANALYSIS: NO ACTIVITIES REQUIRED
==========================================

The shopping_cart workflow from Conductor contains NO tasks that translate
to Temporal activities. All tasks are control flow primitives that are
implemented directly in the workflow logic:

Conductor Task Types Present:
- SET_VARIABLE: Translates to Python variable assignments in workflow
- DO_WHILE: Translates to while loop in workflow
- WAIT: Translates to Update/Signal handlers in workflow
- SWITCH: Translates to if/elif/else logic in workflow
- SUB_WORKFLOW: Translates to workflow.execute_child_workflow()
- INLINE: Translates to direct Python code in workflow

Activity Generation Criteria:
Activities are ONLY generated for:
- SIMPLE tasks (worker-executed business logic)
- HTTP tasks (external API calls)
- Custom task types (domain-specific operations)

Since this workflow contains NONE of these task types, no activities
are needed. All logic is implemented in workflow.py as orchestration code.

If future iterations of this workflow require activities (e.g., calling
external services, database operations, file I/O), they should be added
to this file following this pattern:

Example Activity Pattern:
-----------------------
from temporalio import activity
from typing import Dict, Any

@activity.defn
async def example_activity(input_data: str) -> Dict[str, Any]:
    '''
    Activity description with business logic explanation.

    Args:
        input_data: Description of input parameter

    Returns:
        Dict containing result data

    Recommended Configuration:
        - Timeout: 30s
        - Retry Policy: 3 attempts with exponential backoff
    '''
    activity.logger.info(f"Processing: {input_data}")

    # Business logic here

    return {"status": "success", "data": input_data}
"""
from temporalio import activity  # noqa: F401

# No activities defined - this workflow uses only control flow primitives

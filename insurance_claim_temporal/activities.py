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
from typing import Dict, Any
from temporalio import activity

from insurance_claim_temporal.shared import (
    FindPolicyInput,
    FindPolicyOutput,
    Policy,
    CreateClaimInput,
)


@activity.defn
async def find_policy_for_customer(input_data: FindPolicyInput) -> FindPolicyOutput:
    """Find customer insurance policies by first name and last name.

    Activity migrated from Conductor SIMPLE task: findPolicyForCustomer

    Business Logic:
    Queries the customer database to retrieve all insurance policies associated
    with a customer identified by their first and last name. This is the initial
    step in the claims process where we identify which policies the customer holds.

    Args:
        input_data: FindPolicyInput containing:
            - first_name: Customer's first name
            - last_name: Customer's last name

    Returns:
        FindPolicyOutput containing:
            - policies: List of Policy objects, each with:
                - policy_number: Unique policy identifier
                - policy_type: Type of policy (e.g., "AUTO", "HOME", "LIFE")

    Recommended Configuration:
        - Timeout: 30 seconds (database query should be fast)
        - Retry Policy: Exponential backoff with 3 attempts
        - Maximum Attempts: 3
        - Initial Interval: 1 second
        - Backoff Coefficient: 2.0
        - Non-retryable errors: Customer not found (if desired behavior)

    Raises:
        ValueError: If customer name is invalid or empty
        DatabaseError: If database query fails (will be retried)

    Original Conductor Task Reference: findPolicyForCustomer_ref

    TODO: Implement actual database query logic
    """
    activity.logger.info(
        f"Finding policies for customer: {input_data.first_name} {input_data.last_name}"
    )

    # Validate input
    if not input_data.first_name or not input_data.last_name:
        activity.logger.error("Invalid customer name provided")
        raise ValueError("First name and last name are required")

    # TODO: Replace with actual database query
    # Example: Query customer_policies table
    # SELECT policy_number, policy_type
    # FROM policies
    # WHERE customer_first_name = ? AND customer_last_name = ?
    # This is a placeholder implementation based on Conductor task configuration

    # Placeholder: Return sample policies for demonstration
    # In production, this would query a real database
    sample_policies = [
        Policy(
            policy_number="POL-AUTO-001",
            policy_type="AUTO"
        ),
        Policy(
            policy_number="POL-HOME-002",
            policy_type="HOME"
        ),
    ]

    activity.logger.info(
        f"Found {len(sample_policies)} policies for {input_data.first_name} {input_data.last_name}"
    )

    return FindPolicyOutput(policies=sample_policies)


@activity.defn
async def create_claim_for_policy(input_data: CreateClaimInput) -> Dict[str, Any]:
    """Persist a new insurance claim in the database for the given policy.

    Activity migrated from Conductor SIMPLE task: createClaimForPolicy

    Business Logic:
    Creates and persists a new insurance claim record in the database. This occurs
    after the customer has selected a valid policy and provided incident details.
    The claim is associated with the policy and includes the incident description.
    This is a critical transaction that must succeed for claim processing to continue.

    Args:
        input_data: CreateClaimInput containing:
            - policy_id: The policy number selected by the customer
            - description: Incident description provided by the customer

    Returns:
        Dict containing:
            - claim_id: Unique identifier for the newly created claim
            - status: Creation status (e.g., "created", "pending")
            - created_at: Timestamp of claim creation (ISO 8601 format)
            - policy_id: The policy this claim is associated with
            - message: Human-readable confirmation message

    Recommended Configuration:
        - Timeout: 45 seconds (database write with potential validations)
        - Retry Policy: Exponential backoff with 3 attempts
        - Maximum Attempts: 3
        - Initial Interval: 2 seconds
        - Backoff Coefficient: 2.0
        - Non-retryable errors: Invalid policy ID, duplicate claim

    Raises:
        ValueError: If policy_id is invalid or empty
        DatabaseError: If database write fails (will be retried)
        DuplicateClaimError: If claim already exists for this incident

    Original Conductor Task Reference: createClaimForPolicy_ref

    Implementation Notes:
    - This task is nested at level 1 inside the policy_valid SWITCH "yes" case
    - Only executed when the selected policy type is "AUTO"
    - Claim creation is a prerequisite for assessor evaluation
    - Consider adding idempotency checks to prevent duplicate claims

    TODO: Implement actual database insert logic with transaction handling
    """
    activity.logger.info(
        f"Creating claim for policy: {input_data.policy_id}"
    )

    # Validate input
    if not input_data.policy_id:
        activity.logger.error("Policy ID is required")
        raise ValueError("Policy ID cannot be empty")

    if not input_data.description or len(input_data.description.strip()) < 10:
        activity.logger.error("Incident description is too short")
        raise ValueError("Incident description must be at least 10 characters")

    # TODO: Replace with actual database transaction
    # Example: Insert into claims table
    # INSERT INTO claims (policy_id, incident_description, status, created_at)
    # VALUES (?, ?, 'pending', NOW())
    # RETURNING claim_id
    #
    # Consider:
    # - Validate policy_id exists in policies table
    # - Check for duplicate claims (same policy + similar description)
    # - Set initial claim status to "pending" or "under_review"
    # - Generate unique claim_id
    # - Store timestamp for audit trail

    # Placeholder implementation
    from datetime import datetime

    claim_id = f"CLM-{input_data.policy_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    result = {
        "claim_id": claim_id,
        "status": "created",
        "created_at": datetime.now().isoformat(),
        "policy_id": input_data.policy_id,
        "incident_description": input_data.description,
        "message": f"Claim {claim_id} successfully created for policy {input_data.policy_id}"
    }

    activity.logger.info(
        f"Successfully created claim {claim_id} for policy {input_data.policy_id}"
    )

    return result

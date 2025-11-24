"""Workflow interaction client.

This client allows you to interact with running workflows:
- Send Updates (for human approvals, decisions with validation)
- Execute Queries (for checking workflow status)

Usage:
    # Send an Update
    uv run interact update <workflow-id> <update-name> <json-args>

    # Execute a Query
    uv run interact query <workflow-id> <query-name>

Examples:
    # Submit initial claim
    uv run interact update insurance-claim-123 submit_claim '{"policy_picker": "POL-AUTO-001", "incident_description": "Car accident on Highway 101"}'

    # Submit assessor findings
    uv run interact update insurance-claim-123 submit_assessor_findings '{"visible_assesments": [{"damage_type": "Side collision Damage", "coverage_determination": "Covered", "coverage_score": 100}], "overall_coverage": "yes", "rationale": "Accident is covered under policy", "incident_city": "San Francisco", "incident_street": "123 Main St", "incident_state": "CA"}'

    # Submit investigation findings (for high-cost claims)
    uv run interact update insurance-claim-123 submit_investigation_findings '{"investigation_findings": "On-site investigation confirms no fraud detected", "witness_statements": ["Statement 1", "Statement 2"]}'

    # Query workflow status
    uv run interact query insurance-claim-123 get_status

    # Query claim details
    uv run interact query insurance-claim-123 get_claim_details

    # Query damage summary
    uv run interact query insurance-claim-123 get_damage_summary
"""
import asyncio
import json
import sys
from typing import Any
from temporalio.client import Client

from .workflow import InsuranceClaimWorkflow
from .shared import (
    ClaimSubmission,
    AssessorFindings,
    InvestigationFindings,
    DamageAssessment
)


async def send_update(
    workflow_id: str,
    update_name: str,
    args: dict[str, Any]
) -> None:
    """Send an Update to a running workflow."""
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle_for(
        InsuranceClaimWorkflow.run,
        workflow_id
    )

    print(f"Sending Update '{update_name}' to workflow {workflow_id}")
    print(f"Arguments: {json.dumps(args, indent=2)}")

    try:
        if update_name == "submit_claim":
            # Construct ClaimSubmission dataclass
            submission = ClaimSubmission(
                policy_picker=args["policy_picker"],
                incident_description=args["incident_description"]
            )
            result = await handle.execute_update(
                InsuranceClaimWorkflow.submit_claim,
                submission
            )
            print(f"\n✓ Update accepted!")
            print(f"Status: {result.status}")
            print(f"Message: {result.message}")

        elif update_name == "submit_assessor_findings":
            # Construct AssessorFindings dataclass with DamageAssessment list
            damage_assessments = [
                DamageAssessment(
                    damage_type=assessment["damage_type"],
                    coverage_determination=assessment["coverage_determination"],
                    coverage_score=assessment["coverage_score"]
                )
                for assessment in args["visible_assesments"]
            ]
            findings = AssessorFindings(
                visible_assesments=damage_assessments,
                overall_coverage=args["overall_coverage"],
                rationale=args["rationale"],
                incident_city=args["incident_city"],
                incident_street=args["incident_street"],
                incident_state=args["incident_state"]
            )
            result = await handle.execute_update(
                InsuranceClaimWorkflow.submit_assessor_findings,  # type: ignore[arg-type]
                findings
            )
            print(f"\n✓ Update accepted!")
            print(f"Status: {result.status}")
            print(f"Message: {result.message}")

        elif update_name == "submit_investigation_findings":
            # Construct InvestigationFindings dataclass
            investigation_findings_data = InvestigationFindings(
                investigation_findings=args["investigation_findings"],
                witness_statements=args.get("witness_statements")
            )
            result = await handle.execute_update(
                InsuranceClaimWorkflow.submit_investigation_findings,  # type: ignore[arg-type]
                investigation_findings_data
            )
            print(f"\n✓ Update accepted!")
            print(f"Status: {result.status}")
            print(f"Message: {result.message}")

        else:
            print(f"❌ Unknown update: {update_name}", file=sys.stderr)
            print(f"Available updates: submit_claim, submit_assessor_findings, submit_investigation_findings", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"❌ Update failed: {e}", file=sys.stderr)
        sys.exit(1)


async def execute_query(
    workflow_id: str,
    query_name: str
) -> None:
    """Execute a Query on a running workflow."""
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle_for(
        InsuranceClaimWorkflow.run,
        workflow_id
    )

    print(f"Executing Query '{query_name}' on workflow {workflow_id}")

    try:
        if query_name == "get_status":
            result = await handle.query(
                InsuranceClaimWorkflow.get_status
            )
            print(f"\n✓ Query result:")
            print(json.dumps(result, indent=2, default=str))

        elif query_name == "get_claim_details":
            result = await handle.query(
                InsuranceClaimWorkflow.get_claim_details  # type: ignore[call-overload]
            )
            print(f"\n✓ Query result:")
            print(json.dumps(result, indent=2, default=str))

        elif query_name == "get_damage_summary":
            result = await handle.query(
                InsuranceClaimWorkflow.get_damage_summary  # type: ignore[call-overload]
            )
            print(f"\n✓ Query result:")
            print(json.dumps(result, indent=2, default=str))

        else:
            print(f"❌ Unknown query: {query_name}", file=sys.stderr)
            print(f"Available queries: get_status, get_claim_details, get_damage_summary", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"❌ Query failed: {e}", file=sys.stderr)
        sys.exit(1)


def print_usage() -> None:
    """Print usage instructions."""
    print("Usage: uv run interact <command> <workflow-id> [args...]")
    print("")
    print("Commands:")
    print("  update <workflow-id> <update-name> <json-args>")
    print("  query <workflow-id> <query-name>")
    print("")
    print("=" * 80)
    print("Available Updates:")
    print("=" * 80)
    print("")
    print("1. submit_claim - Submit initial claim with policy selection")
    print("   uv run interact update <wf-id> submit_claim '{")
    print('     "policy_picker": "POL-AUTO-001",')
    print('     "incident_description": "Car accident on Highway 101"')
    print("   }'")
    print("")
    print("2. submit_assessor_findings - Assessor evaluation from incident site")
    print("   uv run interact update <wf-id> submit_assessor_findings '{")
    print('     "visible_assesments": [')
    print("       {")
    print('         "damage_type": "Side collision Damage",')
    print('         "coverage_determination": "Covered",')
    print('         "coverage_score": 100')
    print("       }")
    print("     ],")
    print('     "overall_coverage": "yes",')
    print('     "rationale": "Accident is covered under policy",')
    print('     "incident_city": "San Francisco",')
    print('     "incident_street": "123 Main St",')
    print('     "incident_state": "CA"')
    print("   }'")
    print("")
    print("3. submit_investigation_findings - Investigation for high-cost claims")
    print("   uv run interact update <wf-id> submit_investigation_findings '{")
    print('     "investigation_findings": "Investigation confirms no fraud",')
    print('     "witness_statements": ["Statement 1", "Statement 2"]')
    print("   }'")
    print("")
    print("=" * 80)
    print("Available Queries:")
    print("=" * 80)
    print("")
    print("1. get_status - Get current workflow status and progress")
    print("   uv run interact query <wf-id> get_status")
    print("")
    print("2. get_claim_details - Get submitted claim details")
    print("   uv run interact query <wf-id> get_claim_details")
    print("")
    print("3. get_damage_summary - Get assessor damage summary")
    print("   uv run interact query <wf-id> get_damage_summary")
    print("")


def main() -> None:
    """Console script entry point."""
    if len(sys.argv) < 3:
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

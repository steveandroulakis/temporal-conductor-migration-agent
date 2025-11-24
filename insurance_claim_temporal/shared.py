"""Shared data types for workflow and activities.

This module contains dataclass definitions for:
- Workflow input/output types
- Activity-specific input/output types
- Human interaction types

All types are strongly typed for mypy strict compliance.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class WorkflowInput:
    """Input parameters for the insurance_claim workflow.

    Migrated from Conductor workflow inputs.
    """
    first_name: str
    last_name: str


@dataclass
class WorkflowOutput:
    """Output from the insurance_claim workflow.

    Represents the final outcome of the claim processing workflow.
    Multiple termination paths result in different status/reason combinations.
    """
    status: str  # "COMPLETED" or "TERMINATED"
    reason: str  # Description of termination reason or completion
    details: Optional[Dict[str, Any]] = None  # Additional outcome details


# Activity-specific dataclasses

@dataclass
class Policy:
    """Customer insurance policy details."""
    policy_number: str
    policy_type: str  # e.g., "AUTO", "HOME", "LIFE"


@dataclass
class PolicyMenuItem:
    """Menu item format for policy selection UI.

    Used by map_policies_to_menu_items inline transformation.
    """
    const: str  # policy_number
    title: str  # policy_type


@dataclass
class FindPolicyInput:
    """Input for findPolicyForCustomer activity."""
    first_name: str
    last_name: str


@dataclass
class FindPolicyOutput:
    """Output from findPolicyForCustomer activity."""
    policies: List[Policy]


@dataclass
class CreateClaimInput:
    """Input for createClaimForPolicy activity."""
    policy_id: str
    description: str


# Human interaction dataclasses

@dataclass
class ClaimSubmission:
    """Human-submitted claim information.

    Used with workflow Update for initial claim submission (take_claim_ref).
    """
    policy_picker: str  # Selected policy_number
    incident_description: str


@dataclass
class ClaimSubmissionResult:
    """Result returned from claim submission update."""
    status: str  # "accepted", "rejected"
    message: str


@dataclass
class DamageAssessment:
    """Individual damage assessment item.

    Part of AssessorFindings visible_assesments array.
    """
    damage_type: str  # e.g., "Side collision Damage", "Windshield Damage"
    coverage_determination: str  # "Covered", "Not covered"
    coverage_score: int  # Percentage (0-100)


@dataclass
class AssessorFindings:
    """Assessor evaluation findings.

    Used with workflow Update for assessor report submission (assesor_findings_ref).
    """
    visible_assesments: List[DamageAssessment]
    overall_coverage: str  # "yes", "no", "Not Covered"
    rationale: str  # Assessor explanation
    incident_city: str
    incident_street: str
    incident_state: str


@dataclass
class AssessorFindingsResult:
    """Result returned from assessor findings update."""
    status: str  # "accepted", "rejected"
    message: str


@dataclass
class InvestigationFindings:
    """Investigation findings for high-cost claims.

    Used with workflow Update for investigation report (investigation_human_ref).
    """
    investigation_findings: str  # Detailed investigation results
    witness_statements: Optional[List[str]] = None


@dataclass
class InvestigationFindingsResult:
    """Result returned from investigation findings update."""
    status: str  # "accepted", "rejected"
    message: str


# Damage calculation dataclasses (for determine_price_of_damage inline task)

@dataclass
class DamageItem:
    """Individual damage item with cost calculation."""
    description: str  # Damage type
    estimated_cost: int  # Base cost from cost map
    coverage: str  # "Covered" or "Not covered"
    covered_percentage: int  # Percentage covered (0-100)


@dataclass
class DamageEstimation:
    """Aggregated damage cost estimation."""
    total_damage_cost: int  # Total cost of all damage
    items: List[DamageItem]  # Individual damage items


@dataclass
class CoverageCalculation:
    """Coverage calculation results."""
    total_covered_cost: int  # Amount covered by policy
    total_non_covered_cost: int  # Amount not covered
    explanation: str  # Assessor rationale


@dataclass
class DamageCalculationResult:
    """Complete damage calculation result.

    Output from determine_price_of_damage inline transformation.
    """
    damage_estimation: DamageEstimation
    coverage_calculation: CoverageCalculation


# Constants for damage cost mapping (used in determine_price_of_damage)
DAMAGE_COST_MAP: Dict[str, int] = {
    "Side collision Damage": 2500,
    "Minor front door damage": 500,
    "Windshield Damage": 1000
}

# Cost threshold for triggering investigation
INVESTIGATION_COST_THRESHOLD: int = 100

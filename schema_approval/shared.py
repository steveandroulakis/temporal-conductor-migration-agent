"""Shared dataclasses for the Schema Approval workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WorkflowInput:
    """Input parameters for the Schema Approval workflow."""

    schema_name: str
    """Human readable name of the schema being reviewed."""

    schema_payload: str
    """Serialized schema definition submitted for review."""

    initial_version: int = 1
    """Base version that will be incremented as revisions are uploaded."""

    required_attempts_for_approval: int = 1
    """Number of review rounds required before the schema can be approved."""

    always_require_tertiary_review: bool = False
    """When set, run the tertiary review even if the secondary reviewer approves."""


@dataclass
class SchemaUploadRequest:
    """Parameters sent to the ``upload_schema`` activity."""

    schema_name: str
    schema_payload: str
    target_version: int
    attempt: int


@dataclass
class SchemaSubmission:
    """Result of uploading a schema revision."""

    schema_name: str
    version: int
    payload: str
    attempt: int


@dataclass
class ReviewRequest:
    """Request data for review activities."""

    submission: SchemaSubmission
    reviewer: str
    required_attempts_for_approval: int
    attempt: int
    force_additional_review: bool = False


@dataclass
class ReviewDecision:
    """Decision produced by a review activity."""

    reviewer: str
    approved: bool
    notes: Optional[str] = None
    skip_additional_review: bool = False


@dataclass
class ApprovalRecord:
    """Summary emitted by the ``complete_review`` activity."""

    schema_name: str
    version: int
    attempt: int
    approved: bool
    message: str


@dataclass
class AttemptDetails:
    """Recorded metadata for each loop iteration of the workflow."""

    attempt: int
    submission: SchemaSubmission
    decisions: List[ReviewDecision] = field(default_factory=list)
    finalized: Optional[ApprovalRecord] = None


@dataclass
class WorkflowOutput:
    """Workflow result returned to the caller."""

    approved: bool
    attempts: List[AttemptDetails] = field(default_factory=list)
    final_record: Optional[ApprovalRecord] = None

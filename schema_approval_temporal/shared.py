"""Shared data types for workflow and activities.

This module contains dataclass definitions for:
- Workflow input/output types
- Activity-specific input/output types
- Human interaction types for approval workflows

All types are strongly typed for mypy strict compliance.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class WorkflowInput:
    """Input parameters for the schema_approval workflow.

    Migrated from Conductor workflow inputs.

    Note: The original Conductor workflow has empty inputParameters.
    This dataclass provides a sensible default structure for schema approval.
    """
    schema_id: str
    schema_content: Dict[str, Any]
    submitter_id: str
    priority: int = 1
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowOutput:
    """Output from the schema_approval workflow.

    Migrated from Conductor workflow outputs.
    """
    status: str
    approved: bool
    schema_id: str
    final_approval_stage: str
    iterations: int
    completed_at: Optional[datetime] = None
    approval_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class UploadSchemaInput:
    """Input for upload_schema activity."""
    schema_id: str
    schema_content: Dict[str, Any]
    submitter_id: str
    iteration: int


@dataclass
class UploadSchemaOutput:
    """Output from upload_schema activity."""
    upload_id: str
    status: str
    message: str
    uploaded_at: datetime


@dataclass
class ReviewResult:
    """Result from a review activity (Review1.a, Review1.b, Review2, Review3)."""
    reviewer_id: str
    review_stage: str
    status: str
    comments: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CompleteReviewOutput:
    """Output from CompleteReview activity."""
    completion_id: str
    final_status: str
    approved: bool
    message: str
    completed_at: datetime


@dataclass
class ApprovalDecision:
    """Human approval decision for review checkpoints.

    Used with workflow Updates for approval workflows.
    This is referenced in Conductor as ${user_action.output.approved}.
    """
    reviewer_id: str
    approved: bool
    decision: str  # "YES" or "NO" matching Conductor SWITCH cases
    stage: str  # "Review1Check", "Review2Check", or "Review3Check"
    comments: Optional[str] = None
    timestamp: Optional[datetime] = None
    skip_review3: bool = False  # For Review2Check to decide if Review3 is needed


@dataclass
class ApprovalResult:
    """Result returned from approval update.

    Provides feedback to the approval submitter.
    """
    status: str  # "accepted", "rejected", "invalid"
    message: str
    reviewer: str
    workflow_status: str  # Current workflow state after approval


@dataclass
class WorkflowState:
    """Internal workflow state for tracking progress.

    Not directly migrated from Conductor but useful for managing complex state.
    """
    iteration: int = 0
    approved: bool = False
    current_stage: str = "initialization"
    review1_completed: bool = False
    review2_completed: bool = False
    review3_completed: bool = False
    pending_approval_stage: Optional[str] = None

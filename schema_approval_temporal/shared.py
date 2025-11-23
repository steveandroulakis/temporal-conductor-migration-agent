"""Shared data types for schema approval workflow and activities.

This module contains dataclass definitions for:
- Workflow input/output types
- Activity-specific input/output types
- Human interaction types (approval decisions and results)

All types are strongly typed for mypy strict compliance.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class WorkflowInput:
    """Input parameters for the schema approval workflow.

    Migrated from Conductor workflow inputs. The original Conductor workflow
    had no explicit input parameters, but this structure provides sensible
    defaults for workflow execution.
    """
    submission_id: str
    schema_data: Dict[str, Any]
    submitter_email: str
    priority: int = 1


@dataclass
class WorkflowOutput:
    """Output from the schema approval workflow.

    Contains the final approval status and details of the completed review process.
    """
    status: str  # "approved", "rejected", "pending"
    approval_stage: str  # Which review stage completed the approval
    total_iterations: int  # Number of times the approval loop executed
    completed_at: datetime
    final_decision: Dict[str, Any]


@dataclass
class UploadSchemaInput:
    """Input for upload_schema activity."""
    submission_id: str
    schema_data: Dict[str, Any]
    iteration: int


@dataclass
class ReviewInput:
    """Input for review activities (Review1.a, Review1.b, Review2, Review3)."""
    submission_id: str
    schema_data: Dict[str, Any]
    review_stage: str  # "Review1.a", "Review1.b", "Review2", "Review3"
    previous_reviews: Optional[Dict[str, Any]] = None


@dataclass
class ReviewOutput:
    """Output from review activities."""
    reviewer_id: str
    review_stage: str
    status: str  # "pending", "reviewed", "approved", "rejected"
    timestamp: datetime
    comments: Optional[str] = None


@dataclass
class CompleteReviewInput:
    """Input for CompleteReview activity."""
    submission_id: str
    approval_decisions: Dict[str, Any]
    final_approval: bool


@dataclass
class CompleteReviewOutput:
    """Output from CompleteReview activity."""
    status: str
    message: str
    timestamp: datetime


@dataclass
class ApprovalDecision:
    """Human approval decision sent via workflow Update.

    Used with workflow Updates for approval workflows. Each review checkpoint
    (Review1Check, Review2Check, Review3Check) accepts approval decisions via
    this structure.
    """
    reviewer_id: str
    approved: bool
    skip_review3: bool = False  # For Review2Check decision
    comments: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class ApprovalResult:
    """Result returned from approval update.

    Provides feedback to the approval submitter indicating whether the
    approval was accepted and what the next steps are.
    """
    status: str  # "accepted", "rejected", "duplicate", "awaiting_next_stage"
    message: str
    reviewer: str
    current_stage: str  # "review1", "review2", "review3", "complete"

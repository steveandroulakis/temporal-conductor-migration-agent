"""Shared dataclasses for the schema approval workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class SchemaSubmission:
    """Input describing the schema that requires approval."""

    schema_name: str
    version: int
    description: str
    owner_email: str


@dataclass(frozen=True)
class ReviewRequest:
    """Represents a request sent to a reviewer."""

    review_id: str
    stage: str
    reviewer: str
    iteration: int
    schema_name: str


@dataclass(frozen=True)
class ReviewDecision:
    """Decision returned by a reviewer via a workflow update."""

    review_id: str
    approved: bool
    requires_additional_review: bool = False
    comments: Optional[str] = None


@dataclass
class IterationSummary:
    """Aggregated information for a single review iteration."""

    iteration: int
    schema_name: str
    upload_message: str
    decisions: List[ReviewDecision] = field(default_factory=list)
    approved: bool = False


@dataclass(frozen=True)
class SchemaApprovalResult:
    """Final result returned by the workflow."""

    schema_name: str
    iterations: int
    approved: bool
    summaries: List[IterationSummary]

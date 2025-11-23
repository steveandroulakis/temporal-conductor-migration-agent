"""Shared data types for workflow and activities.

This module contains dataclass definitions for:
- Workflow input/output types
- Activity-specific input/output types
- USPS address validation data structures

All types are strongly typed for mypy strict compliance.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class WorkflowInput:
    """Input parameters for the CheckAddress workflow.

    Migrated from Conductor workflow inputs.
    These parameters are used to construct the USPS API request.
    """
    street: str
    city: str
    state: str
    zip: str


@dataclass
class ParsedAddress:
    """Validated and parsed address from USPS.

    This represents a successfully validated address returned by USPS.
    """
    street: str
    city: str
    state: str
    zip: str


@dataclass
class WorkflowOutput:
    """Output from the CheckAddress workflow.

    Contains either a successfully validated address or an error message.
    """
    success: bool
    parsed_address: Optional[ParsedAddress] = None
    error_message: Optional[str] = None


@dataclass
class UspsHttpRequest:
    """Input for USPS API HTTP activity."""
    uri: str
    method: str = "POST"
    connection_timeout: int = 1000  # milliseconds
    read_timeout: int = 1000  # milliseconds


@dataclass
class UspsHttpResponse:
    """Output from USPS API HTTP activity."""
    status_code: int
    body: str
    headers: Dict[str, Any]

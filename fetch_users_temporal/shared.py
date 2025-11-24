"""Shared data types for workflow and activities.

This module contains dataclass definitions for:
- Workflow input/output types
- Activity-specific input/output types
- HTTP task request/response types
- JSON filtering data types

All types are strongly typed for mypy strict compliance.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class WorkflowInput:
    """Input parameters for the fetch_users workflow.

    Migrated from Conductor workflow inputs.
    This workflow has no input parameters in the original definition.
    """
    pass


@dataclass
class WorkflowOutput:
    """Output from the fetch_users workflow.

    Migrated from Conductor workflow outputs.
    """
    users: List[Dict[str, Any]]


@dataclass
class HttpTaskInput:
    """Input for HTTP activity.

    Used for making HTTP requests to external APIs.
    """
    uri: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    connection_timeout: int = 0
    read_timeout: int = 0


@dataclass
class HttpTaskOutput:
    """Output from HTTP activity.

    Contains the HTTP response data.
    """
    status_code: int
    body: Any
    headers: Dict[str, str]


@dataclass
class FilterUsersInput:
    """Input for user filtering activity.

    Used to filter users based on name criteria.
    """
    users: List[Dict[str, Any]]
    name_pattern: str


@dataclass
class FilterUsersOutput:
    """Output from user filtering activity.

    Contains the filtered list of users.
    """
    filtered_users: List[Dict[str, Any]]

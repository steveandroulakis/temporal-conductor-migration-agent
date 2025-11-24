"""Shared data types for workflow and activities.

This module contains dataclass definitions for:
- Workflow input/output types
- Activity-specific input/output types
- Data structures for security alerts and analysis

All types are strongly typed for mypy strict compliance.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class WorkflowInput:
    """Input parameters for the Agentic Security Example workflow.

    Migrated from Conductor workflow inputs.
    """
    notification_channel: str
    recipient_role: str
    security_malsite_alerts: Optional[List[Dict[str, Any]]] = None
    security_malware_alerts: Optional[List[Dict[str, Any]]] = None


@dataclass
class WorkflowOutput:
    """Output from the Agentic Security Example workflow.

    Migrated from Conductor workflow outputs.
    """
    notified_channel: str
    action_recommendation: str


# Security alert data structures
@dataclass
class MalwareAlert:
    """Individual malware alert from security system."""
    device_id: str
    local_sha256: str
    user: str
    md5: str


@dataclass
class MalsiteAlert:
    """Individual malicious site alert from security system."""
    user: str
    hostname: str
    domain: str


@dataclass
class MockMalwareAlertsResult:
    """Result from mock malware alerts generation."""
    alerts: List[Dict[str, Any]]


@dataclass
class MockMalsiteAlertsResult:
    """Result from mock malsite alerts generation."""
    alerts: List[Dict[str, Any]]


# Extracted data structures
@dataclass
class ExtractedMalwareData:
    """Extracted malware data from alerts.

    Result from JQ transformation activity.
    """
    malware_device_ids: List[Dict[str, str]]
    mw_sha256s: List[Dict[str, str]]
    malware_users: List[Dict[str, str]]
    malware_md5s: List[Dict[str, str]]


@dataclass
class ExtractedMalsiteData:
    """Extracted malsite data from alerts.

    Result from JQ transformation activity.
    """
    malsite_users: List[Dict[str, str]]
    malsite_hostnames: List[Dict[str, str]]


@dataclass
class ExtractedMalsiteDevices:
    """Extracted device IDs from malsite alert processing."""
    malsite_device_ids: List[Dict[str, str]]


# LLM analysis structures
@dataclass
class LLMAnalysisInput:
    """Input for LLM alert analysis activity."""
    malsite_alerts_data: Dict[str, Any]
    malware_alerts_data: Dict[str, Any]
    prompt_name: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 16384


@dataclass
class LLMAnalysisResult:
    """Result from LLM analysis of security alerts."""
    suspected_sha256s: List[str]
    suspected_devices: List[str]
    suspected_users: List[str]
    threat_clusters: List[Dict[str, Any]]


# Validation structures
@dataclass
class ValidationSummary:
    """Accuracy statistics for validation."""
    sha256_accuracy: float
    device_accuracy: float
    user_accuracy: float


@dataclass
class PriorityClassification:
    """Classification of items by priority."""
    high_priority: List[str]
    low_priority: List[str]


@dataclass
class ValidationResult:
    """Result from LLM findings validation."""
    sha256_validation: PriorityClassification
    device_validation: PriorityClassification
    user_validation: PriorityClassification
    summary: ValidationSummary
    action_recommendation: str
    deep_scan: bool


# Child workflow input structures
@dataclass
class SecurityGetDeviceIdInput:
    """Input for security_get_device_id child workflow."""
    hostname: str


@dataclass
class VisionOneDeepVisibilityHuntInput:
    """Input for vision_one_deep_visibility_hunt child workflow."""
    local_sha256: str


@dataclass
class VisionOneDeviceScanInput:
    """Input for vision_one_device_scan child workflow."""
    device_id: str


@dataclass
class NotifyChannelsInput:
    """Input for Notify-Channels child workflow."""
    notification_type: str
    notification_from: str
    notification_to: str
    notification_message: str


# Notification structures
@dataclass
class MessageBodyData:
    """Data used to generate email message body."""
    malsite_devices: ExtractedMalsiteDevices
    malware_alerts: ExtractedMalwareData
    malsite_users: ExtractedMalsiteData

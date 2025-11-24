"""Activity implementations for Agentic Security Example workflow.

This module contains activity functions migrated from Conductor tasks.
Each activity is decorated with @activity.defn and implements specific
security alert processing operations.

Activities:
- JSON transformations for alert data extraction
- OpenAI LLM integration for threat analysis
- Mock data generation utilities

All activities use comprehensive type hints and include detailed docstrings
with timeout and retry recommendations.
"""
import os
import json
from typing import Dict, Any, List
from temporalio import activity

from .shared import (
    ExtractedMalwareData,
    ExtractedMalsiteData,
    ExtractedMalsiteDevices,
    LLMAnalysisInput,
    LLMAnalysisResult,
    MockMalwareAlertsResult,
    MockMalsiteAlertsResult,
)


# ============================================================================
# Mock Data Generation Activities
# ============================================================================


@activity.defn
async def generate_mock_malware_alerts(
    security_malware_alerts: Any
) -> MockMalwareAlertsResult:
    """Generate mock malware alerts data if not provided in workflow input.

    Activity migrated from Conductor INLINE task: mock_security_malware_alerts

    Business Logic:
    Provides default malware alert data for testing and demonstration purposes.
    Returns user-provided alerts if available, otherwise generates realistic
    mock data with 5 malware incidents across different device types and users.

    Args:
        security_malware_alerts: Optional user-provided malware alerts data.
            If None or empty, mock data will be generated.

    Returns:
        MockMalwareAlertsResult containing:
            - alerts: Array of malware alert objects with device_id, sha256,
              md5, user, and other security metadata

    Recommended Configuration:
        - Timeout: 10 seconds (simple data generation)
        - Retry Policy: 3 attempts with exponential backoff
        - Maximum Attempts: 3

    Original Conductor Task Reference: mock_security_malware_alerts_ref
    Nesting Level: 1 (within FORK_JOIN branch)
    """
    activity.logger.info("Generating mock malware alerts data")

    # Return user-provided data if available
    if security_malware_alerts:
        activity.logger.info("Using provided malware alerts data")
        if isinstance(security_malware_alerts, dict) and "result" in security_malware_alerts:
            return MockMalwareAlertsResult(
                alerts=security_malware_alerts["result"].get("alerts", [])
            )
        return MockMalwareAlertsResult(alerts=security_malware_alerts)

    # Generate default mock data
    default_malware_alerts = [
        {
            "timestamp": 1679512845,
            "organization_unit": "Corporate",
            "user": "john.doe@company.com",
            "device": "Windows Workstation",
            "device_id": "ACME-DEV-001-ABC",
            "hostname": "WKSTN-JD001",
            "event_type": "alert",
            "app": "Box",
            "object_type": "file",
            "object": "quarterly_results.xlsm",
            "alert_type": "Malware",
            "alert_name": "Trojan.GenericKD.44758128",
            "severity": "high",
            "category": "Trojan",
            "ccl": "3",
            "policy": "Block Malware",
            "action": "blocked",
            "file_size": 2456789,
            "md5": "a55b9e5d6e279778a752b33b81892144",
            "sha256": "ef537f25c895bfa782526529a9b63d97aa631564d5d789c2b765448c8635fb6c",
            "local_md5": "a55b9e5d6e279778a752b33b81892144",
            "local_sha256": "ef537f25c895bfa782526529a9b63d97aa631564d5d789c2b765448c8635fb6c",
            "browser": "Chrome",
            "browser_version": "109.0.5414.120",
            "os": "Windows",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680012368,
            "organization_unit": "Finance",
            "user": "alice.smith@company.com",
            "device": "Windows Workstation",
            "device_id": "ACME-DEV-002-DEF",
            "hostname": "WKSTN-AS002",
            "event_type": "alert",
            "app": "Dropbox",
            "object_type": "file",
            "object": "invoice_template.docm",
            "alert_type": "Malware",
            "alert_name": "W97M.Downloader",
            "severity": "critical",
            "category": "Trojan Downloader",
            "ccl": "4",
            "policy": "Block Malware",
            "action": "blocked",
            "file_size": 1245678,
            "md5": "c3d825d7892f15e488c1f7472d4307a2",
            "sha256": "8a1c7a943636a8d84c32a619d2f573a0ab45f7531ac01f3b3cbed6fb6f77d67f",
            "local_md5": "c3d825d7892f15e488c1f7472d4307a2",
            "local_sha256": "8a1c7a943636a8d84c32a619d2f573a0ab45f7531ac01f3b3cbed6fb6f77d67f",
            "browser": "Edge",
            "browser_version": "110.0.1587.63",
            "os": "Windows",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680012375,
            "organization_unit": "Engineering",
            "user": "robert.chen@company.com",
            "device": "MacBook Pro",
            "device_id": "ACME-DEV-007-STU",
            "hostname": "MBP-RC007",
            "event_type": "alert",
            "app": "OneDrive",
            "object_type": "file",
            "object": "project_roadmap.xlsx",
            "alert_type": "Malware",
            "alert_name": "OSX.CoinMiner.A",
            "severity": "medium",
            "category": "Cryptominer",
            "ccl": "3",
            "policy": "Block Malware",
            "action": "blocked",
            "file_size": 3458712,
            "md5": "f72e97b45bd5ab0f491c4c7e6388dd76",
            "sha256": "d88bc4547abea342a3b5c5144d6d5c21c7fb6e918a857c9aff075b31f6fe8091",
            "local_md5": "f72e97b45bd5ab0f491c4c7e6388dd76",
            "local_sha256": "d88bc4547abea342a3b5c5144d6d5c21c7fb6e918a857c9aff075b31f6fe8091",
            "browser": "Safari",
            "browser_version": "16.3",
            "os": "macOS",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680012910,
            "organization_unit": "Engineering",
            "user": "robert.chen@company.com",
            "device": "Linux Workstation",
            "device_id": "ACME-DEV-008-VWX",
            "hostname": "LINUX-RC008",
            "event_type": "alert",
            "app": "GitHub",
            "object_type": "file",
            "object": "build_tools.tar.gz",
            "alert_type": "Malware",
            "alert_name": "Linux.Backdoor.Tsunami",
            "severity": "high",
            "category": "Backdoor",
            "ccl": "4",
            "policy": "Block Malware",
            "action": "blocked",
            "file_size": 578234,
            "md5": "3ea97b45dd34fc5491c4121e638123a3",
            "sha256": "a71fc4547a93b432a3bccc5144d6df21c7fb64298a857c9a3f075b31f6f28192",
            "local_md5": "3ea97b45dd34fc5491c4121e638123a3",
            "local_sha256": "a71fc4547a93b432a3bccc5144d6df21c7fb64298a857c9a3f075b31f6f28192",
            "browser": "Firefox",
            "browser_version": "110.0",
            "os": "Linux",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680013215,
            "organization_unit": "Marketing",
            "user": "jennifer.lopez@company.com",
            "device": "Windows Laptop",
            "device_id": "ACME-DEV-009-YZA",
            "hostname": "LAPTOP-JL009",
            "event_type": "alert",
            "app": "Google Drive",
            "object_type": "file",
            "object": "campaign_assets.zip",
            "alert_type": "Malware",
            "alert_name": "Ransom.BlackCat",
            "severity": "critical",
            "category": "Ransomware",
            "ccl": "5",
            "policy": "Block Malware",
            "action": "blocked",
            "file_size": 8923411,
            "md5": "e47b98c6fa2d1c83b7e49f8d6a52abc1",
            "sha256": "7f8e23d14a9b5c6e7f0d1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3",
            "local_md5": "e47b98c6fa2d1c83b7e49f8d6a52abc1",
            "local_sha256": "7f8e23d14a9b5c6e7f0d1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3",
            "browser": "Chrome",
            "browser_version": "110.0.5481.178",
            "os": "Windows",
            "device_classification": "Corporate"
        }
    ]

    activity.logger.info(
        f"Generated {len(default_malware_alerts)} mock malware alerts"
    )
    return MockMalwareAlertsResult(alerts=default_malware_alerts)


@activity.defn
async def generate_mock_malsite_alerts(
    security_malsite_alerts: Any
) -> MockMalsiteAlertsResult:
    """Generate mock malicious site alerts data if not provided in workflow input.

    Activity migrated from Conductor INLINE task: mock_security_malsite_alerts

    Business Logic:
    Provides default malsite alert data for testing and demonstration purposes.
    Returns user-provided alerts if available, otherwise generates realistic
    mock data with 9 malicious site incidents across different users and domains.

    Args:
        security_malsite_alerts: Optional user-provided malsite alerts data.
            If None or empty, mock data will be generated.

    Returns:
        MockMalsiteAlertsResult containing:
            - alerts: Array of malsite alert objects with user, hostname, domain,
              and other security metadata

    Recommended Configuration:
        - Timeout: 10 seconds (simple data generation)
        - Retry Policy: 3 attempts with exponential backoff
        - Maximum Attempts: 3

    Original Conductor Task Reference: mock_security_malsite_alerts_ref
    Nesting Level: 1 (within FORK_JOIN branch)
    """
    activity.logger.info("Generating mock malsite alerts data")

    # Return user-provided data if available
    if security_malsite_alerts:
        activity.logger.info("Using provided malsite alerts data")
        if isinstance(security_malsite_alerts, dict) and "result" in security_malsite_alerts:
            return MockMalsiteAlertsResult(
                alerts=security_malsite_alerts["result"].get("alerts", [])
            )
        return MockMalsiteAlertsResult(alerts=security_malsite_alerts)

    # Generate default mock data
    default_malsite_alerts = [
        {
            "timestamp": 1679425631,
            "organization_unit": "Marketing",
            "user": "mark.johnson@company.com",
            "device": "MacBook Pro",
            "hostname": "MBP-MJ003",
            "event_type": "alert",
            "app": "Web Browsing",
            "url": "http://malicious-downloads.example.com/software.exe",
            "domain": "malicious-downloads.example.com",
            "alert_type": "malsite",
            "alert_name": "Known Malware Distribution Site",
            "severity": "high",
            "category": "Malware",
            "policy": "Block Malicious Websites",
            "action": "blocked",
            "browser": "Safari",
            "browser_version": "16.3",
            "os": "macOS",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1679729521,
            "organization_unit": "Sales",
            "user": "emily.wilson@company.com",
            "device": "Windows Laptop",
            "hostname": "LAPTOP-EW004",
            "event_type": "alert",
            "app": "Web Browsing",
            "url": "https://fake-login.example.net/portal",
            "domain": "fake-login.example.net",
            "alert_type": "malsite",
            "alert_name": "Phishing Site",
            "severity": "medium",
            "category": "Phishing",
            "policy": "Block Malicious Websites",
            "action": "blocked",
            "browser": "Chrome",
            "browser_version": "109.0.5414.120",
            "os": "Windows",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680025683,
            "organization_unit": "Engineering",
            "user": "david.chen@company.com",
            "device": "Windows Workstation",
            "hostname": "WKSTN-DC005",
            "event_type": "alert",
            "app": "Web Browsing",
            "url": "http://malware-cdn.example.org/payload.zip",
            "domain": "malware-cdn.example.org",
            "alert_type": "malsite",
            "alert_name": "Known Malware Distribution Site",
            "severity": "critical",
            "category": "Malware",
            "policy": "Block Malicious Websites",
            "action": "blocked",
            "browser": "Firefox",
            "browser_version": "110.0",
            "os": "Windows",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680112083,
            "organization_unit": "IT",
            "user": "sarah.miller@company.com",
            "device": "Windows Laptop",
            "hostname": "LAPTOP-SM006",
            "event_type": "alert",
            "app": "Web Browsing",
            "url": "https://fake-update.example.com/flash-update.exe",
            "domain": "fake-update.example.com",
            "alert_type": "malsite",
            "alert_name": "Fake Software Update Site",
            "severity": "high",
            "category": "Malware",
            "policy": "Block Malicious Websites",
            "action": "blocked",
            "browser": "Chrome",
            "browser_version": "109.0.5414.120",
            "os": "Windows",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680198483,
            "organization_unit": "Finance",
            "user": "alice.smith@company.com",
            "device": "Windows Workstation",
            "hostname": "WKSTN-AS002",
            "event_type": "alert",
            "app": "Web Browsing",
            "url": "https://invoice-scam.example.net/document.php",
            "domain": "invoice-scam.example.net",
            "alert_type": "malsite",
            "alert_name": "Phishing Site",
            "severity": "high",
            "category": "Phishing",
            "policy": "Block Malicious Websites",
            "action": "blocked",
            "browser": "Edge",
            "browser_version": "110.0.1587.63",
            "os": "Windows",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680011995,
            "organization_unit": "Engineering",
            "user": "robert.chen@company.com",
            "device": "MacBook Pro",
            "hostname": "MBP-RC007",
            "event_type": "alert",
            "app": "Web Browsing",
            "url": "https://xmr-pool.example.io/config.json",
            "domain": "xmr-pool.example.io",
            "alert_type": "malsite",
            "alert_name": "Cryptocurrency Mining Pool",
            "severity": "medium",
            "category": "Cryptomining",
            "policy": "Block Malicious Websites",
            "action": "blocked",
            "browser": "Safari",
            "browser_version": "16.3",
            "os": "macOS",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680012315,
            "organization_unit": "Engineering",
            "user": "robert.chen@company.com",
            "device": "Linux Workstation",
            "hostname": "LINUX-RC008",
            "event_type": "alert",
            "app": "Web Browsing",
            "url": "http://github-assets.example.cc/build-tools/setup.sh",
            "domain": "github-assets.example.cc",
            "alert_type": "malsite",
            "alert_name": "Typosquatting Site",
            "severity": "high",
            "category": "Malware",
            "policy": "Block Malicious Websites",
            "action": "blocked",
            "browser": "Firefox",
            "browser_version": "110.0",
            "os": "Linux",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680012625,
            "organization_unit": "Marketing",
            "user": "jennifer.lopez@company.com",
            "device": "Windows Laptop",
            "hostname": "LAPTOP-JL009",
            "event_type": "alert",
            "app": "Web Browsing",
            "url": "https://ad-campaigns.example.xyz/analytics.php",
            "domain": "ad-campaigns.example.xyz",
            "alert_type": "malsite",
            "alert_name": "Known Malicious Site",
            "severity": "high",
            "category": "Command and Control",
            "policy": "Block Malicious Websites",
            "action": "blocked",
            "browser": "Chrome",
            "browser_version": "110.0.5481.178",
            "os": "Windows",
            "device_classification": "Corporate"
        },
        {
            "timestamp": 1680012970,
            "organization_unit": "Marketing",
            "user": "jennifer.lopez@company.com",
            "device": "Personal iPhone",
            "hostname": "iPhone-JL",
            "event_type": "alert",
            "app": "Web Browsing",
            "url": "https://marketing-templates.example.biz/download/",
            "domain": "marketing-templates.example.biz",
            "alert_type": "malsite",
            "alert_name": "Suspicious Domain",
            "severity": "medium",
            "category": "Malware",
            "policy": "Block Suspicious Websites",
            "action": "blocked",
            "browser": "Safari",
            "browser_version": "16.3",
            "os": "iOS",
            "device_classification": "BYOD"
        }
    ]

    activity.logger.info(
        f"Generated {len(default_malsite_alerts)} mock malsite alerts"
    )
    return MockMalsiteAlertsResult(alerts=default_malsite_alerts)


# ============================================================================
# JSON Transformation Activities (JQ equivalents)
# ============================================================================


@activity.defn
async def extract_malware_alerts(alerts: List[Dict[str, Any]]) -> ExtractedMalwareData:
    """Extract malware device IDs, SHA256s, users, and MD5s from alerts.

    Activity migrated from Conductor JSON_JQ_TRANSFORM task: extract_malware_alerts

    Business Logic:
    Processes malware alerts array and extracts key security indicators:
    - Device IDs for affected machines
    - SHA256 hashes for malware identification
    - User emails for affected personnel
    - MD5 hashes as secondary malware identifiers

    This is a Python translation of the JQ query expression from Conductor.
    Uses list comprehensions to filter and extract specific fields from alerts.

    Args:
        alerts: Array of malware alert objects from security system

    Returns:
        ExtractedMalwareData containing:
            - malware_device_ids: Array of {device_id: string} objects
            - mw_sha256s: Array of {local_sha256: string} objects
            - malware_users: Array of {user: string} objects
            - malware_md5s: Array of {md5: string} objects

    Recommended Configuration:
        - Timeout: 30 seconds (data transformation)
        - Retry Policy: 3 attempts with exponential backoff
        - Maximum Attempts: 3

    Original Conductor Task Reference: extract_malware_alerts_ref
    Nesting Level: 1 (within FORK_JOIN branch)
    """
    activity.logger.info(f"Extracting data from {len(alerts)} malware alerts")

    # Extract device IDs (filter for valid non-empty strings)
    malware_device_ids = [
        {"device_id": alert["device_id"]}
        for alert in alerts
        if "device_id" in alert
        and isinstance(alert["device_id"], str)
        and len(alert["device_id"]) > 0
    ]

    # Extract SHA256 hashes
    mw_sha256s = [
        {"local_sha256": alert["local_sha256"]}
        for alert in alerts
        if "local_sha256" in alert
        and isinstance(alert["local_sha256"], str)
        and len(alert["local_sha256"]) > 0
    ]

    # Extract users
    malware_users = [
        {"user": alert["user"]}
        for alert in alerts
        if "user" in alert
        and isinstance(alert["user"], str)
        and len(alert["user"]) > 0
    ]

    # Extract MD5 hashes
    malware_md5s = [
        {"md5": alert["md5"]}
        for alert in alerts
        if "md5" in alert
        and isinstance(alert["md5"], str)
        and len(alert["md5"]) > 0
    ]

    result = ExtractedMalwareData(
        malware_device_ids=malware_device_ids,
        mw_sha256s=mw_sha256s,
        malware_users=malware_users,
        malware_md5s=malware_md5s,
    )

    activity.logger.info(
        f"Extracted {len(malware_device_ids)} devices, "
        f"{len(mw_sha256s)} SHA256s, "
        f"{len(malware_users)} users, "
        f"{len(malware_md5s)} MD5s"
    )

    return result


@activity.defn
async def extract_malsite_alerts(alerts: Dict[str, Any]) -> ExtractedMalsiteData:
    """Extract malsite users and hostnames from alerts.

    Activity migrated from Conductor JSON_JQ_TRANSFORM task: extract_malsite_alerts

    Business Logic:
    Processes malicious site alerts and extracts:
    - User emails who accessed malicious sites
    - Hostnames of devices that accessed malicious sites

    This is a Python translation of the JQ query expression from Conductor.
    Uses list comprehensions to filter and extract specific fields from alerts.

    Args:
        alerts: Dictionary containing alerts array from security system

    Returns:
        ExtractedMalsiteData containing:
            - malsite_users: Array of {user: string} objects
            - malsite_hostnames: Array of {hostname: string} objects

    Recommended Configuration:
        - Timeout: 30 seconds (data transformation)
        - Retry Policy: 3 attempts with exponential backoff
        - Maximum Attempts: 3

    Original Conductor Task Reference: extract_malsite_alerts_ref
    Nesting Level: 1 (within FORK_JOIN branch)
    """
    activity.logger.info("Extracting data from malsite alerts")

    # Handle nested result structure
    alerts_array = alerts.get("alerts", []) if isinstance(alerts, dict) else alerts

    # Extract users
    malsite_users = [
        {"user": alert["user"]}
        for alert in alerts_array
        if "user" in alert
        and alert["user"] is not None
        and isinstance(alert["user"], str)
        and len(alert["user"]) > 0
    ]

    # Extract hostnames
    malsite_hostnames = [
        {"hostname": alert["hostname"]}
        for alert in alerts_array
        if "hostname" in alert
        and alert["hostname"] is not None
        and isinstance(alert["hostname"], str)
        and len(alert["hostname"]) > 0
    ]

    result = ExtractedMalsiteData(
        malsite_users=malsite_users,
        malsite_hostnames=malsite_hostnames,
    )

    activity.logger.info(
        f"Extracted {len(malsite_users)} users, {len(malsite_hostnames)} hostnames"
    )

    return result


@activity.defn
async def extract_malsite_devices(join_output: Any) -> ExtractedMalsiteDevices:
    """Extract device IDs from joined dynamic fork output.

    Activity migrated from Conductor JSON_JQ_TRANSFORM task: extract_malsite_devices

    Business Logic:
    Processes the output from the dynamic fork that executed
    security_get_device_id child workflows for each hostname.
    Extracts device IDs from the collected results.

    This is a Python translation of the JQ query expression from Conductor.
    Handles potentially nested result structures from child workflow executions.

    Args:
        join_output: Output from dynamic fork join containing device lookup results

    Returns:
        ExtractedMalsiteDevices containing:
            - malsite_device_ids: Array of {device_id: string} objects

    Recommended Configuration:
        - Timeout: 30 seconds (data transformation)
        - Retry Policy: 3 attempts with exponential backoff
        - Maximum Attempts: 3

    Original Conductor Task Reference: extract_malsite_devices_ref
    Nesting Level: 2 (within FORK_JOIN branch, after DYNAMIC_FORK)
    """
    activity.logger.info("Extracting device IDs from dynamic fork results")

    device_ids = []

    # Handle different possible output structures
    if isinstance(join_output, list):
        # List of workflow results
        for item in join_output:
            if isinstance(item, dict) and "device_id" in item:
                device_id = item["device_id"]
                if isinstance(device_id, str) and len(device_id) > 0:
                    device_ids.append({"device_id": device_id})
    elif isinstance(join_output, dict):
        # Single result or nested structure
        # Recursively search for device_id fields
        def extract_device_ids_recursive(obj: Any) -> None:
            if isinstance(obj, dict):
                if "device_id" in obj:
                    device_id = obj["device_id"]
                    if isinstance(device_id, str) and len(device_id) > 0:
                        device_ids.append({"device_id": device_id})
                for value in obj.values():
                    extract_device_ids_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_device_ids_recursive(item)

        extract_device_ids_recursive(join_output)

    result = ExtractedMalsiteDevices(malsite_device_ids=device_ids)

    activity.logger.info(f"Extracted {len(device_ids)} malsite device IDs")

    return result


# ============================================================================
# LLM Integration Activity
# ============================================================================


@activity.defn
async def llm_alert_analysis(llm_input: LLMAnalysisInput) -> LLMAnalysisResult:
    """Analyze security alerts using OpenAI LLM for threat correlation.

    Activity migrated from Conductor LLM_TEXT_COMPLETE task: llm_alert_analysis

    Business Logic:
    Uses OpenAI GPT-4o-mini to analyze malware and malsite security alerts
    and identify:
    - Suspected malicious SHA256 hashes that require investigation
    - Suspected compromised device IDs
    - Suspected affected users
    - Threat clusters (groups of related security incidents)

    The LLM can identify patterns and correlations across alert types that
    simple rule-based systems might miss, providing agentic threat analysis.

    Args:
        llm_input: Analysis request containing:
            - malsite_alerts_data: Malicious site alert data
            - malware_alerts_data: Malware alert data
            - prompt_name: Name of the prompt template
            - model: OpenAI model to use (default: gpt-4o-mini)
            - max_tokens: Maximum response tokens (default: 16384)

    Returns:
        LLMAnalysisResult containing:
            - suspected_sha256s: List of SHA256 hashes requiring investigation
            - suspected_devices: List of device IDs that may be compromised
            - suspected_users: List of user emails that may be affected
            - threat_clusters: Groups of related threats with context

    Recommended Configuration:
        - Timeout: 120 seconds (LLM API calls can be slow)
        - Retry Policy: 3 attempts with exponential backoff starting at 10s
        - Maximum Attempts: 3
        - Retry on: API rate limits, temporary failures

    Original Conductor Task Reference: llm_alert_analysis_ref
    Nesting Level: 0 (main workflow level, after JOIN)

    Environment Requirements:
        - OPENAI_API_KEY: Must be set in environment

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        Exception: On OpenAI API errors (will trigger retry policy)
    """
    activity.logger.info(
        f"Starting LLM alert analysis with model {llm_input.model}"
    )

    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is not set. "
            "LLM analysis requires a valid OpenAI API key."
        )

    try:
        # Import OpenAI SDK (lazy import to avoid import errors if not needed)
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)

        # Construct prompt for security alert analysis
        prompt = f"""You are a cybersecurity analyst reviewing security alerts.

Analyze the following security data and identify threats:

MALWARE ALERTS:
{json.dumps(llm_input.malware_alerts_data, indent=2)}

MALICIOUS SITE ALERTS:
{json.dumps(llm_input.malsite_alerts_data, indent=2)}

Based on these alerts, provide a JSON response with:
1. suspected_sha256s: Array of SHA256 hashes that appear suspicious
2. suspected_devices: Array of device IDs that may be compromised
3. suspected_users: Array of user emails that may be affected
4. threat_clusters: Array of threat clusters with related incidents

Focus on:
- Cross-referencing users/devices across different alert types
- Identifying patterns in malware signatures
- Detecting coordinated attack campaigns
- Highlighting high-severity threats

Return ONLY valid JSON with these exact field names."""

        activity.logger.info(
            f"Sending request to OpenAI API (model: {llm_input.model})"
        )

        # Call OpenAI API
        response = await client.chat.completions.create(
            model=llm_input.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a cybersecurity threat analysis assistant. "
                    "Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=llm_input.max_tokens,
            temperature=0.3,  # Lower temperature for more consistent analysis
            response_format={"type": "json_object"},  # Ensure JSON response
        )

        # Parse LLM response
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI API")

        activity.logger.info("Received response from OpenAI API, parsing JSON")
        llm_response = json.loads(content)

        # Extract fields with defaults
        result = LLMAnalysisResult(
            suspected_sha256s=llm_response.get("suspected_sha256s", []),
            suspected_devices=llm_response.get("suspected_devices", []),
            suspected_users=llm_response.get("suspected_users", []),
            threat_clusters=llm_response.get("threat_clusters", []),
        )

        activity.logger.info(
            f"LLM analysis complete: "
            f"{len(result.suspected_sha256s)} suspected SHA256s, "
            f"{len(result.suspected_devices)} suspected devices, "
            f"{len(result.suspected_users)} suspected users, "
            f"{len(result.threat_clusters)} threat clusters"
        )

        return result

    except ImportError:
        raise ImportError(
            "OpenAI SDK not installed. Run: uv add openai"
        )
    except json.JSONDecodeError as e:
        activity.logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError(f"Invalid JSON response from LLM: {e}")
    except Exception as e:
        activity.logger.error(f"LLM analysis failed: {e}")
        raise

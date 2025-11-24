"""Workflow definition for Agentic Security Example.

This module contains the main workflow orchestration for the security alert
processing workflow migrated from Conductor.

Original Conductor workflow: conductor-definition/Agentic_Security_Example.json
Complexity: HIGH (2-level nested FORK_JOIN + 4 DYNAMIC_FORK + SWITCH)
Max nesting depth: 2 levels

Control Flow Overview:
1. Generate current timestamp (INLINE)
2. FORK_JOIN - Parallel processing of malware and malsite alerts:
   - Branch 1: Mock malware alerts → Extract malware data
   - Branch 2: Mock malsite alerts → Extract malsite data → DYNAMIC_FORK (device ID lookup) → Extract devices
3. LLM analysis of combined alert data
4. Validate LLM findings against extracted data (INLINE)
5. SWITCH - Conditional deep scanning:
   - If deep_scan=True: Execute nested FORK_JOIN with 3 DYNAMIC_FORKs:
     * Threat hunts for SHA256s
     * Device scans for malware-infected devices
     * Device scans for malsite-visiting devices
6. Generate notification message (INLINE)
7. Send notification via child workflow

This workflow is fully automated with NO human interaction.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

# Import shared dataclasses with unsafe.imports_passed_through
with workflow.unsafe.imports_passed_through():
    from .shared import (
        WorkflowInput,
        WorkflowOutput,
        MockMalwareAlertsResult,
        MockMalsiteAlertsResult,
        ExtractedMalwareData,
        ExtractedMalsiteData,
        ExtractedMalsiteDevices,
        LLMAnalysisInput,
        LLMAnalysisResult,
        ValidationResult,
        ValidationSummary,
        PriorityClassification,
        SecurityGetDeviceIdInput,
        VisionOneDeepVisibilityHuntInput,
        VisionOneDeviceScanInput,
        NotifyChannelsInput,
    )
    # CRITICAL: Import specific activity functions by name (NOT the module)
    # This ensures workflow sandbox compliance by avoiding non-deterministic imports
    from .activities import (
        generate_mock_malware_alerts,
        generate_mock_malsite_alerts,
        extract_malware_alerts,
        extract_malsite_alerts,
        extract_malsite_devices,
        llm_alert_analysis,
    )


# Default retry policy for all activities
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=100),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)

# LLM-specific retry policy (longer initial interval for rate limits)
LLM_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    maximum_interval=timedelta(seconds=300),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)


@workflow.defn
class AgenticSecurityExampleWorkflow:
    """
    Agentic security alert processing workflow with LLM-powered threat analysis.

    Control Flow:
    1. Timestamp generation (inline Python)
    2. Parallel alert processing (FORK_JOIN with 2 branches):
       - Malware alerts: Mock → Extract device IDs, SHA256s, users, MD5s
       - Malsite alerts: Mock → Extract users, hostnames → DYNAMIC_FORK device lookup → Extract device IDs
    3. LLM analysis using OpenAI GPT-4o-mini to correlate threats
    4. Validation of LLM findings (inline Python) with accuracy metrics
    5. Conditional deep scanning (SWITCH on deep_scan flag):
       - If True: Nested FORK_JOIN with 3 DYNAMIC_FORKs in parallel:
         * SHA256 threat hunts (child workflow per SHA256)
         * Malware device scans (child workflow per device)
         * Malsite device scans (child workflow per device)
    6. Notification message generation (inline Python with HTML)
    7. Notification delivery (child workflow)

    Original Conductor workflow: Agentic_Security_Example.json
    Complexity: HIGH
    - 2 levels of nesting (main FORK_JOIN contains DYNAMIC_FORK)
    - 4 DYNAMIC_FORK operations requiring child workflows
    - 1 SWITCH with nested parallel execution
    - INLINE tasks translated to deterministic Python code
    - LLM integration with OpenAI API
    - 5 different child workflows called

    Child Workflows Required:
    - security_get_device_id: Lookup device ID from hostname
    - vision_one_deep_visibility_hunt: Threat hunt for SHA256 hash
    - vision_one_device_scan: Device security scan
    - Notify-Channels-x-mocked: Notification delivery

    Environment Requirements:
    - OPENAI_API_KEY: Must be set for LLM analysis

    No Human Interaction:
    This workflow is fully automated with no approval or signal handlers.
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        # Status tracking for queries
        self._current_stage: str = "initializing"
        self._alerts_processed: int = 0
        self._deep_scan_executed: bool = False

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """
        Query current workflow status.

        Allows external systems to check workflow progress without modifying state.

        Returns:
            Dictionary containing:
                - current_stage: Current processing stage
                - alerts_processed: Number of alerts processed
                - deep_scan_executed: Whether deep scanning was performed
        """
        return {
            "current_stage": self._current_stage,
            "alerts_processed": self._alerts_processed,
            "deep_scan_executed": self._deep_scan_executed,
        }

    def _generate_start_time(self) -> str:
        """
        Generate current timestamp (INLINE task translation).

        Conductor INLINE task: get_start_time_ref
        Original JavaScript: Returns current ISO timestamp

        CRITICAL: Use workflow.now() for deterministic timestamp generation.
        DO NOT use datetime.now() or datetime.utcnow() - these cause
        RestrictedWorkflowAccessError in workflow sandbox.

        Returns:
            ISO 8601 timestamp string
        """
        # MUST use workflow.now() for deterministic execution
        current_time = workflow.now()
        return current_time.isoformat()

    def _validate_llm_findings(
        self,
        llm_output: LLMAnalysisResult,
        extracted_malware_sha256s: List[Dict[str, str]],
        extracted_malware_devices: List[Dict[str, str]],
        extracted_malsite_devices: List[Dict[str, str]],
        extracted_malware_users: List[Dict[str, str]],
        extracted_malsite_users: List[Dict[str, str]],
    ) -> ValidationResult:
        """
        Validate LLM findings against extracted data (INLINE task translation).

        Conductor INLINE task: validate_llm_findings_ref
        Original JavaScript: Complex validation logic calculating accuracy and priority

        Business Logic:
        Cross-validates LLM-identified threats with actual extracted data to:
        - Calculate accuracy metrics for SHA256s, devices, users
        - Classify findings as high-priority (in extracted data) or low-priority (not found)
        - Determine if deep scanning is needed (threat clusters found)
        - Generate action recommendation based on findings

        Args:
            llm_output: LLM analysis results with suspected threats
            extracted_malware_sha256s: SHA256 hashes from malware alerts
            extracted_malware_devices: Device IDs from malware alerts
            extracted_malsite_devices: Device IDs from malsite alerts
            extracted_malware_users: Users from malware alerts
            extracted_malsite_users: Users from malsite alerts

        Returns:
            ValidationResult with priority classifications, accuracy stats, and recommendations
        """
        workflow.logger.info("Validating LLM findings against extracted data")

        # Convert extracted data to sets for efficient lookup
        actual_sha256s = {item["local_sha256"] for item in extracted_malware_sha256s}
        actual_malware_devices = {item["device_id"] for item in extracted_malware_devices}
        actual_malsite_devices = {item["device_id"] for item in extracted_malsite_devices}
        actual_devices = actual_malware_devices.union(actual_malsite_devices)
        actual_malware_users = {item["user"] for item in extracted_malware_users}
        actual_malsite_users = {item["user"] for item in extracted_malsite_users}
        actual_users = actual_malware_users.union(actual_malsite_users)

        # Validate SHA256s
        suspected_sha256s_set = set(llm_output.suspected_sha256s)
        sha256_high_priority = list(suspected_sha256s_set.intersection(actual_sha256s))
        sha256_low_priority = list(suspected_sha256s_set.difference(actual_sha256s))
        sha256_accuracy = (
            len(sha256_high_priority) / len(suspected_sha256s_set)
            if len(suspected_sha256s_set) > 0
            else 0.0
        )

        # Validate devices
        suspected_devices_set = set(llm_output.suspected_devices)
        device_high_priority = list(suspected_devices_set.intersection(actual_devices))
        device_low_priority = list(suspected_devices_set.difference(actual_devices))
        device_accuracy = (
            len(device_high_priority) / len(suspected_devices_set)
            if len(suspected_devices_set) > 0
            else 0.0
        )

        # Validate users
        suspected_users_set = set(llm_output.suspected_users)
        user_high_priority = list(suspected_users_set.intersection(actual_users))
        user_low_priority = list(suspected_users_set.difference(actual_users))
        user_accuracy = (
            len(user_high_priority) / len(suspected_users_set)
            if len(suspected_users_set) > 0
            else 0.0
        )

        # Determine if deep scan is needed (threat clusters indicate coordinated attack)
        deep_scan_needed = len(llm_output.threat_clusters) > 0

        # Generate action recommendation
        avg_accuracy = (sha256_accuracy + device_accuracy + user_accuracy) / 3.0
        if avg_accuracy > 0.8 and deep_scan_needed:
            recommendation = (
                f"HIGH PRIORITY: {len(llm_output.threat_clusters)} threat cluster(s) detected "
                f"with {avg_accuracy:.1%} validation accuracy. Initiating deep visibility scans."
            )
        elif deep_scan_needed:
            recommendation = (
                f"MEDIUM PRIORITY: {len(llm_output.threat_clusters)} threat cluster(s) detected "
                f"with {avg_accuracy:.1%} validation accuracy. Review findings and initiate scans."
            )
        else:
            recommendation = (
                f"LOW PRIORITY: No threat clusters detected. "
                f"LLM validation accuracy: {avg_accuracy:.1%}. Monitor alerts."
            )

        result = ValidationResult(
            sha256_validation=PriorityClassification(
                high_priority=sha256_high_priority,
                low_priority=sha256_low_priority,
            ),
            device_validation=PriorityClassification(
                high_priority=device_high_priority,
                low_priority=device_low_priority,
            ),
            user_validation=PriorityClassification(
                high_priority=user_high_priority,
                low_priority=user_low_priority,
            ),
            summary=ValidationSummary(
                sha256_accuracy=sha256_accuracy,
                device_accuracy=device_accuracy,
                user_accuracy=user_accuracy,
            ),
            action_recommendation=recommendation,
            deep_scan=deep_scan_needed,
        )

        workflow.logger.info(
            f"Validation complete: SHA256 {sha256_accuracy:.1%}, "
            f"Device {device_accuracy:.1%}, User {user_accuracy:.1%}, "
            f"Deep scan: {deep_scan_needed}"
        )

        return result

    def _generate_message_body(
        self,
        malsite_devices: ExtractedMalsiteDevices,
        malware_alerts: ExtractedMalwareData,
        malsite_users: ExtractedMalsiteData,
    ) -> str:
        """
        Generate HTML email body from scan results (INLINE task translation).

        Conductor INLINE task: generate_message_body_ref
        Original JavaScript: Generates HTML email with device lists, users, hashes

        Args:
            malsite_devices: Device IDs from malsite alerts
            malware_alerts: Extracted malware alert data
            malsite_users: Extracted malsite user data

        Returns:
            HTML email body string
        """
        workflow.logger.info("Generating notification message body")

        # Extract data for display
        malware_device_count = len(malware_alerts.malware_device_ids)
        malsite_device_count = len(malsite_devices.malsite_device_ids)
        sha256_count = len(malware_alerts.mw_sha256s)
        malware_user_count = len(malware_alerts.malware_users)
        malsite_user_count = len(malsite_users.malsite_users)

        # Generate HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h2 {{ color: #d32f2f; }}
                .section {{ margin: 20px 0; }}
                .metric {{ font-weight: bold; color: #1976d2; }}
                ul {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h2>Security Alert Summary</h2>

            <div class="section">
                <h3>Malware Alerts</h3>
                <p><span class="metric">Devices:</span> {malware_device_count}</p>
                <p><span class="metric">Users:</span> {malware_user_count}</p>
                <p><span class="metric">SHA256 Hashes:</span> {sha256_count}</p>
            </div>

            <div class="section">
                <h3>Malicious Site Alerts</h3>
                <p><span class="metric">Devices:</span> {malsite_device_count}</p>
                <p><span class="metric">Users:</span> {malsite_user_count}</p>
            </div>

            <div class="section">
                <h3>Recommended Actions</h3>
                <ul>
                    <li>Review identified devices for compromise indicators</li>
                    <li>Investigate users with multiple alert types</li>
                    <li>Analyze malware samples using identified SHA256 hashes</li>
                    <li>Monitor for additional activity on affected devices</li>
                </ul>
            </div>

            <p><em>This is an automated security alert from the Agentic Security System.</em></p>
        </body>
        </html>
        """

        workflow.logger.info(
            f"Message body generated: {malware_device_count + malsite_device_count} devices, "
            f"{malware_user_count + malsite_user_count} users, {sha256_count} hashes"
        )

        return html_body

    async def _process_malware_alerts_branch(
        self, workflow_input: WorkflowInput
    ) -> ExtractedMalwareData:
        """
        Helper method for malware alerts processing branch.

        Conductor FORK_JOIN Branch 1:
        1. mock_security_malware_alerts (INLINE → Activity)
        2. extract_malware_alerts (JSON_JQ_TRANSFORM → Activity)

        Args:
            workflow_input: Workflow input with optional malware alerts

        Returns:
            ExtractedMalwareData with device IDs, SHA256s, users, MD5s
        """
        workflow.logger.info("Processing malware alerts branch")

        # Step 1: Generate or use provided malware alerts
        malware_mock_result = await workflow.execute_activity(
            generate_mock_malware_alerts,
            workflow_input.security_malware_alerts,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 2: Extract malware data
        malware_extracted: ExtractedMalwareData = await workflow.execute_activity(
            extract_malware_alerts,
            malware_mock_result.alerts,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        workflow.logger.info(
            f"Malware branch complete: {len(malware_extracted.malware_device_ids)} devices, "
            f"{len(malware_extracted.mw_sha256s)} SHA256s"
        )

        return malware_extracted

    async def _process_malsite_alerts_branch(
        self, workflow_input: WorkflowInput
    ) -> tuple[ExtractedMalsiteData, ExtractedMalsiteDevices]:
        """
        Helper method for malsite alerts processing branch.

        Conductor FORK_JOIN Branch 2 (contains nested DYNAMIC_FORK):
        1. mock_security_malsite_alerts (INLINE → Activity)
        2. extract_malsite_alerts (JSON_JQ_TRANSFORM → Activity)
        3. get_device_id_dynamic_fork (DYNAMIC_FORK → asyncio.gather of child workflows)
        4. get_device_id_dynamic_join (JOIN → implicit in gather)
        5. extract_malsite_devices (JSON_JQ_TRANSFORM → Activity)

        Args:
            workflow_input: Workflow input with optional malsite alerts

        Returns:
            Tuple of (ExtractedMalsiteData, ExtractedMalsiteDevices)
        """
        workflow.logger.info("Processing malsite alerts branch")

        # Step 1: Generate or use provided malsite alerts
        malsite_mock_result = await workflow.execute_activity(
            generate_mock_malsite_alerts,
            workflow_input.security_malsite_alerts,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 2: Extract malsite data (users and hostnames)
        malsite_extracted = await workflow.execute_activity(
            extract_malsite_alerts,
            {"alerts": malsite_mock_result.alerts},
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        # Step 3: DYNAMIC_FORK - Execute security_get_device_id child workflow for each hostname
        # Conductor: get_device_id_dynamic_fork_ref with forkTaskWorkflow="security_get_device_id"
        # Translation: List comprehension + asyncio.gather()
        workflow.logger.info(
            f"Starting DYNAMIC_FORK: {len(malsite_extracted.malsite_hostnames)} "
            f"device ID lookups in parallel"
        )

        # Create child workflow executions for each hostname
        device_lookup_calls = [
            workflow.execute_child_workflow(
                "SecurityGetDeviceIdWorkflow",
                SecurityGetDeviceIdInput(hostname=hostname_dict["hostname"]),
                id=f"{workflow.info().workflow_id}-device-lookup-{idx}",
                task_queue="agentic-security-example-task-queue",
            )
            for idx, hostname_dict in enumerate(malsite_extracted.malsite_hostnames)
        ]

        # Execute all device lookups in parallel
        device_lookup_results = await asyncio.gather(*device_lookup_calls)

        # Conductor JOIN task (get_device_id_dynamic_join_ref) is implicit here
        workflow.logger.info(
            f"Device ID lookups complete: {len(device_lookup_results)} results"
        )

        # Step 4: Extract device IDs from child workflow results
        malsite_devices = await workflow.execute_activity(
            extract_malsite_devices,
            device_lookup_results,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        workflow.logger.info(
            f"Malsite branch complete: {len(malsite_devices.malsite_device_ids)} devices"
        )

        return malsite_extracted, malsite_devices

    async def _execute_deep_scans(
        self,
        malware_sha256s: List[Dict[str, str]],
        malware_device_ids: List[Dict[str, str]],
        malsite_device_ids: List[Dict[str, str]],
    ) -> None:
        """
        Execute deep visibility scans (nested FORK_JOIN with 3 DYNAMIC_FORKs).

        Conductor: alert_follow_up_actions_fork_ref with 3 parallel branches
        Each branch contains a DYNAMIC_FORK executing child workflows.

        Branch 1: Threat hunts for each SHA256 hash
        Branch 2: Device scans for malware-infected devices
        Branch 3: Device scans for malsite-visiting devices

        This is the most complex nested structure in the workflow:
        SWITCH → FORK_JOIN → 3 DYNAMIC_FORKs in parallel

        Args:
            malware_sha256s: SHA256 hashes to hunt for
            malware_device_ids: Malware-infected device IDs to scan
            malsite_device_ids: Malsite-visiting device IDs to scan
        """
        workflow.logger.info(
            f"Starting deep scans: {len(malware_sha256s)} SHA256s, "
            f"{len(malware_device_ids)} malware devices, "
            f"{len(malsite_device_ids)} malsite devices"
        )

        # Execute all 3 DYNAMIC_FORK branches in parallel using asyncio.gather
        await asyncio.gather(
            # Branch 1: DYNAMIC_FORK - Threat hunts for SHA256s
            self._execute_threat_hunts(malware_sha256s),
            # Branch 2: DYNAMIC_FORK - Device scans for malware-infected devices
            self._execute_malware_device_scans(malware_device_ids),
            # Branch 3: DYNAMIC_FORK - Device scans for malsite-visiting devices
            self._execute_malsite_device_scans(malsite_device_ids),
        )

        # Conductor JOIN task (alert_follow_up_actions_join_ref) is implicit here
        workflow.logger.info("Deep scans complete")

    async def _execute_threat_hunts(
        self, malware_sha256s: List[Dict[str, str]]
    ) -> List[Any]:
        """
        Execute threat hunts for SHA256 hashes (DYNAMIC_FORK).

        Conductor: last_30_days_threat_hunt_dynamic_fork_ref
        Child workflow: vision_one_deep_visibility_hunt

        Args:
            malware_sha256s: SHA256 hashes to hunt for

        Returns:
            List of threat hunt results from child workflows
        """
        workflow.logger.info(
            f"Starting DYNAMIC_FORK: {len(malware_sha256s)} threat hunts in parallel"
        )

        # Create child workflow executions for each SHA256
        threat_hunt_calls = [
            workflow.execute_child_workflow(
                "VisionOneDeepVisibilityHuntWorkflow",
                VisionOneDeepVisibilityHuntInput(local_sha256=sha256_dict["local_sha256"]),
                id=f"{workflow.info().workflow_id}-threat-hunt-{idx}",
                task_queue="agentic-security-example-task-queue",
            )
            for idx, sha256_dict in enumerate(malware_sha256s)
        ]

        # Execute all threat hunts in parallel
        results = await asyncio.gather(*threat_hunt_calls)

        # Conductor JOIN task (last_30_days_threat_hunt_join_ref) is implicit
        workflow.logger.info(f"Threat hunts complete: {len(results)} results")

        return results

    async def _execute_malware_device_scans(
        self, malware_device_ids: List[Dict[str, str]]
    ) -> List[Any]:
        """
        Execute device scans for malware-infected devices (DYNAMIC_FORK).

        Conductor: infected_device_scans_dynamic_fork_ref
        Child workflow: vision_one_device_scan

        Args:
            malware_device_ids: Malware-infected device IDs to scan

        Returns:
            List of device scan results from child workflows
        """
        workflow.logger.info(
            f"Starting DYNAMIC_FORK: {len(malware_device_ids)} malware device scans in parallel"
        )

        # Create child workflow executions for each device
        device_scan_calls = [
            workflow.execute_child_workflow(
                "VisionOneDeviceScanWorkflow",
                VisionOneDeviceScanInput(device_id=device_dict["device_id"]),
                id=f"{workflow.info().workflow_id}-malware-scan-{idx}",
                task_queue="agentic-security-example-task-queue",
            )
            for idx, device_dict in enumerate(malware_device_ids)
        ]

        # Execute all device scans in parallel
        results = await asyncio.gather(*device_scan_calls)

        # Conductor JOIN task (infected_device_scans_join_ref) is implicit
        workflow.logger.info(f"Malware device scans complete: {len(results)} results")

        return results

    async def _execute_malsite_device_scans(
        self, malsite_device_ids: List[Dict[str, str]]
    ) -> List[Any]:
        """
        Execute device scans for malsite-visiting devices (DYNAMIC_FORK).

        Conductor: malsite_visited_device_scans_dynamic_fork_ref
        Child workflow: vision_one_device_scan

        Args:
            malsite_device_ids: Malsite-visiting device IDs to scan

        Returns:
            List of device scan results from child workflows
        """
        workflow.logger.info(
            f"Starting DYNAMIC_FORK: {len(malsite_device_ids)} malsite device scans in parallel"
        )

        # Create child workflow executions for each device
        device_scan_calls = [
            workflow.execute_child_workflow(
                "VisionOneDeviceScanWorkflow",
                VisionOneDeviceScanInput(device_id=device_dict["device_id"]),
                id=f"{workflow.info().workflow_id}-malsite-scan-{idx}",
                task_queue="agentic-security-example-task-queue",
            )
            for idx, device_dict in enumerate(malsite_device_ids)
        ]

        # Execute all device scans in parallel
        results = await asyncio.gather(*device_scan_calls)

        # Conductor JOIN task (malsite_visited_device_scans_join_ref) is implicit
        workflow.logger.info(f"Malsite device scans complete: {len(results)} results")

        return results

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        """
        Execute the agentic security alert processing workflow.

        This workflow implements complex enterprise security orchestration:
        - Parallel processing of multiple alert types
        - LLM-powered threat correlation and analysis
        - Conditional deep scanning based on threat severity
        - Automated notification delivery

        Args:
            input: WorkflowInput containing:
                - notification_channel: Channel for notifications (email, slack, etc.)
                - recipient_role: Role to notify (security team, admin, etc.)
                - security_malsite_alerts: Optional malsite alert data
                - security_malware_alerts: Optional malware alert data

        Returns:
            WorkflowOutput containing:
                - notified_channel: Channel that was notified
                - action_recommendation: Recommended actions based on analysis

        Raises:
            ApplicationError: On unrecoverable business logic failures
        """
        workflow.logger.info(
            f"Starting agentic security workflow - "
            f"notification channel: {input.notification_channel}"
        )
        self._current_stage = "started"

        # Step 1: Generate current timestamp (INLINE task: get_start_time_ref)
        # CRITICAL: Uses workflow.now() for deterministic timestamp
        self._current_stage = "generating_timestamp"
        start_time = self._generate_start_time()
        workflow.logger.info(f"Workflow started at: {start_time}")

        # Step 2: FORK_JOIN - Parallel processing of malware and malsite alerts
        # Conductor: get_alerts_calls_fork_ref with 2 branches
        # Translation: asyncio.gather() with helper methods for each branch
        self._current_stage = "processing_alerts"
        workflow.logger.info("Starting parallel alert processing (FORK_JOIN with 2 branches)")

        # Execute both branches in parallel
        malware_extracted, (malsite_extracted, malsite_devices) = await asyncio.gather(
            self._process_malware_alerts_branch(input),
            self._process_malsite_alerts_branch(input),
        )

        # Conductor JOIN task (security_calls_join_ref) is implicit here
        self._alerts_processed = (
            len(malware_extracted.malware_device_ids)
            + len(malsite_devices.malsite_device_ids)
        )
        workflow.logger.info(
            f"Alert processing complete: {self._alerts_processed} total devices identified"
        )

        # Step 3: LLM analysis of security alerts
        # Conductor: llm_alert_analysis_ref (LLM_TEXT_COMPLETE)
        # Translation: Activity with OpenAI API integration
        self._current_stage = "llm_analysis"
        workflow.logger.info("Starting LLM-powered threat analysis")

        llm_result = await workflow.execute_activity(
            llm_alert_analysis,
            LLMAnalysisInput(
                malsite_alerts_data={"alerts": malsite_extracted.__dict__},
                malware_alerts_data={"alerts": malware_extracted.__dict__},
                prompt_name="llm_alert_analysis",
                model="gpt-4o-mini",
                max_tokens=16384,
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=LLM_RETRY_POLICY,
        )

        workflow.logger.info(
            f"LLM analysis complete: {len(llm_result.suspected_sha256s)} suspected SHA256s, "
            f"{len(llm_result.suspected_devices)} suspected devices, "
            f"{len(llm_result.threat_clusters)} threat clusters"
        )

        # Step 4: Validate LLM findings (INLINE task: validate_llm_findings_ref)
        # Translation: Python validation logic in workflow
        self._current_stage = "validating_findings"
        workflow.logger.info("Validating LLM findings against extracted data")

        validation_result = self._validate_llm_findings(
            llm_output=llm_result,
            extracted_malware_sha256s=malware_extracted.mw_sha256s,
            extracted_malware_devices=malware_extracted.malware_device_ids,
            extracted_malsite_devices=malsite_devices.malsite_device_ids,
            extracted_malware_users=malware_extracted.malware_users,
            extracted_malsite_users=malsite_extracted.malsite_users,
        )

        workflow.logger.info(
            f"Validation complete: {validation_result.action_recommendation}"
        )

        # Step 5: SWITCH - Conditional deep scanning
        # Conductor: decide_visionone_follow_ups_ref (SWITCH on deep_scan flag)
        # Expression: "if ($.deep_scan_required) { true; } else { false; }"
        # Translation: Python if statement
        self._current_stage = "checking_deep_scan"

        if validation_result.deep_scan:
            # YES case: Execute nested FORK_JOIN with 3 DYNAMIC_FORKs
            # This is the most complex nested structure:
            # SWITCH → FORK_JOIN (alert_follow_up_actions_fork_ref) → 3 DYNAMIC_FORKs
            workflow.logger.info(
                "Deep scan required - executing nested parallel scans (SWITCH YES case)"
            )
            self._current_stage = "executing_deep_scans"
            self._deep_scan_executed = True

            await self._execute_deep_scans(
                malware_sha256s=malware_extracted.mw_sha256s,
                malware_device_ids=malware_extracted.malware_device_ids,
                malsite_device_ids=malsite_devices.malsite_device_ids,
            )

            workflow.logger.info("Deep scans completed successfully")
        else:
            # NO/default case: Skip deep scans
            workflow.logger.info(
                "Deep scan not required - skipping (SWITCH NO/default case)"
            )

        # Step 6: Generate notification message (INLINE task: generate_message_body_ref)
        # Translation: Python HTML generation in workflow
        self._current_stage = "generating_notification"
        workflow.logger.info("Generating notification message")

        message_body = self._generate_message_body(
            malsite_devices=malsite_devices,
            malware_alerts=malware_extracted,
            malsite_users=malsite_extracted,
        )

        # Step 7: Send notification via child workflow
        # Conductor: notify_channels_subwf_ref (SUB_WORKFLOW)
        # Translation: workflow.execute_child_workflow()
        self._current_stage = "sending_notification"
        workflow.logger.info(f"Sending notification via {input.notification_channel}")

        notification_result = await workflow.execute_child_workflow(
            "NotifyChannelsWorkflow",
            NotifyChannelsInput(
                notification_type=input.notification_channel,
                notification_from="templates-dev@orkes.io",
                notification_to="templates-dev@orkes.io",
                notification_message=message_body,
            ),
            id=f"{workflow.info().workflow_id}-notification",
            task_queue="agentic-security-example-task-queue",
        )

        workflow.logger.info(f"Notification sent successfully: {notification_result}")

        # Workflow complete
        self._current_stage = "completed"
        workflow.logger.info(
            f"Workflow completed successfully - "
            f"{self._alerts_processed} alerts processed, "
            f"deep scan: {self._deep_scan_executed}"
        )

        return WorkflowOutput(
            notified_channel=input.notification_channel,
            action_recommendation=validation_result.action_recommendation,
        )

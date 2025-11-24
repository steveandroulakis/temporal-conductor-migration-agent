"""Child workflow stubs for Agentic Security Example.

This module contains stub implementations of child workflows referenced by the main
AgenticSecurityExampleWorkflow. These are placeholder workflows that return mock data
for testing the parent workflow execution.

In a real implementation, these would:
- SecurityGetDeviceIdWorkflow: Query security system to lookup device ID from hostname
- VisionOneDeepVisibilityHuntWorkflow: Execute deep visibility threat hunt for SHA256
- VisionOneDeviceScanWorkflow: Initiate device security scan
- NotifyChannelsWorkflow: Send notifications via email/Slack/etc.

For now, they return TODO placeholders to allow the parent workflow to complete.
"""
from temporalio import workflow

# Import shared dataclasses with unsafe.imports_passed_through
with workflow.unsafe.imports_passed_through():
    from .shared import (
        SecurityGetDeviceIdInput,
        VisionOneDeepVisibilityHuntInput,
        VisionOneDeviceScanInput,
        NotifyChannelsInput,
    )


@workflow.defn
class SecurityGetDeviceIdWorkflow:
    """
    Child workflow to lookup device ID from hostname.

    Original Conductor workflow: security_get_device_id
    Called via DYNAMIC_FORK for each hostname from malsite alerts.

    TODO: Implement actual device ID lookup logic:
    - Query security API/database with hostname
    - Return device ID for the given hostname
    - Handle cases where device not found
    """

    @workflow.run
    async def run(self, input: SecurityGetDeviceIdInput) -> dict[str, str]:
        """
        Execute device ID lookup.

        Args:
            input: SecurityGetDeviceIdInput with hostname

        Returns:
            Dictionary with device_id field
        """
        workflow.logger.info(
            f"SecurityGetDeviceIdWorkflow: Looking up device ID for hostname: {input.hostname}"
        )

        # TODO: Replace with actual device lookup logic
        # Example:
        # device_id = await workflow.execute_activity(
        #     query_device_by_hostname,
        #     input.hostname,
        #     start_to_close_timeout=timedelta(seconds=30)
        # )

        # Return mock device ID for now
        mock_device_id = f"device-{hash(input.hostname) % 10000:04d}"
        workflow.logger.info(
            f"SecurityGetDeviceIdWorkflow: Returning device ID: {mock_device_id}"
        )

        return {"device_id": mock_device_id}


@workflow.defn
class VisionOneDeepVisibilityHuntWorkflow:
    """
    Child workflow to execute threat hunt for SHA256 hash.

    Original Conductor workflow: vision_one_deep_visibility_hunt
    Called via DYNAMIC_FORK for each SHA256 from malware alerts.

    TODO: Implement actual threat hunt logic:
    - Submit SHA256 to Vision One Deep Visibility API
    - Poll for hunt results
    - Return threat intelligence findings
    """

    @workflow.run
    async def run(self, input: VisionOneDeepVisibilityHuntInput) -> dict[str, str]:
        """
        Execute deep visibility threat hunt.

        Args:
            input: VisionOneDeepVisibilityHuntInput with SHA256 hash

        Returns:
            Dictionary with hunt results
        """
        workflow.logger.info(
            f"VisionOneDeepVisibilityHuntWorkflow: Hunting for SHA256: {input.local_sha256}"
        )

        # TODO: Replace with actual Vision One API integration
        # Example:
        # hunt_result = await workflow.execute_activity(
        #     submit_threat_hunt,
        #     input.local_sha256,
        #     start_to_close_timeout=timedelta(minutes=5)
        # )

        # Return mock hunt result for now
        workflow.logger.info(
            f"VisionOneDeepVisibilityHuntWorkflow: Hunt complete for {input.local_sha256}"
        )

        return {
            "sha256": input.local_sha256,
            "hunt_status": "TODO: Implement Vision One integration",
            "findings": "Mock data",
        }


@workflow.defn
class VisionOneDeviceScanWorkflow:
    """
    Child workflow to initiate device security scan.

    Original Conductor workflow: vision_one_device_scan
    Called via DYNAMIC_FORK for malware-infected and malsite-visiting devices.

    TODO: Implement actual device scan logic:
    - Submit device ID to Vision One scan API
    - Initiate full or quick scan
    - Poll for scan completion
    - Return scan results
    """

    @workflow.run
    async def run(self, input: VisionOneDeviceScanInput) -> dict[str, str]:
        """
        Execute device security scan.

        Args:
            input: VisionOneDeviceScanInput with device ID

        Returns:
            Dictionary with scan results
        """
        workflow.logger.info(
            f"VisionOneDeviceScanWorkflow: Scanning device: {input.device_id}"
        )

        # TODO: Replace with actual Vision One device scan API integration
        # Example:
        # scan_result = await workflow.execute_activity(
        #     initiate_device_scan,
        #     input.device_id,
        #     start_to_close_timeout=timedelta(minutes=10)
        # )

        # Return mock scan result for now
        workflow.logger.info(
            f"VisionOneDeviceScanWorkflow: Scan complete for {input.device_id}"
        )

        return {
            "device_id": input.device_id,
            "scan_status": "TODO: Implement Vision One device scan integration",
            "threats_found": 0,
        }


@workflow.defn
class NotifyChannelsWorkflow:
    """
    Child workflow to send notifications via specified channel.

    Original Conductor workflow: Notify-Channels-x-mocked
    Sends security alert notifications via email, Slack, etc.

    TODO: Implement actual notification logic:
    - Parse notification_type (email, slack, teams, etc.)
    - Format message for channel
    - Send notification via appropriate service
    - Return confirmation
    """

    @workflow.run
    async def run(self, input: NotifyChannelsInput) -> str:
        """
        Send notification via specified channel.

        Args:
            input: NotifyChannelsInput with channel, from, to, message

        Returns:
            Name of channel that was notified
        """
        workflow.logger.info(
            f"NotifyChannelsWorkflow: Sending notification via {input.notification_type}"
        )
        workflow.logger.info(
            f"NotifyChannelsWorkflow: From: {input.notification_from}, To: {input.notification_to}"
        )

        # TODO: Replace with actual notification service integration
        # Example:
        # if input.notification_type == "email":
        #     await workflow.execute_activity(
        #         send_email,
        #         EmailInput(
        #             from_addr=input.notification_from,
        #             to_addr=input.notification_to,
        #             body=input.notification_message
        #         ),
        #         start_to_close_timeout=timedelta(seconds=30)
        #     )
        # elif input.notification_type == "slack":
        #     await workflow.execute_activity(send_slack_message, ...)

        # Return mock confirmation for now
        workflow.logger.info(
            f"NotifyChannelsWorkflow: Notification sent via {input.notification_type}"
        )

        return input.notification_type

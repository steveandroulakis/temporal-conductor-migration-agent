"""Workflow definition for USPS address validation.

This workflow verifies a US postal address using the USPS Address Validation API.
It implements nested conditional branching to handle API failures, validation errors,
and successful address parsing.

Control Flow:
1. HTTP Activity: Call USPS API with address details
2. SWITCH (api_success): Check X-Backside-Transport header
   - If "FAIL FAIL": Raise ApplicationFailure (API failure)
   - Default: Continue to address validation
3. SWITCH (address_success): Check if XML contains "Error"
   - If Error found: Extract error message and return error result
   - Default (success): Parse address from XML and return success result

Original Conductor workflow: check_address.json
Complexity: MEDIUM (nested SWITCH tasks, INLINE XML parsing, multiple termination paths)
Max nesting depth: 3
"""

import xml.etree.ElementTree as ET
from datetime import timedelta
from typing import Dict, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

# CRITICAL: Import activity by name only for workflow sandbox compliance
# activities.py imports httpx which is non-deterministic, so we cannot import the module
with workflow.unsafe.imports_passed_through():
    from .shared import WorkflowInput, WorkflowOutput, ParsedAddress
    from .activities import verify_address_usps


# Default retry policy for activities
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)


@workflow.defn
class CheckAddressWorkflow:
    """
    Temporal workflow migrated from Conductor workflow: check_address

    This workflow verifies a US postal address by calling the USPS Address Validation API
    and parsing the XML response to extract validated address information or error messages.

    Control Flow Pattern:
    - HTTP task for API call
    - Nested SWITCH tasks for conditional branching
    - INLINE tasks for XML parsing (implemented as helper methods)
    - Multiple TERMINATE paths (API failure, validation error, success)

    Original Conductor workflow: check_address.json
    Complexity: MEDIUM
    - Nested SWITCH tasks (2 levels)
    - JavaScript INLINE tasks requiring Python translation
    - Complex XML parsing logic
    - Multiple termination outcomes

    Data Flow:
    - Input: street, city, state, zip
    - API Response: XML from USPS with either validated address or error
    - Output: Structured result with success flag and either parsed address or error message
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        self._status: str = "started"

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        """
        Execute the USPS address validation workflow.

        This workflow calls the USPS Address Validation API and processes the response
        through nested conditional logic to determine if the address is valid.

        Args:
            input: WorkflowInput containing street, city, state, and zip fields

        Returns:
            WorkflowOutput with:
                - success=True and parsed_address if validation succeeds
                - success=False and error_message if validation fails or API errors

        Raises:
            ApplicationError: If the USPS API call fails at the transport level
        """
        workflow.logger.info(
            f"Starting address validation: {input.street}, {input.city}, "
            f"{input.state} {input.zip}"
        )
        self._status = "validating"

        # Step 1: Call USPS API to verify address
        # Original Conductor task: verify_addy_usps (type: HTTP)
        # Timeout: 1000ms connection + 1000ms read timeout
        # Retry: 3 attempts with exponential backoff
        workflow.logger.info("Calling USPS Address Validation API")

        api_response = await workflow.execute_activity(
            verify_address_usps,
            args=[input.street, input.city, input.state, input.zip, "steveandroulakis"],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        workflow.logger.info(
            f"USPS API returned status {api_response.status_code}, "
            f"body length {len(api_response.body)}"
        )

        # Step 2: SWITCH task - Check API success via X-Backside-Transport header
        # Original Conductor task: api_success (type: SWITCH)
        # Evaluates: ${verify_addy_usps.output.response.headers.X-Backside-Transport[0]}
        # Case "FAIL FAIL": Execute API_fail (TERMINATE with FAILED)
        # Default case: Continue to address validation

        # Safe header access with default value
        transport_header = api_response.headers.get("X-Backside-Transport", [""])[0] if isinstance(
            api_response.headers.get("X-Backside-Transport"), list
        ) else api_response.headers.get("X-Backside-Transport", "")

        workflow.logger.info(f"X-Backside-Transport header: {transport_header}")

        if transport_header == "FAIL FAIL":
            # TERMINATE task: API_fail (terminationStatus: FAILED)
            # Original Conductor: Terminate workflow with FAILED status
            # Temporal: Raise ApplicationError to fail the workflow
            workflow.logger.error("API transport failure detected")
            self._status = "api_failed"
            raise ApplicationError(
                "USPS API call failed",
                api_response.body,
                type="APITransportFailure",
                non_retryable=True,
            )

        # Step 3: SWITCH task (nested) - Check if address validation succeeded
        # Original Conductor task: address_success (type: SWITCH)
        # Evaluates: JavaScript function checking if response body contains "Error"
        # Case false (Error found): Extract error message → TERMINATE COMPLETED with error
        # Default case (no Error): Parse address → TERMINATE COMPLETED with success

        workflow.logger.info("Checking XML response for validation errors")

        if "Error" in api_response.body:
            # Error path: Address validation failed
            # Original Conductor: get_error_message (INLINE) → address_error (TERMINATE COMPLETED)

            # INLINE task: get_error_message
            # Original: JavaScript extracting <Description> tag content
            # Translated: Python helper method for XML parsing
            workflow.logger.warning("Address validation error detected in XML")
            error_message = self._extract_error_message(api_response.body)
            workflow.logger.info(f"Extracted error message: {error_message}")

            # TERMINATE task: address_error (terminationStatus: COMPLETED)
            # This represents a business logic error (invalid address), not a workflow failure
            # Return structured result with error details
            self._status = "validation_error"
            return WorkflowOutput(
                success=False,
                error_message=error_message,
                parsed_address=None,
            )

        else:
            # Success path: Address validation succeeded
            # Original Conductor: parse_address_json (INLINE) → terminate_success (TERMINATE COMPLETED)

            # INLINE task: parse_address_json
            # Original: JavaScript extracting <Address2>, <City>, <State>, <Zip5> tags
            # Translated: Python helper method for XML parsing
            workflow.logger.info("Parsing validated address from XML")
            parsed_address = self._parse_address_from_xml(api_response.body)
            workflow.logger.info(
                f"Successfully parsed address: {parsed_address.street}, "
                f"{parsed_address.city}, {parsed_address.state} {parsed_address.zip}"
            )

            # TERMINATE task: terminate_success (terminationStatus: COMPLETED)
            # Return structured result with validated address data
            self._status = "completed"
            return WorkflowOutput(
                success=True,
                parsed_address=parsed_address,
                error_message=None,
            )

    def _extract_error_message(self, xml_body: str) -> str:
        """
        Extract error description from USPS XML response.

        This helper method implements the logic from Conductor INLINE task: get_error_message
        Original JavaScript logic: Parse XML to extract <Description> tag content

        USPS error XML format:
        <AddressValidateResponse>
            <Address>
                <Error>
                    <Number>-2147219401</Number>
                    <Source>clsAMS</Source>
                    <Description>Address Not Found.</Description>
                    ...
                </Error>
            </Address>
        </AddressValidateResponse>

        Args:
            xml_body: Raw XML response string from USPS API

        Returns:
            Error description string extracted from <Description> tag
            Returns generic message if parsing fails
        """
        workflow.logger.debug("Extracting error message from XML")

        try:
            # Parse XML using ElementTree for safe parsing
            root = ET.fromstring(xml_body)

            # Find Description element within Error element
            # USPS structure: AddressValidateResponse > Address > Error > Description
            description_elem = root.find(".//Error/Description")

            if description_elem is not None and description_elem.text:
                return description_elem.text.strip()

            # Fallback: Try string parsing if ElementTree fails to find the tag
            # Original Conductor JavaScript approach as backup
            desc_start_tag = "<Description>"
            desc_end_tag = "</Description>"

            if desc_start_tag in xml_body and desc_end_tag in xml_body:
                start_idx = xml_body.index(desc_start_tag) + len(desc_start_tag)
                end_idx = xml_body.index(desc_end_tag)
                return xml_body[start_idx:end_idx].strip()

            # No description found
            workflow.logger.warning("Could not find Description tag in error XML")
            return "Address validation failed (no error description available)"

        except ET.ParseError as e:
            workflow.logger.error(f"XML parsing error: {e}")
            return f"Address validation failed (XML parse error: {e})"
        except Exception as e:
            workflow.logger.error(f"Unexpected error extracting error message: {e}")
            return f"Address validation failed (error extraction failed: {e})"

    def _parse_address_from_xml(self, xml_body: str) -> ParsedAddress:
        """
        Parse validated address from USPS XML response.

        This helper method implements the logic from Conductor INLINE task: parse_address_json
        Original JavaScript logic: Extract <Address2>, <City>, <State>, <Zip5> tags and
        construct JSON object

        USPS success XML format:
        <AddressValidateResponse>
            <Address>
                <Address2>123 MAIN ST</Address2>
                <City>NEW YORK</City>
                <State>NY</State>
                <Zip5>10001</Zip5>
                <Zip4>1234</Zip4>
            </Address>
        </AddressValidateResponse>

        Args:
            xml_body: Raw XML response string from USPS API

        Returns:
            ParsedAddress dataclass with street, city, state, zip fields

        Raises:
            ApplicationError: If XML parsing fails or required fields are missing
        """
        workflow.logger.debug("Parsing validated address from XML")

        try:
            # Parse XML using ElementTree
            root = ET.fromstring(xml_body)

            # Extract address fields
            # USPS structure: AddressValidateResponse > Address > field elements
            address_elem = root.find(".//Address")

            if address_elem is None:
                raise ApplicationError(
                    "Invalid USPS response: No Address element found",
                    xml_body,
                    type="XMLParseError",
                    non_retryable=True,
                )

            # Extract individual fields (USPS uses Address2 for street address)
            street_elem = address_elem.find("Address2")
            city_elem = address_elem.find("City")
            state_elem = address_elem.find("State")
            zip_elem = address_elem.find("Zip5")

            # Validate all required fields are present
            if street_elem is None or not street_elem.text:
                raise ApplicationError(
                    "Missing Address2 (street) field in USPS response",
                    xml_body,
                    type="XMLParseError",
                    non_retryable=True,
                )
            if city_elem is None or not city_elem.text:
                raise ApplicationError(
                    "Missing City field in USPS response",
                    xml_body,
                    type="XMLParseError",
                    non_retryable=True,
                )
            if state_elem is None or not state_elem.text:
                raise ApplicationError(
                    "Missing State field in USPS response",
                    xml_body,
                    type="XMLParseError",
                    non_retryable=True,
                )
            if zip_elem is None or not zip_elem.text:
                raise ApplicationError(
                    "Missing Zip5 field in USPS response",
                    xml_body,
                    type="XMLParseError",
                    non_retryable=True,
                )

            # Construct ParsedAddress with validated data
            parsed = ParsedAddress(
                street=street_elem.text.strip(),
                city=city_elem.text.strip(),
                state=state_elem.text.strip(),
                zip=zip_elem.text.strip(),
            )

            workflow.logger.debug(f"Successfully parsed address: {parsed}")
            return parsed

        except ET.ParseError as e:
            workflow.logger.error(f"XML parsing error: {e}")
            raise ApplicationError(
                f"Failed to parse USPS XML response: {e}",
                xml_body,
                type="XMLParseError",
                non_retryable=True,
            )
        except ApplicationError:
            # Re-raise ApplicationError as-is
            raise
        except Exception as e:
            workflow.logger.error(f"Unexpected error parsing address: {e}")
            raise ApplicationError(
                f"Unexpected error parsing USPS response: {e}",
                xml_body,
                type="XMLParseError",
                non_retryable=True,
            )

    @workflow.query
    def get_status(self) -> Dict[str, str]:
        """
        Query current workflow status.

        Allows external systems to check workflow progress without modifying state.

        Returns:
            Dictionary with current status information
        """
        return {
            "status": self._status,
        }

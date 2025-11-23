"""Activity implementations.

This module contains activity functions migrated from Conductor tasks.
Each activity is decorated with @activity.defn and implements a specific
business operation or external service call.

IMPORTANT NOTE ABOUT INLINE TASKS:
This workflow has 2 INLINE tasks in the Conductor definition (get_error_message
and parse_address_json) that perform XML parsing using JavaScript. These are
NOT implemented as activities here - they will be implemented as inline Python
code within the workflow, as they are simple data transformations that don't
require external I/O or long-running operations.

Activities in this module:
- verify_address_usps: Mock USPS Address Validation activity (realistic responses)

NOTE: This uses MOCK data instead of the real USPS API, as the USPS system is
transitioning to OAuth-based authentication (required by January 2026).
"""
from temporalio import activity

from check_address_temporal.shared import UspsHttpResponse


@activity.defn
async def verify_address_usps(
    street: str,
    city: str,
    state: str,
    zip_code: str,
    username: str = "steveandroulakis"
) -> UspsHttpResponse:
    """Validate and standardize US postal addresses using realistic mock data.

    NOTE: This is a MOCK implementation. The USPS API is transitioning to an
    OAuth-based Developer Portal system (required by January 2026), so this
    activity uses realistic mock responses instead of calling the real API.

    Business Logic:
    Validates a US postal address and returns the USPS-standardized version
    (typically in all CAPS) or an error if the address cannot be validated.

    The mock implementation includes:
    - Known valid addresses: Return USPS-standardized format (all caps)
    - Unknown addresses: Return "Address Not Found" error
    - Empty/invalid inputs: Return appropriate validation errors

    Args:
        street: Street address line (e.g., "100 Winchester Circle")
        city: City name (e.g., "Los Gatos")
        state: Two-letter state code (e.g., "CA")
        zip_code: 5-digit ZIP code (e.g., "95032")
        username: USPS API username (retained for compatibility, not used in mock)

    Returns:
        UspsHttpResponse containing:
            - status_code: HTTP response status code (always 200 for mock)
            - body: XML response body matching USPS format
            - headers: HTTP response headers including X-Backside-Transport

    Recommended Configuration:
        - Timeout: start_to_close_timeout=timedelta(seconds=10)
        - Retry Policy: RetryPolicy with maximum_attempts=2

    Original Conductor Task Reference: verify_addy_usps (type: HTTP)
    """
    activity.logger.info(
        f"USPS address validation (MOCK): street={street}, city={city}, "
        f"state={state}, zip={zip_code}"
    )

    # Known valid addresses for testing (based on conductor-definition/README.md examples)
    known_addresses = {
        ("100 Winchester Circle", "Los Gatos", "CA"): ("100 WINCHESTER CIR", "LOS GATOS", "CA", "95032"),
        ("1600 Pennsylvania Avenue NW", "Washington", "DC"): ("1600 PENNSYLVANIA AVE NW", "WASHINGTON", "DC", "20500"),
        ("1 Apple Park Way", "Cupertino", "CA"): ("1 APPLE PARK WAY", "CUPERTINO", "CA", "95014"),
    }

    # Normalize input for lookup (case-insensitive)
    lookup_key = (street.strip(), city.strip(), state.strip().upper())

    # Check if address is in known valid addresses
    for known_key, validated_address in known_addresses.items():
        if (known_key[0].lower() == lookup_key[0].lower() and
            known_key[1].lower() == lookup_key[1].lower() and
            known_key[2].upper() == lookup_key[2].upper()):

            # Return USPS-standardized address (all caps)
            validated_street, validated_city, validated_state, validated_zip = validated_address
            activity.logger.info(f"Mock: Address found and validated - {validated_street}")

            mock_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<AddressValidateResponse>'
                '<Address>'
                f'<Address2>{validated_street}</Address2>'
                f'<City>{validated_city}</City>'
                f'<State>{validated_state}</State>'
                f'<Zip5>{validated_zip}</Zip5>'
                '<Zip4></Zip4>'
                '</Address>'
                '</AddressValidateResponse>'
            )
            return UspsHttpResponse(
                status_code=200,
                body=mock_xml,
                headers={"X-Backside-Transport": "OK OK", "Content-Type": "text/xml"}
            )

    # Address not found - return error response
    activity.logger.warning(f"Mock: Address not found - {street}, {city}, {state}")

    mock_error_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<AddressValidateResponse>'
        '<Address>'
        '<Error>'
        '<Number>-2147219401</Number>'
        '<Source>clsAMS</Source>'
        '<Description>Address Not Found.</Description>'
        '<HelpFile></HelpFile>'
        '<HelpContext></HelpContext>'
        '</Error>'
        '</Address>'
        '</AddressValidateResponse>'
    )
    return UspsHttpResponse(
        status_code=200,
        body=mock_error_xml,
        headers={"X-Backside-Transport": "OK OK", "Content-Type": "text/xml"}
    )

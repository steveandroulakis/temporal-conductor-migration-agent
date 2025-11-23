# Conductor to Temporal: Comparison Guide

This document shows side-by-side comparisons of how each Conductor task type was translated to Temporal Python code for the CheckAddress workflow.

**Original Conductor Workflow**: `conductor-definition/check_address.json`

---

## Workflow Definition

### Conductor (JSON)
```json
{
  "name": "check_address",
  "version": 1,
  "description": "verify an address with USPS",
  "inputParameters": ["street", "city", "state", "zip"],
  "outputParameters": {
    "header": "${verify_addy_usps.output.response.headers}",
    "address": "${verify_addy_usps.output.response.body}"
  },
  "schemaVersion": 2,
  "restartable": true,
  "ownerEmail": "doug.sillars@orkes.io"
}
```

### Temporal (Python)
```python
@workflow.defn
class CheckAddressWorkflow:
    """
    Temporal workflow migrated from Conductor workflow: check_address

    This workflow verifies a US postal address by calling the USPS
    Address Validation API and parsing the XML response.
    """

    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        # Workflow implementation
        ...
```

### Translation Notes
- Conductor's declarative JSON defines workflow metadata; Temporal uses Python decorators
- Input parameters become dataclass fields with strong typing
- Output parameters are structured as a return type (WorkflowOutput dataclass)
- Workflow logic is expressed as procedural Python code, not JSON configuration

---

## Task 1: verify_addy_usps (HTTP Task)

**Original Conductor Task Reference**: `verify_addy_usps`

### Conductor JSON
```json
{
  "name": "verify address",
  "taskReferenceName": "verify_addy_usps",
  "type": "HTTP",
  "inputParameters": {
    "http_request": {
      "uri": "https://production.shippingapis.com/ShippingAPI.dll?API=Verify&XML=<AddressValidateRequest USERID=\"${workflow.secrets.post_office_username}\"><Address><Address1>${workflow.input.street}</Address1><Address2></Address2><City>${workflow.input.city}</City><State>${workflow.input.state}</State><Zip5>${workflow.input.zip}</Zip5><Zip4></Zip4></Address></AddressValidateRequest>",
      "method": "POST",
      "connectionTimeOut": 1000,
      "readTimeOut": 1000
    }
  }
}
```

### Temporal Python

**Activity Definition** (activities.py):
```python
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
    OAuth-based Developer Portal system (required by January 2026).
    """
    activity.logger.info(
        f"USPS address validation (MOCK): street={street}, city={city}, "
        f"state={state}, zip={zip_code}"
    )

    # Known valid addresses for testing
    known_addresses = {
        ("100 Winchester Circle", "Los Gatos", "CA"):
            ("100 WINCHESTER CIR", "LOS GATOS", "CA", "95032"),
        ("1600 Pennsylvania Avenue NW", "Washington", "DC"):
            ("1600 PENNSYLVANIA AVE NW", "WASHINGTON", "DC", "20500"),
        # ... more addresses
    }

    # Return mock USPS-formatted XML response
    # ...
```

**Workflow Invocation** (workflow.py):
```python
api_response = await workflow.execute_activity(
    verify_address_usps,
    args=[input.street, input.city, input.state, input.zip, "steveandroulakis"],
    start_to_close_timeout=timedelta(seconds=10),
    retry_policy=DEFAULT_RETRY_POLICY,
)
```

### Translation Notes
- Conductor HTTP task → Temporal @activity.defn function
- URI template with embedded XML → Structured function parameters
- Conductor's `${workflow.input.X}` expressions → Python `input.X`
- Conductor's `${workflow.secrets.X}` → Function parameter (can be passed from config)
- Connection/read timeouts → Temporal's `start_to_close_timeout`
- **Mock Implementation**: Real USPS API replaced with mock for OAuth transition
- Mock returns realistic USPS-formatted XML responses

---

## Task 2: api_success (SWITCH Task)

**Original Conductor Task Reference**: `api_success`

### Conductor JSON
```json
{
  "name": "api_success",
  "taskReferenceName": "api_success",
  "type": "SWITCH",
  "inputParameters": {
    "switchCaseValue": "${verify_addy_usps.output.response.headers.X-Backside-Transport[0]}"
  },
  "evaluatorType": "value-param",
  "expression": "switchCaseValue",
  "decisionCases": {
    "FAIL FAIL": ["API_fail"]
  },
  "defaultCase": ["address_success"]
}
```

### Temporal Python
```python
# Safe header access with default value
transport_header = api_response.headers.get("X-Backside-Transport", [""])[0] if isinstance(
    api_response.headers.get("X-Backside-Transport"), list
) else api_response.headers.get("X-Backside-Transport", "")

workflow.logger.info(f"X-Backside-Transport header: {transport_header}")

if transport_header == "FAIL FAIL":
    # TERMINATE task: API_fail (terminationStatus: FAILED)
    workflow.logger.error("API transport failure detected")
    self._status = "api_failed"
    raise ApplicationError(
        "USPS API call failed",
        api_response.body,
        type="APITransportFailure",
        non_retryable=True,
    )

# Default case: Continue to address validation (address_success SWITCH)
```

### Translation Notes
- Conductor SWITCH with `evaluatorType: value-param` → Python `if/elif/else`
- JSONPath `${verify_addy_usps.output.response.headers.X-Backside-Transport[0]}` → Python `api_response.headers.get(...)`
- Safe array access handling (checks if header is list or string)
- Case "FAIL FAIL" → `if` branch
- Default case → implicit `else` (code continues)

---

## Task 3: API_fail (TERMINATE Task)

**Original Conductor Task Reference**: `API_fail`

### Conductor JSON
```json
{
  "name": "terminate_fail",
  "taskReferenceName": "API_fail",
  "type": "TERMINATE",
  "inputParameters": {
    "terminationStatus": "FAILED",
    "workflowOutput": {
      "api_response": "${verify_addy_usps.output.response.body}"
    }
  }
}
```

### Temporal Python
```python
raise ApplicationError(
    "USPS API call failed",
    api_response.body,
    type="APITransportFailure",
    non_retryable=True,
)
```

### Translation Notes
- Conductor TERMINATE with `terminationStatus: FAILED` → Temporal `raise ApplicationError`
- This FAILS the workflow execution (visible as FAILED in Temporal UI)
- Workflow output becomes error details attached to the ApplicationError
- `non_retryable=True` prevents automatic retries

---

## Task 4: address_success (Nested SWITCH Task)

**Original Conductor Task Reference**: `address_success`

### Conductor JSON
```json
{
  "name": "address_success",
  "taskReferenceName": "address_success",
  "type": "SWITCH",
  "inputParameters": {
    "inputvalue": "${verify_addy_usps.output.response.body}"
  },
  "evaluatorType": "javascript",
  "expression": "function hasError() {var input = $.inputvalue; if(input.indexOf('Error')>0){return false;}else{return true;}} hasError();",
  "decisionCases": {
    "false": ["get_error_message", "address_error"]
  },
  "defaultCase": ["parse_address_json", "terminate_success"]
}
```

### Temporal Python
```python
workflow.logger.info("Checking XML response for validation errors")

if "Error" in api_response.body:
    # Error path: Address validation failed
    # Case "false" - executes get_error_message + address_error

    error_message = self._extract_error_message(api_response.body)
    workflow.logger.info(f"Extracted error message: {error_message}")

    # TERMINATE task: address_error (terminationStatus: COMPLETED)
    self._status = "validation_error"
    return WorkflowOutput(
        success=False,
        error_message=error_message,
        parsed_address=None,
    )

else:
    # Success path: Address validation succeeded
    # Default case - executes parse_address_json + terminate_success

    parsed_address = self._parse_address_from_xml(api_response.body)
    workflow.logger.info(f"Successfully parsed address: {parsed_address.street}, ...")

    # TERMINATE task: terminate_success (terminationStatus: COMPLETED)
    self._status = "completed"
    return WorkflowOutput(
        success=True,
        parsed_address=parsed_address,
        error_message=None,
    )
```

### Translation Notes
- Conductor SWITCH with `evaluatorType: javascript` → Python `if/else`
- JavaScript function checking for "Error" substring → Python `"Error" in api_response.body`
- Case "false" (error found) → `if` branch
- Default case (no error) → `else` branch
- Conductor's sequential task list → Python method calls and return statements
- This is a **nested SWITCH** (inside the default case of the previous SWITCH)

---

## Task 5: get_error_message (INLINE Task)

**Original Conductor Task Reference**: `get_error_message`

### Conductor JSON
```json
{
  "name": "get_error_message",
  "taskReferenceName": "get_error_message",
  "type": "INLINE",
  "inputParameters": {
    "xml": "${verify_addy_usps.output.response.body}",
    "evaluatorType": "javascript",
    "expression": "function e() {var xml = $.xml;var descriptionIndexStart = xml.indexOf('<Description>')+13;var descriptionIndexEnd = xml.indexOf('</Description>');var description = xml.substring(descriptionIndexStart,descriptionIndexEnd);return description;}e();"
  }
}
```

### Temporal Python

**Workflow Helper Method**:
```python
def _extract_error_message(self, xml_body: str) -> str:
    """
    Extract error description from USPS XML response.

    This helper method implements the logic from Conductor INLINE task.
    Original JavaScript logic: Parse XML to extract <Description> tag content.
    """
    workflow.logger.debug("Extracting error message from XML")

    try:
        # Parse XML using ElementTree for safe parsing
        root = ET.fromstring(xml_body)

        # Find Description element within Error element
        description_elem = root.find(".//Error/Description")

        if description_elem is not None and description_elem.text:
            return description_elem.text.strip()

        # Fallback: Try string parsing (original Conductor JavaScript approach)
        desc_start_tag = "<Description>"
        desc_end_tag = "</Description>"

        if desc_start_tag in xml_body and desc_end_tag in xml_body:
            start_idx = xml_body.index(desc_start_tag) + len(desc_start_tag)
            end_idx = xml_body.index(desc_end_tag)
            return xml_body[start_idx:end_idx].strip()

        # No description found
        return "Address validation failed (no error description available)"

    except ET.ParseError as e:
        workflow.logger.error(f"XML parsing error: {e}")
        return f"Address validation failed (XML parse error: {e})"
```

### Translation Notes
- Conductor INLINE task with JavaScript → Temporal workflow helper method (Python)
- JavaScript string manipulation (`indexOf`, `substring`) → Python xml.etree.ElementTree (safer)
- Fallback to string parsing if ElementTree fails (preserves original logic)
- INLINE tasks execute within workflow context (deterministic), so they're implemented as workflow methods, NOT activities
- Error handling added for XML parsing failures

---

## Task 6: address_error (TERMINATE Task with COMPLETED Status)

**Original Conductor Task Reference**: `address_error`

### Conductor JSON
```json
{
  "name": "terminate_fail_error",
  "taskReferenceName": "address_error",
  "type": "TERMINATE",
  "inputParameters": {
    "terminationStatus": "COMPLETED",
    "workflowOutput": {
      "error_message": "${get_error_message.output}"
    }
  }
}
```

### Temporal Python
```python
# TERMINATE task: address_error (terminationStatus: COMPLETED)
# This represents a business logic error (invalid address), not a workflow failure
# Return structured result with error details
self._status = "validation_error"
return WorkflowOutput(
    success=False,
    error_message=error_message,
    parsed_address=None,
)
```

### Translation Notes
- Conductor TERMINATE with `terminationStatus: COMPLETED` → Temporal `return` statement
- The workflow completes successfully (status COMPLETED in Temporal UI)
- But the result indicates validation failure (success=False)
- This is a **business logic error**, not a workflow execution error
- Different from API_fail which uses `raise ApplicationError` (workflow FAILED)

---

## Task 7: parse_address_json (INLINE Task)

**Original Conductor Task Reference**: `parse_address_json`

### Conductor JSON
```json
{
  "name": "parse_address_json",
  "taskReferenceName": "parse_address_json",
  "type": "INLINE",
  "inputParameters": {
    "xml": "${verify_addy_usps.output.response.body}",
    "evaluatorType": "javascript",
    "expression": "function e() {var xml = $.xml;var streetIndexStart = xml.indexOf('<Address2>')+10;var streetIndexEnd = xml.indexOf('</Address2>');var street = xml.substring(streetIndexStart,streetIndexEnd);var cityIndexStart = xml.indexOf('<City>')+6;var cityIndexEnd = xml.indexOf('</City>');var city = xml.substring(cityIndexStart,cityIndexEnd);var stateIndexStart = xml.indexOf('<State>')+7;var stateIndexEnd = xml.indexOf('</State>');var state = xml.substring(stateIndexStart,stateIndexEnd);var zipIndexStart = xml.indexOf('<Zip5>')+6;var zipIndexEnd = xml.indexOf('</Zip5>');var zip = xml.substring(zipIndexStart,zipIndexEnd);var json = '{\"street\":\"' +street+'\",\"city\":\"' +city+'\",\"state\":\"' +state+'\",\"zip\":\"' +zip+'\"}' ;return JSON.parse(json);}e();"
  }
}
```

### Temporal Python

**Workflow Helper Method**:
```python
def _parse_address_from_xml(self, xml_body: str) -> ParsedAddress:
    """
    Parse validated address from USPS XML response.

    This helper method implements the logic from Conductor INLINE task.
    Original JavaScript logic: Extract address fields and construct JSON object.
    """
    workflow.logger.debug("Parsing validated address from XML")

    try:
        # Parse XML using ElementTree
        root = ET.fromstring(xml_body)

        # Extract address fields
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
            raise ApplicationError("Missing Address2 (street) field", ...)
        if city_elem is None or not city_elem.text:
            raise ApplicationError("Missing City field", ...)
        if state_elem is None or not state_elem.text:
            raise ApplicationError("Missing State field", ...)
        if zip_elem is None or not zip_elem.text:
            raise ApplicationError("Missing Zip5 field", ...)

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
```

### Translation Notes
- Conductor INLINE JavaScript → Temporal workflow helper method (Python)
- JavaScript string manipulation → Python xml.etree.ElementTree (safer and more maintainable)
- JavaScript manual JSON construction → Python dataclass (type-safe)
- Comprehensive field validation added (raises ApplicationError if fields missing)
- Error handling for XML parsing failures
- USPS uses `Address2` for street address (not `Address1`)

---

## Task 8: terminate_success (TERMINATE Task)

**Original Conductor Task Reference**: `terminate_success`

### Conductor JSON
```json
{
  "name": "terminate_success",
  "taskReferenceName": "terminate_success",
  "type": "TERMINATE",
  "inputParameters": {
    "terminationStatus": "COMPLETED",
    "workflowOutput": {
      "api_response": "${parse_address_json.output}"
    }
  }
}
```

### Temporal Python
```python
# TERMINATE task: terminate_success (terminationStatus: COMPLETED)
# Return structured result with validated address data
self._status = "completed"
return WorkflowOutput(
    success=True,
    parsed_address=parsed_address,
    error_message=None,
)
```

### Translation Notes
- Conductor TERMINATE with `terminationStatus: COMPLETED` → Temporal `return` statement
- Workflow completes successfully with success=True
- Parsed address data included in structured output
- Status field updated for query handlers

---

## Control Flow Patterns

### Pattern: Nested SWITCH Tasks

**Conductor Structure**:
```json
// Outer SWITCH: api_success
{
  "type": "SWITCH",
  "decisionCases": {
    "FAIL FAIL": ["API_fail"]
  },
  "defaultCase": ["address_success"]  // Inner SWITCH
}

// Inner SWITCH: address_success (nested within default case)
{
  "type": "SWITCH",
  "decisionCases": {
    "false": ["get_error_message", "address_error"]
  },
  "defaultCase": ["parse_address_json", "terminate_success"]
}
```

**Temporal Translation**:
```python
# Outer conditional: Check API transport
if transport_header == "FAIL FAIL":
    # API failure path
    raise ApplicationError(...)

# Default case of outer conditional: Check address validation
if "Error" in api_response.body:
    # Error path (inner conditional - case "false")
    error_message = self._extract_error_message(api_response.body)
    return WorkflowOutput(success=False, error_message=error_message, ...)
else:
    # Success path (inner conditional - default case)
    parsed_address = self._parse_address_from_xml(api_response.body)
    return WorkflowOutput(success=True, parsed_address=parsed_address, ...)
```

**Explanation**:
Conductor's nested SWITCH tasks map to nested if/else statements in Python. The outer SWITCH checks the API transport header, and its default case contains another SWITCH that checks for validation errors. This creates a 3-level nesting depth.

---

## Data Flow Examples

### Workflow Input Access

**Conductor**: `${workflow.input.street}`
**Temporal**: `input.street`

Example:
```python
# In workflow.run():
api_response = await workflow.execute_activity(
    verify_address_usps,
    args=[input.street, input.city, input.state, input.zip, "steveandroulakis"],
    ...
)
```

### Task Output Access

**Conductor**: `${verify_addy_usps.output.response.body}`
**Temporal**: `api_response.body`

Example:
```python
# Store activity result in variable
api_response = await workflow.execute_activity(verify_address_usps, ...)

# Access response fields
if "Error" in api_response.body:
    # Process error
```

### Nested Object Access

**Conductor**: `${verify_addy_usps.output.response.headers.X-Backside-Transport[0]}`
**Temporal**: `api_response.headers.get("X-Backside-Transport", [""])[0]`

Example:
```python
transport_header = api_response.headers.get("X-Backside-Transport", [""])[0] if isinstance(
    api_response.headers.get("X-Backside-Transport"), list
) else api_response.headers.get("X-Backside-Transport", "")
```

### Workflow Secrets

**Conductor**: `${workflow.secrets.post_office_username}`
**Temporal**: Passed as parameter or configuration

Example:
```python
# Option 1: Pass as workflow input
workflow_input = WorkflowInput(
    street="...",
    usps_username="steveandroulakis"  # From config
)

# Option 2: Pass directly to activity (as done in this migration)
api_response = await workflow.execute_activity(
    verify_address_usps,
    args=[input.street, input.city, input.state, input.zip, "steveandroulakis"],
    ...
)
```

---

## Key Architectural Differences

### 1. Execution Model
- **Conductor**: Poll-based task execution with JSON configuration. Tasks are executed by workers polling task queues, orchestrated by the Conductor server.
- **Temporal**: Code-first workflow orchestration with Python. Workflows execute in a sandboxed environment, calling activities that run on workers.

### 2. Data Passing
- **Conductor**: JSONPath expressions with string templates (`${task.output.field}`)
- **Temporal**: Native Python objects with type safety (dataclasses, direct attribute access)

### 3. Control Flow
- **Conductor**: JSON operators (SWITCH with evaluatorType, decisionCases)
- **Temporal**: Native Python constructs (if/elif/else, while loops, try/except)

### 4. Inline Logic
- **Conductor**: INLINE tasks with JavaScript evaluator for simple transformations
- **Temporal**: Workflow helper methods (Python) that execute deterministically within workflow context

### 5. Error Handling
- **Conductor**: TERMINATE tasks with different terminationStatus values (FAILED, COMPLETED)
- **Temporal**:
  - `raise ApplicationError` for workflow failures (FAILED status)
  - `return` statement with structured output for business logic errors (COMPLETED status with error details)

### 6. Type Safety
- **Conductor**: Dynamic JSON types, no compile-time checking
- **Temporal**: Strong typing with Python type hints, dataclasses, and mypy validation

### 7. Debugging
- **Conductor**: View task outputs in Conductor UI, JSON-based logs
- **Temporal**: Python logging, full event history in Temporal UI, can debug with standard Python tools

---

## Activity Mapping Table

| Conductor Task | Task Type | Temporal Activity | Notes |
|----------------|-----------|-------------------|-------|
| verify_addy_usps | HTTP | verify_address_usps | Mock implementation (OAuth transition), returns USPS XML |
| api_success | SWITCH | *(inline if/else)* | Checks X-Backside-Transport header |
| API_fail | TERMINATE | *(raise ApplicationError)* | Workflow fails with error details |
| address_success | SWITCH | *(inline if/else)* | Checks for "Error" in XML |
| get_error_message | INLINE | _extract_error_message() | Workflow helper method (deterministic) |
| address_error | TERMINATE | *(return with error)* | Returns error result (workflow COMPLETED) |
| parse_address_json | INLINE | _parse_address_from_xml() | Workflow helper method (deterministic) |
| terminate_success | TERMINATE | *(return with success)* | Returns success result |

---

## Mock Implementation Notes

This migration uses **REALISTIC MOCK DATA** instead of calling the real USPS API:

**Why?**
- USPS is transitioning to OAuth-based authentication (required by January 2026)
- Legacy XML API used in Conductor workflow is being deprecated
- Mock allows testing without USPS credentials

**What's Mocked?**
- `verify_address_usps` activity returns hardcoded XML responses
- Known valid addresses return USPS-standardized format (all caps)
- Unknown addresses return "Address Not Found" error

**Known Valid Mock Addresses**:
- 1600 Pennsylvania Avenue NW, Washington, DC 20500
- 100 Winchester Circle, Los Gatos, CA 95032
- 1 Apple Park Way, Cupertino, CA 95014

**Future Integration**:
When OAuth credentials are available, replace mock implementation in `activities.py` with real httpx API calls using OAuth authentication.

---

**This comparison was generated automatically during migration.**
For detailed migration decisions, see `CONDUCTOR_MIGRATION_NOTES.md`.

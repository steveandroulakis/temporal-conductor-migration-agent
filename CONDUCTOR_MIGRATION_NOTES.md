# Conductor to Temporal: Migration Notes

**Migration Date**: November 23, 2025
**Original Workflow**: `conductor-definition/check_address.json`
**Complexity**: MEDIUM
**Validation Status**: All checks passed
**Execution Status**: Successfully tested end-to-end

---

## Migration Overview

This document records the decisions, assumptions, and considerations made during the automatic migration from Conductor to Temporal.

## Workflow Characteristics

### Complexity Analysis
- **Max Nesting Depth**: 3 (outer SWITCH → inner SWITCH → task execution)
- **Has Loops**: No
- **Has Parallel Execution**: No
- **Has Dynamic Parallelism**: No
- **Has Sub-workflows**: No
- **Has Nested Switches**: Yes (api_success contains address_success)

### Task Breakdown
- **Total Tasks**: 8
- **HTTP tasks**: 1 → 1 activity (verify_address_usps with mock implementation)
- **SWITCH tasks**: 2 → Nested if/else statements
- **INLINE tasks**: 2 → 2 workflow helper methods
- **TERMINATE tasks**: 3 → ApplicationError + return statements

### Complexity Factors
1. Nested SWITCH tasks (2 levels deep)
2. Multiple TERMINATE tasks with different outcomes (FAILED vs COMPLETED)
3. INLINE tasks with JavaScript XML parsing logic
4. Complex conditional branching based on HTTP response
5. Secret substitution in URI template
6. XML response parsing required

---

## Migration Decisions

### 1. Mock Implementation Decision

**Decision**: Implemented realistic mock data instead of calling real USPS API

**Rationale**:
- USPS is transitioning to OAuth-based authentication (required by January 2026)
- Legacy XML-based API used in original Conductor workflow is being deprecated
- OAuth credentials not available for automated migration
- Mock allows testing without USPS account setup

**Implementation**:
- Created `verify_address_usps` activity with hardcoded valid addresses
- Returns USPS-formatted XML responses (matching real API structure)
- Includes both success and error response formats
- Known valid addresses: White House, Netflix HQ, Apple Park

**Alternative Approaches Considered**:
1. Skip HTTP activity entirely (rejected - would not validate workflow logic)
2. Use placeholder TODO comments (rejected - workflow wouldn't execute)
3. Mock with generic responses (rejected - wouldn't match USPS XML format)

**Future Path**:
When OAuth credentials are available:
1. Replace mock implementation in `activities.py`
2. Add OAuth token acquisition logic
3. Use httpx for real API calls
4. Handle USPS rate limits and error codes

---

### 2. Control Flow Translation

#### Pattern: Nested SWITCH Tasks

**Conductor Pattern**: Outer SWITCH (api_success) with inner SWITCH (address_success) in default case

**Temporal Mechanism**: Nested if/else statements

**Decision Rationale**:
- Python if/else preserves Conductor's branching semantics
- Outer check: API transport header (FAIL FAIL vs OK)
- Inner check: Address validation status (Error in XML vs success)
- Maintains 3-level nesting depth from Conductor

**Code Structure**:
```python
# Level 1: API transport check
if transport_header == "FAIL FAIL":
    raise ApplicationError(...)  # API_fail path

# Level 2: Address validation check (nested)
if "Error" in api_response.body:
    # Level 3: Error handling
    error_message = self._extract_error_message(...)
    return WorkflowOutput(success=False, error_message=...)
else:
    # Level 3: Success handling
    parsed_address = self._parse_address_from_xml(...)
    return WorkflowOutput(success=True, parsed_address=...)
```

---

#### Pattern: INLINE JavaScript to Python Helper Methods

**Conductor Pattern**: INLINE tasks with `evaluatorType: javascript`

**Temporal Mechanism**: Workflow helper methods (deterministic Python)

**Decision Rationale**:
- INLINE tasks perform simple data transformations (XML parsing)
- No external I/O required → Can execute within workflow context
- Implementing as helper methods keeps code deterministic
- Not implemented as activities because:
  - No need for retry/timeout behavior
  - No non-deterministic operations
  - Faster execution (no activity scheduling overhead)

**Tasks Translated**:
1. `get_error_message`: JavaScript string manipulation → `_extract_error_message()` with xml.etree.ElementTree
2. `parse_address_json`: JavaScript XML parsing → `_parse_address_from_xml()` with xml.etree.ElementTree

**Improvement Over Conductor**:
- Used xml.etree.ElementTree instead of string manipulation (safer)
- Added comprehensive error handling for malformed XML
- Added field validation (missing required fields)
- Maintained fallback to string parsing for compatibility

---

#### Pattern: TERMINATE Tasks with Different Status

**Conductor Pattern**: TERMINATE tasks with `terminationStatus: FAILED` or `COMPLETED`

**Temporal Mechanism**:
- FAILED → `raise ApplicationError` (workflow fails)
- COMPLETED with error → `return` structured output with error details
- COMPLETED with success → `return` structured output with data

**Decision Rationale**:
- Temporal distinguishes between:
  1. Workflow execution failures (ApplicationError)
  2. Business logic outcomes (return values)
- API transport failure is an execution failure → ApplicationError
- Address validation error is a business outcome → return with success=False
- Successful validation is a business outcome → return with success=True

**Translation Table**:
| Conductor Task | Status | Temporal Implementation |
|---------------|--------|------------------------|
| API_fail | FAILED | `raise ApplicationError(...)` |
| address_error | COMPLETED | `return WorkflowOutput(success=False, error_message=...)` |
| terminate_success | COMPLETED | `return WorkflowOutput(success=True, parsed_address=...)` |

---

### 3. Activity Design

**Decision**: Created 1 activity from Conductor HTTP task

**Activity Timeout Strategy**:
- **Connection + Read timeout**: Original Conductor: 1000ms + 1000ms = 2s total
- **Temporal timeout**: `start_to_close_timeout=timedelta(seconds=10)`
- **Rationale**: Temporal's timeout includes scheduling, execution, and result return. Increased to 10s to account for worker availability and mock processing.

**Retry Policy Strategy**:
- **Initial interval**: 1 second
- **Maximum interval**: 30 seconds
- **Maximum attempts**: 3
- **Backoff coefficient**: 2.0
- **Rationale**: Conductor workflow had no retry policy configured. Added standard retry for network resilience (even for mocks, to demonstrate pattern).

**Why httpx in dependencies despite mocks?**
- `pyproject.toml` includes `httpx>=0.26.0` dependency
- Rationale: Demonstrates expected dependency for HTTP activities
- When replacing mock with real API, httpx will be needed
- Minimal overhead to include now for future-proofing

---

### 4. Data Type Mapping

**Conductor Input Parameters** → **Temporal Dataclasses**

| Conductor Field | Temporal Field | Type | Rationale |
|----------------|----------------|------|-----------|
| `street` | `WorkflowInput.street` | `str` | Direct mapping |
| `city` | `WorkflowInput.city` | `str` | Direct mapping |
| `state` | `WorkflowInput.state` | `str` | Direct mapping |
| `zip` | `WorkflowInput.zip` | `str` | Direct mapping |

**Conductor Output Parameters** → **Temporal Dataclasses**

Original Conductor output:
```json
{
  "header": "${verify_addy_usps.output.response.headers}",
  "address": "${verify_addy_usps.output.response.body}"
}
```

Temporal output dataclass:
```python
@dataclass
class WorkflowOutput:
    success: bool
    parsed_address: Optional[ParsedAddress] = None
    error_message: Optional[str] = None
```

**Rationale for Restructuring**:
- Conductor returns raw headers and XML body
- Temporal returns **structured, parsed data**
- Benefits:
  - Type safety (ParsedAddress dataclass)
  - Clear success/failure indication
  - Parsed data ready for consumption
  - Error messages extracted from XML
- Consumers don't need to parse XML themselves

---

### 5. XML Parsing Strategy

**Conductor Approach**: JavaScript string manipulation (`indexOf`, `substring`)

**Temporal Approach**: xml.etree.ElementTree with string parsing fallback

**Decision Rationale**:
- ElementTree is safer for XML parsing (handles malformed XML, edge cases)
- Validates XML structure before extracting data
- Raises clear errors for missing fields
- String parsing fallback preserves original Conductor logic if ElementTree fails

**Example Improvement**:
```python
# Conductor JavaScript (get_error_message)
var descriptionIndexStart = xml.indexOf('<Description>')+13;
var descriptionIndexEnd = xml.indexOf('</Description>');
var description = xml.substring(descriptionIndexStart,descriptionIndexEnd);

# Temporal Python (with validation)
root = ET.fromstring(xml_body)
description_elem = root.find(".//Error/Description")
if description_elem is not None and description_elem.text:
    return description_elem.text.strip()
else:
    # Fallback to string parsing + error handling
```

---

### 6. Secrets Management

**Conductor Approach**: `${workflow.secrets.post_office_username}`

**Temporal Approach**: Passed as function parameter with default value

**Decision**:
```python
async def verify_address_usps(
    street: str,
    city: str,
    state: str,
    zip_code: str,
    username: str = "steveandroulakis"  # Default from Conductor analysis
) -> UspsHttpResponse:
```

**Rationale**:
- Default value extracted from conductor-analysis.json
- Can be overridden at workflow start time
- For production: Pass from workflow input or environment config

**Alternative Approaches**:
1. Environment variable (rejected - harder to test multiple values)
2. Workflow input field (considered - adds complexity for users)
3. Activity input with default (chosen - flexible and clear)

---

## Assumptions Made

### 1. Activity Implementations

**Assumption**: Mock implementation is acceptable for USPS API activity

**Context**: USPS OAuth transition requires credentials not available during migration

**Documentation**: Clearly documented in:
- Activity docstring
- README.md (Mock Implementation Details section)
- Migration notes (this document)

**Next Steps for Users**:
- Replace mock with real OAuth implementation when credentials available
- Update `activities.py` with httpx API calls
- Add OAuth token management

---

### 2. Timeout Values

**Assumption**: 10-second activity timeout is sufficient for USPS API call

**Original Conductor**: 1000ms connection + 1000ms read = 2 seconds total

**Temporal Timeout**: 10 seconds (start_to_close_timeout)

**Rationale**:
- Accounts for worker availability, activity scheduling
- Includes mock processing time
- For real API: May need adjustment based on USPS response times

**Recommendation**: Monitor activity durations in production, adjust timeout if needed

---

### 3. Example Input Data

**Assumption**: White House address (1600 Pennsylvania Ave) is suitable default example

**Rationale**:
- Well-known, easily recognized address
- One of the mock valid addresses
- Demonstrates successful validation path
- Used in WORKFLOW_EXECUTION_REPORT.md testing

**Alternative Examples Provided**:
- Netflix HQ: 100 Winchester Circle, Los Gatos, CA
- Apple Park: 1 Apple Park Way, Cupertino, CA

---

### 4. Error Handling Strategy

**Assumption**: Three distinct exit paths are appropriate

**Exit Paths**:
1. **API Transport Failure**: `raise ApplicationError` (workflow FAILED)
2. **Address Validation Error**: `return WorkflowOutput(success=False, error_message=...)` (workflow COMPLETED)
3. **Validation Success**: `return WorkflowOutput(success=True, parsed_address=...)` (workflow COMPLETED)

**Rationale**:
- Matches Conductor's three TERMINATE tasks
- Distinguishes infrastructure failures from business logic outcomes
- Provides structured data for all paths

---

## Known Limitations

### 1. Mock Implementation

**Limitation**: Only 3 addresses are known valid in mock

**Impact**: Any other address returns "Address Not Found" error

**Workaround**: Add more addresses to `known_addresses` dict in `activities.py`

**Future Resolution**: Replace with real USPS API integration

---

### 2. USPS API Authentication

**Limitation**: Original Conductor workflow uses legacy USPS API with username in query string

**Impact**: Authentication method is deprecated (OAuth required by Jan 2026)

**Documentation**: Clearly noted in README.md and activity docstring

**Future Resolution**:
- Implement OAuth token acquisition
- Update activity to use Authorization header
- Handle token refresh and expiration

---

### 3. XML Response Format Dependencies

**Limitation**: Parsing logic depends on USPS XML response structure

**Impact**: If USPS changes XML format, parsing will break

**Mitigation**:
- Used ElementTree for structure validation
- Comprehensive error handling for missing fields
- Fallback to string parsing

**Recommendation**: Monitor USPS API documentation for format changes

---

## Customization Recommendations

### Immediate Customizations Needed

#### 1. Replace Mock Implementation

**Priority**: HIGH (for production use)

**Location**: `check_address_temporal/activities.py`

**Steps**:
1. Implement OAuth token acquisition:
   ```python
   async def get_usps_oauth_token() -> str:
       # OAuth flow with client_id, client_secret
       pass
   ```

2. Replace mock logic with real httpx calls:
   ```python
   async with httpx.AsyncClient() as client:
       token = await get_usps_oauth_token()
       headers = {
           "Authorization": f"Bearer {token}",
           "Content-Type": "application/xml"
       }
       response = await client.post(
           "https://api.usps.com/addresses/v3/address",
           headers=headers,
           data=xml_request,
           timeout=10.0
       )
       return UspsHttpResponse(
           status_code=response.status_code,
           body=response.text,
           headers=dict(response.headers)
       )
   ```

3. Update documentation to remove mock references

---

#### 2. Customize Workflow Input

**Priority**: MEDIUM

**Location**: `check_address_temporal/starter.py`

**Current**:
```python
workflow_input = WorkflowInput(
    street="1600 Pennsylvania Avenue NW",
    city="Washington",
    state="DC",
    zip="20500"
)
```

**Customize to**:
- Accept command-line arguments
- Read from configuration file
- Integrate with your address input source

---

#### 3. Adjust Timeouts

**Priority**: LOW (monitor and adjust as needed)

**Location**: `check_address_temporal/workflow.py`

**Current**:
```python
start_to_close_timeout=timedelta(seconds=10)
```

**Monitor**: Activity duration in Temporal UI

**Adjust**: Based on real USPS API response times

---

### Optional Enhancements

#### 1. Batch Address Validation

**Enhancement**: Validate multiple addresses in parallel

**Implementation**:
```python
@workflow.run
async def run(self, inputs: List[WorkflowInput]) -> List[WorkflowOutput]:
    # Execute activities in parallel
    results = await asyncio.gather(
        *[self._validate_single_address(input) for input in inputs]
    )
    return results
```

**Benefit**: Improved throughput for bulk validation

---

#### 2. Caching for Repeated Addresses

**Enhancement**: Cache validated addresses to avoid duplicate API calls

**Implementation**:
- Use Temporal side effects for caching within workflow
- Implement external cache (Redis) for cross-workflow deduplication

**Benefit**: Reduced API costs, faster execution

---

#### 3. Enhanced Error Reporting

**Enhancement**: Add more detailed error categorization

**Implementation**:
```python
@dataclass
class WorkflowOutput:
    success: bool
    parsed_address: Optional[ParsedAddress] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None  # NEW
    error_type: Optional[str] = None  # NEW (API, VALIDATION, PARSING)
```

**Benefit**: Better error handling in consuming applications

---

#### 4. Monitoring and Metrics

**Enhancement**: Add custom metrics for observability

**Implementation**:
```python
# In activities
activity.logger.info(
    "usps_validation_duration_ms",
    extra={"duration_ms": duration, "result": "success"}
)
```

**Benefit**: Production monitoring and alerting

---

## Future Considerations

### 1. USPS OAuth Integration

**Timeline**: By January 2026 (USPS OAuth requirement)

**Requirements**:
- USPS Developer Portal account
- Client ID and Client Secret
- OAuth token management (acquisition, refresh, expiration)

**Implementation Steps**:
1. Register application on USPS Developer Portal
2. Implement OAuth 2.0 flow
3. Store credentials securely (environment variables, secrets manager)
4. Handle token refresh before expiration
5. Update activity with Authorization header

**Resources**:
- [USPS Web Tools API Documentation](https://www.usps.com/business/web-tools-apis/)

---

### 2. Scalability

**For high-volume workflows, consider**:

1. **Activity Batching**: Validate multiple addresses per activity call
   - Reduces activity overhead
   - May increase activity timeout

2. **Worker Scaling**: Run multiple worker processes
   - Increases parallel activity execution
   - Configure worker count based on load

3. **Temporal Cloud**: Production deployment
   - Managed infrastructure
   - Built-in monitoring and alerting
   - High availability

---

### 3. Testing

**Add comprehensive test coverage**:

1. **Unit Tests** (activities):
   ```python
   @pytest.mark.asyncio
   async def test_verify_address_usps_known_address():
       result = await verify_address_usps(
           "1600 Pennsylvania Avenue NW", "Washington", "DC", "20500"
       )
       assert result.status_code == 200
       assert "1600 PENNSYLVANIA AVE NW" in result.body
   ```

2. **Integration Tests** (workflows):
   ```python
   @pytest.mark.asyncio
   async def test_workflow_valid_address():
       async with await WorkflowEnvironment.start_time_skipping() as env:
           # Test workflow with mock time
           pass
   ```

3. **End-to-End Tests**: Full worker + starter execution

---

## Validation Results

See `VALIDATION_REPORT.md` for detailed validation results.

**Summary**:
- Syntax Validation: PASS
- Type Checking (mypy --strict): PASS (1 fix applied automatically)
- Sandbox Compliance: PASS
- Configuration: PASS
- Activity Signatures: PASS

**Fixes Applied During Validation**:
1. Dict type parameters added to query method return type

---

## Execution Test Results

See `WORKFLOW_EXECUTION_REPORT.md` for detailed execution test results.

**Summary**:
- Worker startup: PASS
- Workflow execution: PASS
- Activity execution: PASS (mock implementation)
- XML parsing: PASS
- Result validation: PASS

**Tested Scenarios**:
- Valid address (White House) → Successfully validated and standardized

**Not Yet Tested** (requires additional test scenarios):
- API transport failure (X-Backside-Transport = "FAIL FAIL")
- Address validation error (XML contains "Error" tag)
- Invalid/unknown addresses

---

## References

- Original Conductor workflow: `conductor-definition/check_address.json`
- Conductor Primitives Reference: [conductor-migration/conductor-primitives-reference.md](./conductor-migration/conductor-primitives-reference.md)
- Conductor Architecture Guide: [conductor-migration/conductor-architecture.md](./conductor-migration/conductor-architecture.md)
- Temporal Python SDK: https://docs.temporal.io/develop/python
- USPS API Documentation: https://www.usps.com/business/web-tools-apis/

---

**Migration Tool Version**: 1.0
**Generated**: November 23, 2025
**Agents**: Conductor-to-Temporal 8-Agent Sequential Pipeline

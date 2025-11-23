# check_address_temporal Module Documentation

This module contains the Temporal workflow implementation for the USPS Address Validation workflow, migrated from the Conductor `check_address` workflow definition.

## Module Structure

### shared.py
Data models (dataclasses) for workflow and activity inputs/outputs.

**Exports**:
- `WorkflowInput`: Input parameters for the workflow (street, city, state, zip)
- `ParsedAddress`: Validated and parsed address from USPS
- `WorkflowOutput`: Output from the workflow (success flag, parsed address, or error message)
- `UspsHttpRequest`: Input for USPS API HTTP activity
- `UspsHttpResponse`: Output from USPS API HTTP activity

### activities.py
Activity implementations for USPS address validation.

**Exports**:
- `verify_address_usps`: Mock USPS Address Validation activity that returns realistic XML responses

**Note**: This activity uses MOCK data instead of the real USPS API due to the OAuth transition (required by January 2026). The mock includes known valid addresses and returns USPS-formatted XML responses.

### workflow.py
Workflow orchestration for address validation.

**Exports**:
- `CheckAddressWorkflow`: Main workflow class that:
  - Calls USPS API activity (mock implementation)
  - Checks API transport status
  - Validates address from XML response
  - Parses validated address or extracts error message
  - Returns structured result with success/error indication

**Key Features**:
- Nested conditional branching (3 levels deep)
- XML parsing with ElementTree
- Multiple exit paths (API failure, validation error, success)
- Comprehensive error handling and logging

### worker.py
Worker registration and execution.

**Entry Point**: `worker:main`

**Usage**: `uv run worker`

### starter.py
Workflow starter client.

**Entry Point**: `starter:main`

**Usage**: `uv run starter`

### interact.py
Workflow interaction client for queries.

**Entry Point**: `interact:main`

**Usage**: `uv run interact query <workflow-id> get_status`

## Usage

See the main project PROJECT_README.md for complete setup and usage instructions.

## Development

When modifying this module:
1. Maintain strict type hints (mypy --strict compliance)
2. Update docstrings for all public functions
3. Run validation: `mypy check_address_temporal --strict --ignore-missing-imports`
4. Test with worker and starter: `uv run worker` and `uv run starter`

## Mock Implementation

This module uses **REALISTIC MOCK DATA** for the USPS API:

**Known Valid Addresses**:
- 1600 Pennsylvania Avenue NW, Washington, DC 20500
- 100 Winchester Circle, Los Gatos, CA 95032
- 1 Apple Park Way, Cupertino, CA 95014

**Mock Response Format**: USPS-formatted XML matching real API structure

**Future Integration**: When USPS OAuth credentials are available, replace the mock implementation in `activities.py` with real httpx API calls.

## Migration Context

Migrated from Conductor workflow: `conductor-definition/check_address.json`

**Original Conductor Tasks**:
- 1 HTTP task → `verify_address_usps` activity (with mock)
- 2 SWITCH tasks → Nested if/else conditional logic
- 2 INLINE tasks → Workflow helper methods (`_extract_error_message`, `_parse_address_from_xml`)
- 3 TERMINATE tasks → ApplicationError + return statements

---

**Migrated from Conductor by Conductor-to-Temporal Migration Tool**
**Migration Date**: November 23, 2025

# CheckAddress Workflow - Temporal Migration

Migrated from Netflix Conductor workflow definition to Temporal Python SDK.

**Original Conductor Workflow**: `conductor-definition/check_address.json`
**Migration Date**: November 23, 2025
**Complexity**: MEDIUM (Max nesting depth: 3)
**Workflow Execution Status**: VALIDATED (Successfully tested end-to-end)

## Overview

This project implements the **CheckAddress** workflow using Temporal's Python SDK. The workflow was automatically migrated from a Conductor JSON definition.

### Workflow Description

The USPS Address Validation workflow verifies US postal addresses by calling the USPS Address Validation API. The USPS maintains a database of 160 million addresses in the USA. This workflow returns either a USPS-standardized version of the address (typically in all CAPS with abbreviated street suffixes) or an error message if the address cannot be validated.

**IMPORTANT NOTE ABOUT MOCK IMPLEMENTATION**: This workflow uses **REALISTIC MOCK DATA** instead of calling the real USPS API. The USPS is transitioning to OAuth-based authentication (required by January 2026), and the legacy API used by the original Conductor workflow is being deprecated. The mock implementation includes known valid addresses and realistic USPS-formatted XML responses for testing purposes.

### Control Flow

This workflow implements:
- 1 HTTP activity (USPS API call with mock data)
- 2 nested SWITCH tasks (conditional branches for API status and address validation)
- 2 INLINE tasks (XML parsing logic translated to Python)
- 3 TERMINATE outcomes (API failure, validation error, success)

Key features:
- Nested conditional branching (3 levels deep)
- XML response parsing with ElementTree
- Multiple exit paths with different outcomes
- Comprehensive error handling and logging

## Prerequisites

### Required Software

1. **Python 3.11+**
   ```bash
   python3 --version  # Should show 3.11 or higher
   ```

2. **UV Package Manager**
   ```bash
   # macOS
   brew install uv

   # Linux/macOS (curl)
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Temporal CLI and Dev Server**
   ```bash
   # macOS
   brew install temporal

   # Linux/Windows: Download from https://temporal.io/download
   ```

### Temporal Server

Start the Temporal dev server:
```bash
temporal server start-dev
```

The dev server provides:
- Temporal server (localhost:7233)
- Web UI (http://localhost:8233)
- In-memory persistence

## Quick Start

### 1. Install Dependencies

Run the automated setup script:
```bash
chmod +x setup.sh  # Make executable
./setup.sh
```

Or manually:
```bash
uv venv
uv add temporalio httpx
uv add --dev mypy ruff
uv sync --all-extras
```

### 2. Start the Worker

In a terminal window:
```bash
uv run worker
```

You should see:
```
Worker ready — polling task queue: check-address-task-queue
```

Keep this terminal running.

### 3. Execute the Workflow

In a new terminal window:
```bash
uv run starter
```

The starter will:
- Connect to Temporal
- Start the workflow with example address (1600 Pennsylvania Avenue NW, Washington, DC)
- Display the workflow URL
- Wait for completion
- Show the validated address result

### 4. Monitor in Web UI

Open the workflow in your browser:
```
http://localhost:8233
```

Navigate to your workflow to see:
- Workflow execution history
- Activity results
- Current status
- Complete event timeline

## Project Structure

```
check_address_temporal/
├── check_address_temporal/          # Main package directory
│   ├── __init__.py                  # Package marker
│   ├── shared.py                    # Data models (dataclasses)
│   ├── activities.py                # Activity implementations (mock USPS API)
│   ├── workflow.py                  # Workflow definition
│   ├── worker.py                    # Worker registration
│   ├── starter.py                   # Workflow starter
│   └── interact.py                  # Workflow interaction client (Queries)
├── pyproject.toml                   # Project configuration
├── setup.sh                         # Automated setup script
├── PROJECT_README.md                # This file
├── CONDUCTOR_COMPARISON.md          # Conductor vs Temporal mapping
├── CONDUCTOR_MIGRATION_NOTES.md     # Migration decisions
├── VALIDATION_REPORT.md             # Code validation results
└── WORKFLOW_EXECUTION_REPORT.md     # Execution test results
```

### Module Overview

- **shared.py**: Dataclass definitions for workflow inputs, outputs, and activity data
- **activities.py**: USPS address validation activity with realistic mock responses
- **workflow.py**: Workflow orchestration with nested conditional logic
- **worker.py**: Worker process that executes workflows and activities
- **starter.py**: Client for starting workflow executions
- **interact.py**: Client for querying workflow status

## Mock Implementation Details

This workflow uses **REALISTIC MOCK DATA** instead of calling the real USPS API.

### Why Mock Data?

The USPS is transitioning to OAuth-based authentication (required by January 2026). The legacy XML-based API used in the original Conductor workflow is being deprecated. To provide a working demonstration without requiring USPS API credentials, this migration includes realistic mock responses.

### Known Valid Mock Addresses

The mock implementation includes these valid addresses for testing:

| Input Address | Validated Output |
|---------------|------------------|
| 1600 Pennsylvania Avenue NW, Washington, DC | 1600 PENNSYLVANIA AVE NW, WASHINGTON, DC 20500 |
| 100 Winchester Circle, Los Gatos, CA | 100 WINCHESTER CIR, LOS GATOS, CA 95032 |
| 1 Apple Park Way, Cupertino, CA | 1 APPLE PARK WAY, CUPERTINO, CA 95014 |

Any other address will return a "Address Not Found" error, simulating the USPS validation error response.

### Mock Response Format

The mock implementation returns USPS-formatted XML responses:

**Success Response**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<AddressValidateResponse>
    <Address>
        <Address2>1600 PENNSYLVANIA AVE NW</Address2>
        <City>WASHINGTON</City>
        <State>DC</State>
        <Zip5>20500</Zip5>
        <Zip4></Zip4>
    </Address>
</AddressValidateResponse>
```

**Error Response**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<AddressValidateResponse>
    <Address>
        <Error>
            <Number>-2147219401</Number>
            <Source>clsAMS</Source>
            <Description>Address Not Found.</Description>
        </Error>
    </Address>
</AddressValidateResponse>
```

## Testing the Workflow

### Test Valid Address

The default starter configuration uses the White House address:

```bash
uv run starter
```

Expected output:
```
Validated Address:
  Street: 1600 PENNSYLVANIA AVE NW
  City:   WASHINGTON
  State:  DC
  ZIP:    20500
```

### Test Invalid Address

To test with an invalid address, edit `check_address_temporal/starter.py`:

```python
workflow_input = WorkflowInput(
    street="123 Fake Street",
    city="NowhereVille",
    state="XX",
    zip="00000"
)
```

Expected output:
```
Workflow completed with validation error:
Error: Address Not Found.
```

### Query Workflow Status

While a workflow is running, you can query its status:

```bash
uv run interact query <workflow-id> get_status
```

This returns the current workflow status (started, validating, completed, etc.).

## Configuration

### Workflow Timeouts

The workflow has the following timeout configuration:
- **Execution timeout**: 1 hour (configurable in starter.py)
- **Activity timeout**: 10 seconds (start_to_close_timeout in workflow.py)

To adjust timeouts, edit the timeout parameters in `check_address_temporal/workflow.py`:
```python
start_to_close_timeout=timedelta(seconds=10)  # Modify as needed
```

### Task Queue

The worker and starter use task queue: **check-address-task-queue**

To change the task queue:
1. Update `worker.py`: `task_queue="new-task-queue"`
2. Update `starter.py`: `task_queue="new-task-queue"`

### Workflow Input

To customize workflow input, edit `check_address_temporal/starter.py`:
```python
workflow_input = WorkflowInput(
    street="100 Winchester Circle",
    city="Los Gatos",
    state="CA",
    zip="95032"
)
```

### Activity Retry Policy

The workflow uses exponential backoff retry for the USPS API activity:
- Initial interval: 1 second
- Maximum interval: 30 seconds
- Maximum attempts: 3
- Backoff coefficient: 2.0

## Troubleshooting

### Worker Won't Start

**Error**: `Cannot connect to Temporal server`

**Solution**: Ensure Temporal dev server is running:
```bash
temporal server start-dev
```

---

**Error**: `No module named 'temporalio'`

**Solution**: Install dependencies:
```bash
uv sync --all-extras
```

---

**Error**: `console script not found: worker`

**Solution**: Ensure `[tool.uv]` section with `package = true` is in `pyproject.toml`, then:
```bash
uv sync --all-extras
```

### Workflow Fails to Start

**Error**: `Activity verify_address_usps not found`

**Solution**: Ensure worker is running before starting workflow.

---

**Error**: `Workflow execution timeout`

**Solution**: Increase timeout in starter.py:
```python
execution_timeout=timedelta(hours=2)  # Increase as needed
```

### Type Checking Issues

To run type checking:
```bash
mypy check_address_temporal --strict --ignore-missing-imports
```

If errors occur, see `VALIDATION_REPORT.md` for guidance.

### Validation Results

The workflow has been validated and tested successfully:

**Code Validation** (see VALIDATION_REPORT.md):
- Syntax validation: PASS
- Type checking (mypy --strict): PASS
- Workflow sandbox compliance: PASS
- Configuration validation: PASS

**Execution Testing** (see WORKFLOW_EXECUTION_REPORT.md):
- End-to-end workflow execution: PASS
- Worker startup: PASS
- Activity execution: PASS
- XML parsing: PASS
- Result validation: PASS

## Development

### Running Tests

Tests can be added in a `tests/` directory using pytest:
```bash
uv add --dev pytest
pytest tests/
```

### Code Quality

This project follows strict Python standards:
- **Type hints**: All functions have complete type annotations
- **Docstrings**: Comprehensive documentation for all public APIs
- **Code style**: PEP 8 compliant

Run linting:
```bash
uv add --dev ruff
ruff check check_address_temporal/
```

## Migration Notes

This project was automatically migrated from Conductor. See:
- **CONDUCTOR_COMPARISON.md** - Side-by-side Conductor vs Temporal examples
- **CONDUCTOR_MIGRATION_NOTES.md** - Migration decisions and recommendations

### Key Differences from Conductor

**Control Flow Translation**:
- Conductor SWITCH tasks → Python if/elif/else statements
- Conductor INLINE JavaScript tasks → Python helper methods
- Conductor TERMINATE tasks → Python return statements or ApplicationError

**Data Passing**:
- Conductor `${workflow.input.street}` → Temporal `input.street`
- Conductor `${verify_addy_usps.output.response.body}` → Temporal `api_response.body`

**Error Handling**:
- Conductor TERMINATE with FAILED → Temporal ApplicationError (workflow fails)
- Conductor TERMINATE with COMPLETED (but error) → Temporal structured return with error details

**XML Parsing**:
- Conductor JavaScript string manipulation → Temporal Python xml.etree.ElementTree

**API Integration**:
- Conductor HTTP task with real USPS API → Temporal activity with mock responses

## Future: Real USPS API Integration

When USPS OAuth credentials are available, replace the mock implementation:

1. **Update activities.py**:
   - Replace mock implementation with real httpx API calls
   - Add OAuth authentication headers
   - Handle USPS API rate limits

2. **OAuth Configuration**:
   ```python
   # Add OAuth token acquisition
   async def get_usps_oauth_token() -> str:
       # Implement OAuth flow
       pass

   # Use token in API request
   headers = {
       "Authorization": f"Bearer {token}",
       "Content-Type": "application/xml"
   }
   ```

3. **Update Documentation**:
   - Remove mock implementation notes
   - Add USPS API credential setup instructions
   - Document OAuth token management

## Additional Resources

- [Temporal Python SDK Documentation](https://docs.temporal.io/develop/python)
- [Temporal Python SDK API Reference](https://python.temporal.io/)
- [Temporal Learning Portal](https://learn.temporal.io/)
- [Conductor to Temporal Migration Guide](./conductor-migration/)
- [USPS Web Tools API Documentation](https://www.usps.com/business/web-tools-apis/)

## Support

For migration-specific questions:
- Review `CONDUCTOR_MIGRATION_NOTES.md` for decisions made during migration
- Check `VALIDATION_REPORT.md` for code quality notes
- Check `WORKFLOW_EXECUTION_REPORT.md` for execution test results
- Consult the Conductor migration documentation in `conductor-migration/`

---

**Generated by Conductor to Temporal Migration Tool**
**Migration Date**: November 23, 2025
**Validation Status**: All checks passed
**Execution Status**: Successfully tested end-to-end

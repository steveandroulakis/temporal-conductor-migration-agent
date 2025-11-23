#!/bin/bash
set -e

echo "======================================"
echo "  Temporal Workflow Setup"
echo "======================================"
echo ""
echo "Setting up: schema_approval"
echo ""

# Unset Temporal environment variables that might interfere
echo "Clearing Temporal environment variables..."
unset TEMPORAL_CLI_ADDRESS TEMPORAL_CLI_NAMESPACE TEMPORAL_CLI_TLS_CERT \
      TEMPORAL_CLI_TLS_KEY TEMPORAL_CERT_PATH TEMPORAL_KEY_PATH \
      TEMPORAL_NAMESPACE TEMPORAL_ADDRESS TEMPORAL_API_KEY \
      TEMPORAL_HOST_PORT TEMPORAL_TLS_CERT TEMPORAL_TLS_KEY

# Check Python version
echo "Checking Python version..."
python3 --version | grep -q 'Python 3\.1[1-9]\|Python 3\.[2-9][0-9]' || {
    echo "Error: Python 3.11+ required"
    echo "   Current version: $(python3 --version)"
    exit 1
}
echo "Python version OK"

# Check UV installed
echo "Checking UV installation..."
command -v uv >/dev/null 2>&1 || {
    echo "Error: UV not installed"
    echo "   Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
}
echo "UV installed"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
uv venv

# Install dependencies
echo ""
echo "Installing dependencies..."
uv add temporalio

# Install dev dependencies
echo "Installing dev dependencies..."
uv add --dev mypy ruff

# Sync all dependencies and install entry points
echo ""
echo "Syncing all dependencies and installing entry points..."
uv sync --all-extras

# Verify dependencies installed
echo ""
echo "Verifying dependencies..."
uv pip list | grep -E "(temporalio|mypy)" || {
    echo "Error: Required dependencies missing"
    exit 1
}
echo "All dependencies installed"

# Run syntax validation
echo ""
echo "Validating Python syntax..."
python3 -m py_compile schema_approval_temporal/*.py || {
    echo "Syntax validation failed"
    exit 1
}
echo "Syntax validation passed"

# Run type checking
echo ""
echo "Running type checking..."
mypy schema_approval_temporal --strict --ignore-missing-imports || {
    echo "Type checking found issues (see output above)"
    echo "   Review VALIDATION_REPORT.md for details"
    # Don't exit - type errors are warnings, not blockers
}

echo ""
echo "======================================"
echo "  Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start Temporal dev server (in separate terminal):"
echo "   temporal server start-dev"
echo ""
echo "2. Start the worker (in separate terminal):"
echo "   uv run worker"
echo ""
echo "3. Execute the workflow:"
echo "   uv run starter"
echo ""
echo "4. Monitor in Web UI:"
echo "   http://localhost:8233"
echo ""
echo "See README.md for detailed instructions."
echo ""

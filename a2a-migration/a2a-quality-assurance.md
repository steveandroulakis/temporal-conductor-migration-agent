# A2A Quality Assurance Guide

> **Part of the [A2A Project Generation Guide](./README.md)**

This document defines validation procedures and success criteria for generated A2A + Temporal projects.

---

## Validation Phases

### Phase 1: Syntax Validation

Verify all Python files are syntactically correct:

```bash
# Check all Python files
python3 -m py_compile shared/__init__.py
python3 -m py_compile shared/types.py
python3 -m py_compile {agent}_agent/__init__.py
python3 -m py_compile {agent}_agent/agent_card.py
python3 -m py_compile {agent}_agent/activities.py
python3 -m py_compile {agent}_agent/workflow.py
python3 -m py_compile {agent}_agent/gateway.py
python3 -m py_compile {agent}_agent/worker.py
```

**Success**: All files compile without errors.

---

### Phase 2: Type Checking

Run strict type checking:

```bash
# Run mypy with strict mode
mypy --strict shared/ {agent}_agent/
```

**Success**: Zero type errors.

**Common issues**:
- Missing type annotations on functions
- Using `Any` instead of specific types
- Incompatible types in assignments

---

### Phase 3: Import Validation

Verify all imports resolve correctly:

```bash
# Test imports
python3 -c "from shared.types import *"
python3 -c "from {agent}_agent.agent_card import AGENT_CARD"
python3 -c "from {agent}_agent.activities import *"
python3 -c "from {agent}_agent.workflow import *"
```

**Success**: All imports succeed without errors.

---

### Phase 4: Workflow Sandbox Compliance

Verify workflows don't import non-deterministic code directly:

```bash
# This should NOT fail with sandbox violations
python3 -c "from {agent}_agent.workflow import {WorkflowClass}"
```

**Success**: Workflow imports without sandbox violations.

**Check for violations**:
- Activities importing httpx, requests, etc.
- Importing `random`, `datetime.datetime.now()`
- File I/O operations in workflow code

---

### Phase 5: Agent Card Validation

Verify Agent Cards are valid:

```python
# validate_agent_cards.py
from a2a.types import AgentCard
import json

def validate_agent_card(module_path: str) -> bool:
    """Validate an agent card module."""
    import importlib
    module = importlib.import_module(module_path)
    card = getattr(module, 'AGENT_CARD')

    # Check it's a valid AgentCard
    assert isinstance(card, AgentCard), "AGENT_CARD must be AgentCard type"

    # Check required fields
    assert card.name, "Agent must have a name"
    assert card.description, "Agent must have a description"
    assert card.url, "Agent must have a URL"
    assert len(card.skills) > 0, "Agent must have at least one skill"

    # Check skills have required fields
    for skill in card.skills:
        assert skill.id, "Skill must have an ID"
        assert skill.name, "Skill must have a name"
        assert skill.description, "Skill must have a description"

    return True
```

**Success**: All agent cards validate.

---

### Phase 6: Port and Queue Uniqueness

Verify no conflicts:

```python
# validate_ports.py
def validate_ports_and_queues(agents: list[dict]) -> bool:
    """Validate ports and task queues are unique."""
    ports = [a['port'] for a in agents]
    queues = [a['task_queue'] for a in agents]

    assert len(ports) == len(set(ports)), f"Duplicate ports: {ports}"
    assert len(queues) == len(set(queues)), f"Duplicate queues: {queues}"

    return True
```

**Success**: All ports and task queues are unique.

---

### Phase 7: Gateway Startup Test

Verify gateways can start:

```bash
# Start gateway (should not error immediately)
timeout 5 python3 -m {agent}_agent.gateway || [ $? -eq 124 ]
```

**Success**: Gateway starts without immediate errors.

---

### Phase 8: Worker Registration Test

Verify workers can start:

```bash
# Start worker (should not error immediately)
timeout 5 python3 -m {agent}_agent.worker || [ $? -eq 124 ]
```

**Success**: Worker starts without immediate errors.

---

## End-to-End Validation

### Full System Test

```bash
#!/bin/bash
# e2e_test.sh

set -e

echo "=== Starting E2E Test ==="

# 1. Check Temporal server
if ! temporal operator cluster health 2>/dev/null; then
    echo "Starting Temporal server..."
    temporal server start-dev &
    sleep 5
fi

# 2. Install dependencies
echo "Installing dependencies..."
uv sync

# 3. Start all workers
echo "Starting workers..."
for agent in restaurant_finder taco_shop; do
    uv run python -m ${agent}_agent.worker &
done
sleep 3

# 4. Start all gateways
echo "Starting gateways..."
for agent in restaurant_finder taco_shop; do
    uv run python -m ${agent}_agent.gateway &
done
sleep 3

# 5. Verify agent cards
echo "Verifying agent cards..."
curl -s http://localhost:8000/.well-known/agent.json | jq .name
curl -s http://localhost:8001/.well-known/agent.json | jq .name

# 6. Run demo starter
echo "Running demo..."
uv run python starter.py

# 7. Cleanup
echo "Cleaning up..."
pkill -f "python -m.*_agent"

echo "=== E2E Test Complete ==="
```

---

## Success Criteria Checklist

### Project Structure
- [ ] All required directories exist
- [ ] All required files exist
- [ ] `pyproject.toml` has correct dependencies
- [ ] `pyproject.toml` has `[tool.uv] package = true`

### Code Quality
- [ ] All files pass syntax validation
- [ ] `mypy --strict` passes with zero errors
- [ ] No sandbox violations in workflows
- [ ] All imports resolve correctly

### A2A Compliance
- [ ] All agent cards are valid `AgentCard` types
- [ ] Skill IDs are consistent across card and gateway
- [ ] Ports are unique per agent
- [ ] Task queues are unique per agent
- [ ] URLs match configured ports

### Temporal Compliance
- [ ] Workflows use `@workflow.defn` decorator
- [ ] Activities use `@activity.defn` decorator
- [ ] RetryPolicy imported from `temporalio.common`
- [ ] Activity arguments match function signatures
- [ ] Timeouts configured for all activities

### Runtime Validation
- [ ] Gateways start without errors
- [ ] Workers start without errors
- [ ] Agent cards accessible at `/.well-known/agent.json`
- [ ] A2A tasks can be sent and received
- [ ] Cross-agent communication works

### Documentation
- [ ] README.md is comprehensive
- [ ] Architecture diagram included
- [ ] Running instructions are clear
- [ ] All agents documented

---

## Validation Script

```python
#!/usr/bin/env python3
"""validate_project.py - Validate generated A2A project."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], check: bool = True) -> tuple[int, str]:
    """Run command and return exit code and output."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def validate_syntax(project_dir: Path) -> bool:
    """Validate Python syntax."""
    print("Checking syntax...")
    for py_file in project_dir.rglob("*.py"):
        code, output = run_command(["python3", "-m", "py_compile", str(py_file)])
        if code != 0:
            print(f"  FAIL: {py_file}")
            print(output)
            return False
        print(f"  OK: {py_file}")
    return True


def validate_types(project_dir: Path) -> bool:
    """Run mypy type checking."""
    print("Checking types...")
    code, output = run_command(["mypy", "--strict", str(project_dir)])
    if code != 0:
        print(f"  FAIL: mypy errors")
        print(output)
        return False
    print("  OK: types valid")
    return True


def validate_imports(project_dir: Path, agents: list[str]) -> bool:
    """Validate all imports work."""
    print("Checking imports...")

    # Check shared types
    code, output = run_command([
        "python3", "-c", "from shared.types import *"
    ])
    if code != 0:
        print(f"  FAIL: shared.types")
        return False

    # Check each agent
    for agent in agents:
        for module in ["agent_card", "activities", "workflow", "gateway", "worker"]:
            code, output = run_command([
                "python3", "-c", f"from {agent}_agent.{module} import *"
            ])
            if code != 0:
                print(f"  FAIL: {agent}_agent.{module}")
                return False
        print(f"  OK: {agent}_agent")

    return True


def main() -> int:
    """Run all validations."""
    project_dir = Path(".")
    agents = ["restaurant_finder", "taco_shop"]  # Update as needed

    results = {
        "syntax": validate_syntax(project_dir),
        "types": validate_types(project_dir),
        "imports": validate_imports(project_dir, agents),
    }

    print("\n=== Validation Summary ===")
    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check}: {status}")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## Continuous Validation

Add to development workflow:

```bash
# Run before committing
./validate_project.py

# Run full E2E before release
./e2e_test.sh
```

---

## Related Documentation

- [A2A Troubleshooting](./a2a-troubleshooting.md) - Common issues and fixes
- [A2A Patterns Reference](./a2a-patterns-reference.md) - Implementation patterns

---

**[← Back to SDK Integration](./a2a-sdk-integration.md)** | **[→ Troubleshooting](./a2a-troubleshooting.md)**

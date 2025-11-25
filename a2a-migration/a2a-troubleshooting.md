# A2A + Temporal Troubleshooting Guide

> **Part of the [A2A Project Generation Guide](./README.md)**

This document provides solutions to common issues encountered when building A2A + Temporal systems.

---

## Common Issues

### 1. Workflow Sandbox Violation

**Symptom**:
```
temporalio.worker.workflow_sandbox._restrictions.RestrictedWorkflowAccessError:
Cannot access 'httpx' from workflow code
```

**Cause**: Importing modules with side effects (HTTP clients, random, etc.) directly in workflow code.

**Solution**: Use passthrough imports for activities:

```python
# workflow.py

# WRONG - causes sandbox violation
from myproject.activities import my_activity  # activities.py imports httpx

# CORRECT - use passthrough imports
with workflow.unsafe.imports_passed_through():
    from myproject.activities import my_activity
```

---

### 2. Wrong RetryPolicy Import

**Symptom**:
```
ImportError: cannot import name 'RetryPolicy' from 'temporalio.workflow'
```

**Cause**: RetryPolicy is in `temporalio.common`, not `temporalio.workflow`.

**Solution**:

```python
# WRONG
from temporalio.workflow import RetryPolicy

# CORRECT
from temporalio.common import RetryPolicy
```

---

### 3. Console Script Async Main Error

**Symptom**:
```
RuntimeWarning: coroutine 'main' was never awaited
```

**Cause**: Console scripts (in pyproject.toml) require synchronous entry points.

**Solution**:

```python
# worker.py

# WRONG - async main won't work as console script entry point
async def main():
    ...

# CORRECT - wrap async in sync
def main():
    asyncio.run(async_main())

async def async_main():
    ...
```

```toml
# pyproject.toml
[project.scripts]
worker = "myproject.worker:main"  # Points to sync function
```

---

### 4. Agent Card Not Found

**Symptom**:
```
404 Not Found at /.well-known/agent.json
```

**Cause**: Routes not added to FastAPI app.

**Solution**: Ensure `add_routes_to_app` or `build()` is called:

```python
# WRONG - routes not added
app = FastAPI()
a2a_app = A2AFastAPIApplication(agent_card=CARD, http_handler=handler)
# Missing: a2a_app.add_routes_to_app(app)

# CORRECT - use build()
a2a_app = A2AFastAPIApplication(agent_card=CARD, http_handler=handler)
app = a2a_app.build()  # Routes added automatically
```

---

### 5. Port Already in Use

**Symptom**:
```
OSError: [Errno 48] Address already in use
```

**Cause**: Another process using the port, or previous gateway didn't shut down.

**Solution**:

```bash
# Find and kill process on port
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn myagent.gateway:app --port 8001
```

---

### 6. Temporal Client Connection Failed

**Symptom**:
```
grpc._channel._InactiveRpcError: <_InactiveRpcError of RPC that terminated with:
    status = StatusCode.UNAVAILABLE
```

**Cause**: Temporal server not running or wrong address.

**Solution**:

```bash
# Check if Temporal is running
temporal operator cluster health

# Start Temporal server
temporal server start-dev

# Or check address in code
client = await Client.connect("localhost:7233")  # Verify address
```

---

### 7. A2A Task Never Completes

**Symptom**: Task stays in `working` state forever.

**Cause**: Event queue not sending completion event.

**Solution**: Ensure executor sends completion event:

```python
async def execute(self, context, event_queue):
    result = await self.do_work()

    # MUST send completion event
    await event_queue.enqueue_event(
        TaskArtifactUpdateEvent(
            artifacts=[DataArtifact(data=result)]
        )
    )
```

---

### 8. Activity Timeout

**Symptom**:
```
temporalio.exceptions.ActivityError: activity timed out
```

**Cause**: Activity takes longer than configured timeout.

**Solution**: Increase timeout or optimize activity:

```python
# Increase timeout
result = await workflow.execute_activity(
    my_activity,
    input_data,
    start_to_close_timeout=timedelta(minutes=5),  # Increase from default
)
```

---

### 9. Cross-Agent Communication Fails

**Symptom**: A2A task to another agent returns error.

**Cause**: Various - target agent not running, wrong URL, network issues.

**Diagnostic steps**:

```bash
# 1. Check target agent is running
curl http://localhost:8001/.well-known/agent.json

# 2. Check agent card URL matches
cat {agent}_agent/agent_card.py | grep url

# 3. Test manual A2A call
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tasks/send","id":"test","params":{"message":{"role":"user","parts":[{"type":"text","text":"{}"}]}}}'
```

---

### 10. Type Errors with A2A SDK

**Symptom**:
```
ValidationError: 1 validation error for AgentCard
skills -> 0 -> inputSchema
  Input should be a valid dictionary [type=dict_type, ...]
```

**Cause**: Pydantic v2 strict typing.

**Solution**: Ensure correct types:

```python
# WRONG - list instead of dict
skills=[
    AgentSkill(
        inputSchema=["string", "integer"]  # Wrong type
    )
]

# CORRECT - proper JSON Schema
skills=[
    AgentSkill(
        inputSchema={
            "type": "object",
            "properties": {
                "param": {"type": "string"}
            }
        }
    )
]
```

---

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# For Temporal
logging.getLogger("temporalio").setLevel(logging.DEBUG)

# For A2A SDK
logging.getLogger("a2a").setLevel(logging.DEBUG)
```

### Check Workflow History

```bash
# View workflow execution details
temporal workflow show --workflow-id a2a-task-123
```

### Test A2A Protocol Manually

```bash
# Fetch agent card
curl http://localhost:8000/.well-known/agent.json | jq

# Send task
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "id": "1",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "{}"}]
      }
    }
  }' | jq

# Get task status
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "id": "2",
    "params": {"id": "task-id-here"}
  }' | jq
```

---

## Quick Diagnostic Checklist

1. **Temporal server running?**
   ```bash
   temporal operator cluster health
   ```

2. **Workers started?**
   ```bash
   ps aux | grep "python.*worker"
   ```

3. **Gateways accessible?**
   ```bash
   curl http://localhost:8000/.well-known/agent.json
   ```

4. **Logs showing errors?**
   ```bash
   tail -f worker.log gateway.log
   ```

5. **Workflow execution visible?**
   ```bash
   temporal workflow list
   ```

---

## Getting Help

If issues persist:

1. Check [A2A SDK source](../tmp-resources/a2a-python/) for implementation details
2. Review [Temporal Python SDK docs](https://docs.temporal.io/dev-guide/python)
3. Check generated code against [Patterns Reference](./a2a-patterns-reference.md)

---

## Related Documentation

- [A2A Quality Assurance](./a2a-quality-assurance.md) - Validation procedures
- [A2A Patterns Reference](./a2a-patterns-reference.md) - Correct patterns

---

**[← Back to Quality Assurance](./a2a-quality-assurance.md)** | **[Back to Main Guide](./README.md)**

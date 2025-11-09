# Conductor to Temporal: Architecture Reference

> **Part of the [Conductor to Temporal Migration Guide](./README.md)**

This document provides a comprehensive reference for understanding the architectural differences between Netflix Conductor and Temporal, and how Conductor concepts map to Temporal implementations.

---

## Core Architectural Shift

| Aspect | Conductor | Temporal |
|--------|-----------|----------|
| **Definition Style** | Declarative JSON DSL | Imperative Python code |
| **Workflow Location** | JSON file separate from code | Code decorated with @workflow.defn |
| **State Management** | External metadata store | Event sourcing (automatic) |
| **Execution Model** | Workers poll for tasks | Workers execute activities and workflows |
| **Data Passing** | JSONPath expressions | Native Python objects |
| **Control Flow** | JSON task types | Native Python constructs |

---

## Task Type Mappings

| Conductor Task Type | Temporal Equivalent | Python Implementation |
|---------------------|---------------------|----------------------|
| **SIMPLE** | Activity | `@activity.defn` function |
| **HTTP** | HTTP Activity | `@activity.defn` with httpx |
| **HUMAN_TASK** | Update/Signal + Wait | `@workflow.update` or `@workflow.signal` + `workflow.wait_condition()` - [See guide](./conductor-human-interaction.md) |
| **SET_VARIABLE** | Variable Assignment | Direct Python variable assignment |
| **WAIT** | Signal/Update + Wait Condition | `@workflow.signal` or `@workflow.update` + `workflow.wait_condition()` - [See guide](./conductor-human-interaction.md) |
| **INLINE** | Inline Python | Direct Python code in workflow |
| **SUB_WORKFLOW** | Child Workflow | `workflow.execute_child_workflow()` |
| **FORK_JOIN** + **JOIN** | Parallel Execution | `asyncio.gather()` |
| **DO_WHILE** | While Loop | Python `while` loop |
| **SWITCH** | Conditional Logic | Python `if/elif/else` |
| **DYNAMIC_FORK** | Dynamic Parallel | List comprehension + `asyncio.gather()` |

**For detailed primitive-by-primitive reference with complete JSON and Python examples**, see the [Primitives Reference](./conductor-primitives-reference.md).

---

## Control Flow Pattern Translation

### Sequential Execution
**Conductor:**
```json
{
  "tasks": [
    {"name": "task1", "type": "SIMPLE"},
    {"name": "task2", "type": "SIMPLE"}
  ]
}
```

**Temporal:**
```python
result1 = await workflow.execute_activity(activities.task1, ...)
result2 = await workflow.execute_activity(activities.task2, args=[result1], ...)
```

### Parallel Execution (FORK_JOIN)
**Conductor:**
```json
{
  "name": "fork_task",
  "type": "FORK_JOIN",
  "forkTasks": [
    [{"name": "task_a", "type": "SIMPLE"}],
    [{"name": "task_b", "type": "SIMPLE"}]
  ]
}
```

**Temporal:**
```python
result_a, result_b = await asyncio.gather(
    workflow.execute_activity(activities.task_a, ...),
    workflow.execute_activity(activities.task_b, ...)
)
```

### Conditional Logic (SWITCH)
**Conductor:**
```json
{
  "name": "decision",
  "type": "SWITCH",
  "switchCaseValue": "${approval.status}",
  "decisionCases": {
    "APPROVED": [{"name": "proceed", "type": "SIMPLE"}],
    "REJECTED": [{"name": "notify", "type": "SIMPLE"}]
  }
}
```

**Temporal:**
```python
status = approval_result.status
if status == "APPROVED":
    await workflow.execute_activity(activities.proceed, ...)
elif status == "REJECTED":
    await workflow.execute_activity(activities.notify, ...)
```

### Loops (DO_WHILE)
**Conductor:**
```json
{
  "name": "retry_loop",
  "type": "DO_WHILE",
  "loopCondition": "$.approved == false",
  "loopOver": [{"name": "check_approval", "type": "SIMPLE"}]
}
```

**Temporal:**
```python
approved = False
while not approved:
    result = await workflow.execute_activity(activities.check_approval, ...)
    approved = result.approved
```

---

## Data Passing Translation

| Conductor Expression | Temporal Python Equivalent | Notes |
|----------------------|---------------------------|-------|
| `${workflow.input.field}` | `input.field` | Direct access to workflow input parameter |
| `${task_ref.output.field}` | `result_variable.field` | Access result from activity execution |
| `${workflow.variables.var}` | `var` (local variable) | Workflow-scoped variables |
| `${user_action.output.approved}` | `self._user_action.approved` | External input from signals/updates - [See guide](./conductor-human-interaction.md) |
| `$.some.path` (JSONPath) | `data.some.path` or `data["some"]["path"]` | Direct Python object access |

**For external/human inputs**: References like `${user_action.output.*}` indicate data coming from outside the workflow (human approvals, external systems). In Temporal, this is handled via Signals or Updates - see the [Human Interaction Patterns guide](./conductor-human-interaction.md) for complete examples.

---

## Key Differences to Remember

### 1. **Determinism Requirements**
- **Conductor**: No strict determinism requirements in workflow definitions
- **Temporal**: Workflows must be deterministic - no random numbers, no current time, no I/O operations directly in workflow code

### 2. **State Persistence**
- **Conductor**: Maintains state in external database
- **Temporal**: Automatically persists state through event sourcing - every workflow action is logged

### 3. **Error Handling**
- **Conductor**: Configure retry policies in JSON
- **Temporal**: Configure retry policies in Python code using `RetryPolicy` class

### 4. **Timeouts**
- **Conductor**: Various timeout configurations in JSON
- **Temporal**: More granular timeout controls:
  - `start_to_close_timeout` - Max activity execution time
  - `schedule_to_close_timeout` - Max time from scheduling to completion
  - `schedule_to_start_timeout` - Max queue time
  - `execution_timeout` - Max workflow execution time

### 5. **Signals and Waits**
- **Conductor**: WAIT task type
- **Temporal**: `@workflow.signal` decorator + `workflow.wait_condition()` for async event handling

---

## Related Documentation

- [Primitives Reference](./conductor-primitives-reference.md) - Detailed primitive-by-primitive mapping with complete examples
- [Migration Guide](./conductor-migration-guide.md) - Step-by-step migration instructions
- [Human Interaction Patterns](./conductor-human-interaction.md) - Approvals, signals, updates, and human-in-the-loop workflows
- [Quality Assurance](./conductor-quality-assurance.md) - Testing and validation
- [Troubleshooting](./conductor-troubleshooting.md) - Common issues and solutions

---

**[← Back to Main Guide](./README.md)**

# Conductor Primitives Reference

> **Part of the [Conductor to Temporal Migration Guide](./README.md)**

## Overview

This document provides a comprehensive primitive-by-primitive mapping reference between Netflix Conductor's JSON-based workflow primitives and Temporal Python SDK's code-based implementations. Each section includes complete Conductor JSON examples with configuration details, corresponding Temporal Python code, and links to official documentation.

**Use this document when:**
- You need detailed examples of how a specific Conductor primitive maps to Temporal
- You're translating a specific task type (SWITCH, DO_WHILE, FORK_JOIN, HTTP, etc.)
- You want complete code examples with retry policies, timeout configurations, and error handling
- You need to understand the mechanics of Conductor primitives (like dynamicForkTasksParam, loopCondition, etc.)

**For other migration needs:**
- **Conceptual understanding**: See [Architecture Reference](./conductor-architecture.md) for high-level architectural differences
- **Step-by-step migration**: See [Migration Guide](./conductor-migration-guide.md) for phase-by-phase instructions
- **Human interaction patterns**: See [Human Interaction Patterns](./conductor-human-interaction.md) for approvals, signals, and updates

This reference is designed for active migrators who need detailed lookup information for specific Conductor constructs.

---

## **Input / Output Expressions**

### **Conductor**
Uses JSONPath expressions in workflow definitions to wire data between tasks via `inputParameters` and `outputParameters`. Data flows through templated expressions:

```json
{
  "inputParameters": {
    "movieId": "${workflow.input.movieId}",
    "url": "${workflow.input.fileLocation}",
    "lang": "${loc_task.output.languages[0]}",
    "http_request": {
      "method": "POST",
      "url": "http://example.com/${loc_task.output.fileId}/encode"
    }
  }
}
```

- **Data Access**: `${workflow.input.field}`, `${taskRef.output.field}`
- **JSONPath Support**: Can use JSONPath queries like `${task.output.list[?(@.status == 'COMPLETED')]}`
- **No Type Safety**: All parameters are JSON; no compile-time validation

[**Conductor Documentation**](https://conductor.netflix.com/configuration/workflowdef.html)

### **Temporal Python**
Workflow parameters and return values are native Python function arguments and return types with full type safety:

```python
@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, input: MyInput) -> MyResult:
        result = await workflow.execute_activity(
            process_data,
            input.data,
            start_to_close_timeout=timedelta(minutes=5)
        )
        return MyResult(processed=result)
```

- **Native Python**: Standard function signatures with type hints
- **Type Safety**: MyPy validation, IDE autocomplete
- **Direct Access**: No templating syntax needed

[**Temporal Documentation**](https://docs.temporal.io/develop/python)

---

## **Outputs**

### **Conductor**
Task outputs are JSON objects accessed via `${taskReferenceName.output.field}` in subsequent tasks. Task definitions specify `outputKeys` as documentation (not enforced):

```json
{
  "name": "my_task",
  "outputKeys": ["result", "status", "metadata"]
}
```

Output is automatically persisted and can be referenced by any downstream task.

[**Conductor Task Definitions**](https://conductor.netflix.com/configuration/taskdef.html)

### **Temporal Python**
Strongly typed return values that can be any serializable Python object:

```python
@activity.defn
async def say_hello(name: str) -> str:
    return f"Hello, {name}!"

@dataclass
class ProcessResult:
    status: str
    data: dict
    
@activity.defn
async def process_data(input: dict) -> ProcessResult:
    return ProcessResult(status="success", data={"key": "value"})
```

[**Temporal Activities**](https://docs.temporal.io/activities)

---

## **Branching / Conditional Logic**

### **Conductor: Switch Task**
JSON-based conditional branching using `SWITCH` task type with JavaScript or value-param evaluators:

```json
{
  "name": "switch_task",
  "taskReferenceName": "switch_ref",
  "type": "SWITCH",
  "evaluatorType": "javascript",
  "expression": "$.inputValue == 'fedex' ? 'fedex' : 'ups'",
  "inputParameters": {
    "inputValue": "${workflow.input.service}"
  },
  "decisionCases": {
    "fedex": [
      {
        "name": "ship_via_fedex",
        "taskReferenceName": "fedex_task",
        "type": "SIMPLE"
      }
    ],
    "ups": [
      {
        "name": "ship_via_ups", 
        "taskReferenceName": "ups_task",
        "type": "SIMPLE"
      }
    ]
  },
  "defaultCase": [
    {
      "name": "default_handler",
      "taskReferenceName": "default_ref",
      "type": "SIMPLE"
    }
  ]
}
```

- **Evaluator Types**: `value-param` (direct parameter matching) or `javascript`/`graaljs` (expression evaluation)
- **Nested Support**: Can nest switches, forks, loops within switch cases
- **Default Case**: Optional fallback branch

[**Conductor Switch**](https://orkes.io/content/reference-docs/operators/switch)

### **Temporal Python**
Standard Python conditional logic with full language support:

```python
@workflow.defn
class ShippingWorkflow:
    @workflow.run
    async def run(self, service: str) -> str:
        if service == "fedex":
            result = await workflow.execute_activity(
                ship_via_fedex,
                start_to_close_timeout=timedelta(minutes=5)
            )
        elif service == "ups":
            result = await workflow.execute_activity(
                ship_via_ups,
                start_to_close_timeout=timedelta(minutes=5)
            )
        else:
            result = await workflow.execute_activity(
                default_handler,
                start_to_close_timeout=timedelta(minutes=5)
            )
        return result
```

- **Native Python**: Use `if/elif/else`, `match` (Python 3.10+), or any Python logic
- **No DSL Required**: Full programming language expressiveness

[**Temporal Programming Model**](https://temporal.io/blog/tihomir-journey-to-temporal#programming-model)

---

## **Error Handling**

### **Conductor**
Configured in task definitions with retry policies and timeout settings:

```json
{
  "name": "my_task",
  "retryCount": 3,
  "retryLogic": "EXPONENTIAL_BACKOFF",
  "retryDelaySeconds": 5,
  "backoffScaleFactor": 2,
  "timeoutSeconds": 300,
  "timeoutPolicy": "RETRY",
  "responseTimeoutSeconds": 60
}
```

- **Retry Logic**: `FIXED`, `EXPONENTIAL_BACKOFF`, `LINEAR_BACKOFF`
- **Timeout Policies**: `RETRY`, `TIME_OUT_WF`, `ALERT_ONLY`
- **Failure Workflows**: Specify a compensation workflow via `failureWorkflow` parameter
- **Configuration-Based**: All error handling defined in JSON, not code

[**Conductor Error Handling**](https://orkes.io/content/error-handling)

### **Temporal Python**
Native try/except blocks with built-in retry policies:

```python
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationFailure

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self) -> str:
        try:
            result = await workflow.execute_activity(
                risky_operation,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=100),
                    maximum_attempts=3,
                    backoff_coefficient=2.0
                )
            )
        except ApplicationFailure as err:
            # Handle specific failure
            workflow.logger.error(f"Activity failed: {err.message}")
            result = await workflow.execute_activity(
                fallback_operation,
                start_to_close_timeout=timedelta(minutes=5)
            )
        return result
```

- **Pythonic**: Standard exception handling
- **Activity-Level**: Retry policies per activity invocation
- **Application Failures**: Explicitly raise retryable or non-retryable failures

[**Temporal Error Handling**](https://docs.temporal.io/develop/python/failure-detection)

---

## **While Loops**

### **Conductor: Do-While Task**
JSON-based loop with condition evaluation:

```json
{
  "name": "loop_task",
  "taskReferenceName": "loop_ref",
  "type": "DO_WHILE",
  "loopCondition": "if ($.loop_ref['iteration'] < 10) { true; } else { false; }",
  "loopOver": [
    {
      "name": "task_in_loop",
      "taskReferenceName": "task_ref",
      "type": "HTTP",
      "inputParameters": {
        "uri": "https://api.example.com/page/${loop_ref.output.iteration}"
      }
    }
  ]
}
```

- **Loop Condition**: JavaScript expression evaluated each iteration
- **Iteration Counter**: Accessible via `${taskRef.output.iteration}`
- **Task Naming**: Loop tasks get `__i` suffix (e.g., `task_ref__1`, `task_ref__2`)
- **Limitations**: No nested DO_WHILE (use SUB_WORKFLOW instead)

[**Conductor Do-While**](https://orkes.io/content/reference-docs/operators/do-while)

### **Temporal Python**
Standard Python while loops with continue-as-new for long-running cases:

```python
@workflow.defn
class LoopWorkflow:
    @workflow.run
    async def run(self, max_iterations: int) -> list:
        results = []
        iteration = 0
        
        while iteration < max_iterations:
            result = await workflow.execute_activity(
                process_item,
                iteration,
                start_to_close_timeout=timedelta(minutes=1)
            )
            results.append(result)
            iteration += 1
            
            # Prevent history bloat in long-running loops
            if workflow.info().is_continue_as_new_suggested():
                workflow.continue_as_new(max_iterations - iteration)
        
        return results
```

[**Temporal Continue-As-New**](https://docs.temporal.io/develop/python/continue-as-new)

---

## **ForEach / Iteration**

### **Conductor: Dynamic Fork**
Dynamically creates parallel tasks based on input list:

```json
{
  "name": "dynamic_fork",
  "taskReferenceName": "dynamic_fork_ref",
  "type": "FORK_JOIN_DYNAMIC",
  "dynamicForkTasksParam": "dynamicTasks",
  "dynamicForkTasksInputParamName": "dynamicTasksInput",
  "inputParameters": {
    "dynamicTasks": "${prep_task.output.taskList}",
    "dynamicTasksInput": "${prep_task.output.inputMap}"
  }
}
```

The prep task outputs:
```json
{
  "dynamicTasks": [
    {"name": "resize_image", "taskReferenceName": "resize_1", "type": "SIMPLE"},
    {"name": "resize_image", "taskReferenceName": "resize_2", "type": "SIMPLE"}
  ],
  "dynamicTasksInput": {
    "resize_1": {"size": "300x300"},
    "resize_2": {"size": "200x200"}
  }
}
```

[**Conductor Dynamic Fork**](https://conductor.netflix.com/reference-docs/dynamic-fork-task.html)

### **Temporal Python**
Native for loops with asyncio.gather for parallelism:

```python
@workflow.defn
class ProcessItemsWorkflow:
    @workflow.run
    async def run(self, items: list[str]) -> list[str]:
        # Sequential
        results = []
        for item in items:
            result = await workflow.execute_activity(
                process_item,
                item,
                start_to_close_timeout=timedelta(minutes=1)
            )
            results.append(result)
        
        # Parallel
        results = await asyncio.gather(
            *(workflow.execute_activity(
                process_item,
                item,
                start_to_close_timeout=timedelta(minutes=1)
            ) for item in items)
        )
        
        return results
```

[**Temporal Parallelism**](https://docs.temporal.io/develop/python)

---

## **Parallel Execution**

### **Conductor: Fork/Join Tasks**
Explicitly defined parallel branches with JOIN synchronization:

```json
[
  {
    "name": "fork_task",
    "taskReferenceName": "fork_ref",
    "type": "FORK_JOIN",
    "forkTasks": [
      [
        {
          "name": "email_notification",
          "taskReferenceName": "email_ref",
          "type": "SIMPLE"
        }
      ],
      [
        {
          "name": "sms_notification",
          "taskReferenceName": "sms_ref",
          "type": "SIMPLE"
        }
      ],
      [
        {
          "name": "http_notification",
          "taskReferenceName": "http_ref",
          "type": "HTTP"
        }
      ]
    ]
  },
  {
    "name": "join_task",
    "taskReferenceName": "join_ref",
    "type": "JOIN",
    "joinOn": ["email_ref", "sms_ref"]
  }
]
```

- **Fork Branches**: Each array in `forkTasks` is a separate parallel branch
- **Selective Join**: `joinOn` can wait for subset of tasks (others optional)
- **Output**: JOIN task produces map of `{taskRef: taskOutput}`

[**Conductor Fork/Join**](https://orkes.io/content/reference-docs/operators/fork-join)

### **Temporal Python**
Use asyncio.gather for concurrent activity execution:

```python
@workflow.defn
class NotificationWorkflow:
    @workflow.run
    async def run(self) -> dict:
        # All three run concurrently
        email_result, sms_result, http_result = await asyncio.gather(
            workflow.execute_activity(
                send_email,
                start_to_close_timeout=timedelta(minutes=1)
            ),
            workflow.execute_activity(
                send_sms,
                start_to_close_timeout=timedelta(minutes=1)
            ),
            workflow.execute_activity(
                send_http,
                start_to_close_timeout=timedelta(minutes=1)
            ),
            return_exceptions=True  # Continue if some fail
        )
        
        return {
            "email": email_result,
            "sms": sms_result,
            "http": http_result
        }
```

[**Temporal Async Patterns**](https://docs.temporal.io/develop/python)

---

## **Delay / Sleep**

### **Conductor: Wait Task**
Pauses workflow for specified duration or until timestamp:

```json
{
  "name": "wait_task",
  "taskReferenceName": "wait_ref",
  "type": "WAIT",
  "inputParameters": {
    "duration": "5m 30s"
  }
}
```

Or wait until specific time:
```json
{
  "inputParameters": {
    "until": "2024-12-31 23:59:59"
  }
}
```

- **Duration Format**: `"DdHhMmSs"` or `"D days H hours M minutes S seconds"`
- **Absolute Time**: ISO 8601 or `yyyy-MM-dd HH:mm:ss` with optional timezone
- **Signal-Based**: Can also wait for external signal/event

[**Conductor Wait Task**](https://orkes.io/content/reference-docs/operators/wait)

### **Temporal Python**
Durable timers that survive worker restarts:

```python
@workflow.defn
class DelayWorkflow:
    @workflow.run
    async def run(self) -> str:
        # Wait 5 minutes
        await workflow.sleep(timedelta(minutes=5))
        
        # Or wait until specific time
        target_time = datetime(2024, 12, 31, 23, 59, 59)
        sleep_duration = target_time - workflow.now()
        await workflow.sleep(sleep_duration)
        
        return "Delay complete"
```

- **Durable**: Timer persists across worker restarts
- **No Polling**: Timer is managed by Temporal server

[**Temporal Timers**](https://docs.temporal.io/develop/python/timers)

---

## **Recur / Recurring Workflows**

### **Conductor**
No native recurring/schedule primitive in workflow DSL. Options:
1. **External Scheduler**: Use cron or workflow scheduler to trigger workflows periodically
2. **Do-While Loop**: Implement recurrence within workflow (not recommended for long-term)
3. **Community Plugin**: [Schedule Conductor Workflows](https://github.com/Netflix/conductor/issues/27) plugin

[**Conductor FAQ on Scheduling**](https://conductor-oss.github.io/conductor/devguide/faq.html)

### **Temporal Python**
Two approaches:

**1. Continue-As-New (within workflow):**
```python
@workflow.defn
class RecurringWorkflow:
    @workflow.run
    async def run(self, iterations_left: int) -> None:
        # Do work
        await workflow.execute_activity(
            process_task,
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        # Sleep until next iteration
        await workflow.sleep(timedelta(hours=1))
        
        # Continue as new to prevent history buildup
        if iterations_left > 1:
            workflow.continue_as_new(iterations_left - 1)
```

**2. Temporal Schedules (external):**
```python
# Create schedule via SDK or CLI
schedule = await client.create_schedule(
    "my-recurring-workflow",
    Schedule(
        action=ScheduleActionStartWorkflow(
            MyWorkflow.run,
            id="scheduled-workflow",
        ),
        spec=ScheduleSpec(
            cron_expressions=["0 */1 * * *"],  # Every hour
        ),
    ),
)
```

[**Temporal Schedules**](https://docs.temporal.io/workflows#schedule)

---

## **Schedule / Cron**

### **Conductor**
Not built into workflow DSL. Must use external scheduling:
- Cron jobs calling Conductor REST API
- Workflow scheduling plugins
- External workflow schedulers

### **Temporal Python**
First-class Schedules with advanced features:

```python
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    ScheduleCalendarSpec,
    ScheduleRange,
)

schedule = await client.create_schedule(
    "nightly-report",
    Schedule(
        action=ScheduleActionStartWorkflow(
            GenerateReport.run,
            args=["daily"],
            id="report-workflow",
        ),
        spec=ScheduleSpec(
            calendars=[
                ScheduleCalendarSpec(
                    hour=[2],  # 2 AM
                    minute=[0],
                )
            ],
        ),
        policy=SchedulePolicy(
            overlap=ScheduleOverlapPolicy.BUFFER_ONE,
            catchup_window=timedelta(hours=1),
        ),
    ),
)
```

- **Cron Expressions**: Support standard cron syntax
- **Calendar-based**: Rich calendar specifications
- **Overlap Policies**: Control what happens if run overlaps
- **Backfills**: Can backfill missed runs

[**Temporal Schedules**](https://docs.temporal.io/workflows#schedule)

---

## **WaitFor / Signals / Human Interaction**

### **Conductor: WAIT, HUMAN_TASK, and Event Tasks**

Conductor handles human interaction and external events through several mechanisms:
- **WAIT tasks**: Pause workflow until external event/API call
- **HUMAN_TASK tasks**: Assign tasks to humans for approval/input
- **Event Handlers**: Configure event listeners that complete tasks
- **Manual completion**: Via Conductor UI or REST API

### **Temporal Python: Signals and Updates**

Temporal provides **Signals** (fire-and-forget) and **Updates** (request-response) for external interaction with running workflows. The choice between them depends on your use case.

**For comprehensive coverage of human interaction patterns, see:**

### **[→ Human Interaction Patterns Guide](./conductor-human-interaction.md)**

This dedicated guide provides complete coverage of:
- **Signals vs Updates**: Decision criteria table and when to use each
- **HUMAN_TASK mapping**: How to translate Conductor HUMAN_TASK to Temporal
- **Approval workflows**: With validation, timeout handling, and escalation
- **Multiple reviewers**: Parallel approval patterns
- **Approval loops**: Retry until approved patterns
- **Data flow**: Translating `${user_action.output.*}` references

**Quick Signal Example:**
```python
@workflow.defn
class ApprovalWorkflow:
    def __init__(self) -> None:
        self.approved = False

    @workflow.signal
    async def receive_approval(self, approved: bool) -> None:
        self.approved = approved

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.approved)
        return "Approved"

# Send signal: await handle.signal(ApprovalWorkflow.receive_approval, True)
```

**Quick Update Example:**
```python
@workflow.defn
class ApprovalWorkflow:
    def __init__(self) -> None:
        self.approved = False

    @workflow.update
    async def submit_approval(self, approved: bool) -> str:
        """Update with validation and return value."""
        if self.approved:
            raise ApplicationError("Already approved")
        self.approved = approved
        return "Approval recorded"

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.approved)
        return "Approved"

# Send update: result = await handle.execute_update(ApprovalWorkflow.submit_approval, True)
```

**See the [Human Interaction Patterns Guide](./conductor-human-interaction.md) for production-ready patterns with timeout handling, multiple approvals.**

---

## **Activity / Worker Tasks**

### **Conductor: Simple Tasks**
Tasks implemented by workers polling Conductor server:

**Task Definition (registered):**
```json
{
  "name": "encode_video",
  "retryCount": 3,
  "timeoutSeconds": 1200,
  "inputKeys": ["videoUrl", "format"],
  "outputKeys": ["encodedUrl", "duration"],
  "timeoutPolicy": "TIME_OUT_WF",
  "retryLogic": "FIXED",
  "retryDelaySeconds": 60,
  "responseTimeoutSeconds": 300
}
```

**Worker Implementation (Python example):**
```python
from conductor.client.worker.worker_task import worker_task

@worker_task(task_definition_name='encode_video')
def encode_video(videoUrl: str, format: str) -> dict:
    # Process video
    encoded_url = encode(videoUrl, format)
    return {
        'encodedUrl': encoded_url,
        'duration': 120
    }
```

- **Polling Model**: Workers poll Conductor for tasks
- **Language Agnostic**: Any language that can make HTTP calls
- **Separate Registration**: Tasks must be registered before use

[**Conductor Tasks**](https://conductor.netflix.com/devguide/concepts/tasks.html)

### **Temporal Python**
Activities are Python functions with decorators:

```python
from temporalio import activity
from datetime import timedelta

@activity.defn
async def encode_video(video_url: str, format: str) -> dict:
    # Long-running processing
    activity.heartbeat({"progress": 25})  # Send heartbeat
    
    encoded_url = await encode_async(video_url, format)
    
    return {
        'encoded_url': encoded_url,
        'duration': 120
    }

# In workflow
result = await workflow.execute_activity(
    encode_video,
    args=["https://example.com/video.mp4", "h264"],
    start_to_close_timeout=timedelta(minutes=20),
    heartbeat_timeout=timedelta(seconds=30),
    retry_policy=RetryPolicy(maximum_attempts=3)
)
```

- **Type-Safe**: Full Python type hints
- **Heartbeats**: Built-in progress reporting
- **Retries**: Per-activity retry policies
- **No Registration**: Activities discovered from worker code

[**Temporal Activities**](https://docs.temporal.io/activities)

---

## **Key Differences Summary**

For a comprehensive architectural comparison table, see the **[Main Migration Guide](./README.md#key-differences-at-a-glance)**.

---

## **Migration Considerations**

When migrating from Conductor to Temporal:

1. **JSON to Code**: Translate JSON workflow definitions into Python workflow classes
2. **Operators to Logic**: Replace SWITCH/FORK/DO_WHILE with Python if/asyncio.gather/while
3. **Templates to Objects**: Replace `${task.output.field}` with direct Python variable access
4. **Task Registration**: Remove task registration step; activities auto-discovered
5. **Error Config to Code**: Move retry/timeout configs from JSON to Python retry policies
6. **Events to Signals**: Replace Conductor events with Temporal signals

---

## **Additional Resources**

### **Conductor**
- [Conductor Documentation](https://conductor-oss.github.io/conductor/)
- [Orkes Conductor Docs](https://orkes.io/content)
- [Netflix Tech Blog: Conductor](https://netflixtechblog.com/netflix-conductor-a-microservices-orchestrator-2e8d4771bf40)

### **Temporal Python**
- [Temporal Python SDK](https://docs.temporal.io/develop/python)
- [Python SDK API Reference](https://python.temporal.io/)
- [Temporal Learning Portal](https://learn.temporal.io/)
- [GitHub: Temporal Python SDK](https://github.com/temporalio/sdk-python)
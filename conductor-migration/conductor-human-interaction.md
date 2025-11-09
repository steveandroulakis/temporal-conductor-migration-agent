# Human-in-the-Loop Patterns: Interactive Workflows

## Introduction

Many workflows require human input, approvals, or decisions at various stages. In Conductor, this is typically handled through:
- `HUMAN_TASK` task types
- `WAIT` tasks waiting for external events
- DO_WHILE loops checking for approval status
- References to external input like `${user_action.output.approved}`

In Temporal, human interaction is handled through **Signals** and **Updates**, which allow external systems (including humans via UI) to send data into a running workflow.

**When to use this guide:**
- Your Conductor workflow has `HUMAN_TASK` tasks
- You see references to `${user_action.output.*}` or similar external data sources
- Your workflow waits for approval, review, or manual decisions
- You have DO_WHILE loops that continue until a human provides input

---

## Signals vs Updates: When to Use Each

Temporal provides two mechanisms for external interaction with running workflows:

| Feature | **Signals** | **Updates** |
|---------|------------|------------|
| **Communication Style** | Fire-and-forget (async) | Request-response (sync) |
| **Return Value** | None | Can return data to caller |
| **Validation** | Cannot reject | Can validate and reject |
| **Best For** | Notifications, events | Approvals, data submission |
| **Caller Waits** | No | Yes (until complete) |
| **Error Handling** | Cannot fail | Can throw errors |

### Decision Criteria

**Use Updates when:**
- ✅ You need to return a result to the caller (e.g., "approval accepted")
- ✅ You want to validate input before accepting it
- ✅ The interaction is transactional (approve/reject with immediate feedback)
- ✅ Conductor used `HUMAN_TASK` for approval workflows
- ✅ The caller needs to know if the submission was successful

**Use Signals when:**
- ✅ You're sending notifications or fire-and-forget events
- ✅ You don't need to validate the input
- ✅ The caller doesn't need immediate confirmation
- ✅ You're migrating simple `WAIT` tasks
- ✅ Multiple parties may send the same signal

---

## Conductor Task Type Mappings

### HUMAN_TASK → Update (Recommended)

When your Conductor workflow has a `HUMAN_TASK`:

```json
{
  "name": "approve_request",
  "taskReferenceName": "approve_request_ref",
  "type": "HUMAN_TASK",
  "inputParameters": {
    "assignee": "manager@example.com",
    "taskObject": "${workflow.input.request}"
  }
}
```

**Translate to Temporal Update:**

```python
from temporalio import workflow
from temporalio.exceptions import ApplicationError

@workflow.defn
class ApprovalWorkflow:
    def __init__(self) -> None:
        self._approval_decision: ApprovalDecision | None = None

    @workflow.update
    async def submit_approval(self, decision: ApprovalDecision) -> ApprovalResult:
        """Handle approval decision from human reviewer."""
        # Validate the decision
        if self._approval_decision is not None:
            raise ApplicationError("Approval already submitted")

        if decision.reviewer_id not in self._authorized_reviewers:
            raise ApplicationError(f"Unauthorized reviewer: {decision.reviewer_id}")

        # Store the decision
        self._approval_decision = decision

        # Return result to caller
        return ApprovalResult(
            status="accepted",
            reviewer=decision.reviewer_id,
            timestamp=workflow.now()
        )

    @workflow.run
    async def run(self, request: ApprovalRequest) -> ApprovalResult:
        # ... do work ...

        # Wait for human approval
        await workflow.wait_condition(
            lambda: self._approval_decision is not None,
            timeout=timedelta(hours=24)
        )

        if self._approval_decision.approved:
            # Continue with approval
            return await self._process_approved()
        else:
            # Handle rejection
            return await self._process_rejected()
```

**Sending the update from client:**

```python
from temporalio.client import Client

client = await Client.connect("localhost:7233")
handle = client.get_workflow_handle("approval-workflow-123")

# Submit approval decision (caller waits for validation)
result = await handle.execute_update(
    "submit_approval",
    ApprovalDecision(
        reviewer_id="user@example.com",
        approved=True,
        comments="Looks good!"
    )
)
print(f"Approval recorded: {result.status}")
```

### HUMAN_TASK → Signal (Alternative)

If you don't need validation or return values:

```python
@workflow.defn
class ApprovalWorkflow:
    def __init__(self) -> None:
        self._approval_decision: ApprovalDecision | None = None

    @workflow.signal
    async def receive_approval(self, decision: ApprovalDecision) -> None:
        """Handle approval decision via signal."""
        self._approval_decision = decision

    @workflow.run
    async def run(self, request: ApprovalRequest) -> ApprovalResult:
        # Wait for approval signal
        await workflow.wait_condition(
            lambda: self._approval_decision is not None
        )

        # Process based on decision
        if self._approval_decision.approved:
            return await self._process_approved()
```

**Sending the signal from client:**

```python
handle = client.get_workflow_handle("approval-workflow-123")

# Send approval signal (fire-and-forget)
await handle.signal(
    "receive_approval",
    ApprovalDecision(
        reviewer_id="user@example.com",
        approved=True
    )
)
```

---

## Data Flow: Translating External References

### Pattern: ${user_action.output.approved}

In Conductor, you often see references to external data:

```json
{
  "name": "check_approval",
  "type": "SWITCH",
  "inputParameters": {
    "switchCaseValue": "${user_action.output.approved}"
  },
  "decisionCases": {
    "true": [...],
    "false": [...]
  }
}
```

**Temporal Translation:**

```python
@workflow.defn
class ApprovalWorkflow:
    def __init__(self) -> None:
        # Store human input in workflow instance variable
        self._user_action: UserAction | None = None

    @workflow.update
    async def submit_user_action(self, action: UserAction) -> None:
        """Receive external input from human."""
        self._user_action = action

    @workflow.run
    async def run(self, request: Request) -> Result:
        # Wait for user action
        await workflow.wait_condition(lambda: self._user_action is not None)

        # Access the data: ${user_action.output.approved} → self._user_action.approved
        if self._user_action.approved:
            # YES case
            result = await self._handle_approved()
        else:
            # NO case
            result = await self._handle_rejected()

        return result
```

### Mapping Table

| Conductor Reference | Temporal Equivalent | Notes |
|---------------------|---------------------|-------|
| `${user_action.output.approved}` | `self._user_action.approved` | After receiving signal/update |
| `${reviewer1.output.decision}` | `self._reviewer1_decision.decision` | Store each reviewer's input separately |
| `${human_task.output.selectedOption}` | `self._human_input.selected_option` | After update handler stores it |

---

## Pattern: Basic Approval with Timeout

Handle scenarios where humans must respond within a time limit:

```python
from datetime import timedelta
from temporalio import workflow
from temporalio.exceptions import ApplicationError
import asyncio

@workflow.defn
class TimedApprovalWorkflow:
    def __init__(self) -> None:
        self._approval: Approval | None = None

    @workflow.update
    async def submit_approval(self, approval: Approval) -> str:
        """Receive approval decision."""
        if self._approval is not None:
            raise ApplicationError("Approval already submitted")

        self._approval = approval
        return "Approval recorded"

    @workflow.run
    async def run(self, request: Request) -> Result:
        # Notify human that approval is needed
        await workflow.execute_activity(
            notify_approval_needed,
            args=[request],
            start_to_close_timeout=timedelta(seconds=30)
        )

        # Wait up to 24 hours for approval
        try:
            await workflow.wait_condition(
                lambda: self._approval is not None,
                timeout=timedelta(hours=24)
            )
        except asyncio.TimeoutError:
            # Handle timeout - could escalate, use default, or fail
            workflow.logger.warning("Approval timeout - using default rejection")
            return Result(approved=False, reason="timeout")

        # Process approval
        if self._approval.approved:
            return await workflow.execute_activity(
                process_approval,
                args=[request],
                start_to_close_timeout=timedelta(seconds=30)
            )
        else:
            return Result(approved=False, reason=self._approval.rejection_reason)
```

---

## Pattern: Multiple Parallel Approvals

When multiple reviewers must approve in parallel (like FORK_JOIN with HUMAN_TASKs):

**Conductor Example:**
```json
{
  "type": "FORK_JOIN",
  "forkTasks": [
    [{"name": "Review1.a", "type": "HUMAN_TASK"}],
    [{"name": "Review1.b", "type": "HUMAN_TASK"}]
  ]
}
```

**Temporal Translation:**

```python
from typing import Dict

@workflow.defn
class MultiReviewerWorkflow:
    def __init__(self) -> None:
        self._approvals: Dict[str, ReviewDecision] = {}
        self._required_reviewers = {"reviewer_a", "reviewer_b"}

    @workflow.update
    async def submit_review(self, reviewer_id: str, decision: ReviewDecision) -> str:
        """Receive review from any reviewer."""
        if reviewer_id not in self._required_reviewers:
            raise ApplicationError(f"Unknown reviewer: {reviewer_id}")

        if reviewer_id in self._approvals:
            raise ApplicationError(f"Reviewer {reviewer_id} already submitted")

        self._approvals[reviewer_id] = decision
        return f"Review from {reviewer_id} recorded"

    @workflow.run
    async def run(self, request: Request) -> Result:
        # Notify all reviewers in parallel
        await asyncio.gather(
            workflow.execute_activity(
                notify_reviewer,
                args=["reviewer_a", request],
                start_to_close_timeout=timedelta(seconds=30)
            ),
            workflow.execute_activity(
                notify_reviewer,
                args=["reviewer_b", request],
                start_to_close_timeout=timedelta(seconds=30)
            )
        )

        # Wait for ALL reviewers to respond
        await workflow.wait_condition(
            lambda: all(
                reviewer in self._approvals
                for reviewer in self._required_reviewers
            )
        )

        # Check if ALL approved
        all_approved = all(
            decision.approved
            for decision in self._approvals.values()
        )

        if all_approved:
            return await self._process_approved()
        else:
            rejections = [
                f"{rid}: {decision.comments}"
                for rid, decision in self._approvals.items()
                if not decision.approved
            ]
            return Result(approved=False, rejections=rejections)
```

---

## Pattern: Approval Loop (Retry Until Approved)

When workflows must loop until human approves (DO_WHILE with approval condition):

**Conductor Example:**
```json
{
  "type": "DO_WHILE",
  "loopCondition": "if ($.approved) { false; } else { true; }",
  "loopOver": [
    {"name": "submit_for_review", "type": "SIMPLE"},
    {"name": "wait_for_approval", "type": "HUMAN_TASK"}
  ]
}
```

**Temporal Translation:**

```python
@workflow.defn
class ApprovalLoopWorkflow:
    def __init__(self) -> None:
        self._current_approval: Approval | None = None

    @workflow.update
    async def submit_approval_decision(self, approval: Approval) -> str:
        """Receive approval or rejection with feedback."""
        self._current_approval = approval
        return "Decision recorded"

    @workflow.run
    async def run(self, request: Request) -> Result:
        iteration = 0
        max_iterations = 5

        while iteration < max_iterations:
            iteration += 1
            workflow.logger.info(f"Approval iteration {iteration}")

            # Submit for review
            submission = await workflow.execute_activity(
                submit_for_review,
                args=[request, iteration],
                start_to_close_timeout=timedelta(seconds=30)
            )

            # Reset and wait for decision
            self._current_approval = None
            await workflow.wait_condition(
                lambda: self._current_approval is not None
            )

            # Check decision
            if self._current_approval.approved:
                # Approved! Exit loop
                return Result(
                    approved=True,
                    iteration=iteration,
                    submission=submission
                )
            else:
                # Rejected - update request based on feedback and retry
                workflow.logger.info(
                    f"Rejected: {self._current_approval.feedback}"
                )
                request = self._apply_feedback(
                    request,
                    self._current_approval.feedback
                )
                # Loop continues

        # Max iterations reached without approval
        raise ApplicationError(
            f"Request not approved after {max_iterations} iterations"
        )
```

---

## Pattern: Query Current Status

Allow external systems to check approval status without affecting workflow:

```python
@workflow.defn
class ApprovalWorkflow:
    def __init__(self) -> None:
        self._approval: Approval | None = None
        self._status = "awaiting_approval"

    @workflow.update
    async def submit_approval(self, approval: Approval) -> str:
        self._approval = approval
        self._status = "approved" if approval.approved else "rejected"
        return self._status

    @workflow.query
    def get_approval_status(self) -> Dict[str, Any]:
        """Query current approval status without modifying workflow."""
        return {
            "status": self._status,
            "has_decision": self._approval is not None,
            "approved": self._approval.approved if self._approval else None,
            "submitted_at": self._approval.timestamp if self._approval else None
        }

    @workflow.run
    async def run(self, request: Request) -> Result:
        # ... workflow logic ...
        await workflow.wait_condition(lambda: self._approval is not None)
        # ... continue ...
```

**Querying from client:**

```python
handle = client.get_workflow_handle("approval-workflow-123")

# Query without affecting workflow execution
status = await handle.query("get_approval_status")
print(f"Current status: {status['status']}")
```

---

## Common Patterns Summary

### Pattern Cheat Sheet

| Scenario | Use This Approach |
|----------|-------------------|
| **Single approval needed** | Update with validation + wait_condition |
| **Fire-and-forget notification** | Signal |
| **Multiple approvals (all required)** | Update per reviewer + wait for all |
| **Timeout if no response** | wait_condition with timeout parameter |
| **Loop until approved** | while loop + update + wait_condition |
| **Check status without changing workflow** | Query |
| **Return validation errors to caller** | Update with raised ApplicationError |
| **Approval with immediate feedback** | Update (returns result to caller) |

---

## Next Steps

After implementing human interaction patterns:

1. **Review [Quality Assurance](./conductor-quality-assurance.md)** for standards
2. **Implement notification activities** to alert humans when input is needed (email, Slack, UI)
3. **Add queries** to allow UIs to check workflow status
4. **Consider audit trails** - log all human decisions for compliance
5. **Plan escalation logic** - what happens if humans don't respond in time?

---

## Additional Resources

- **Temporal Signals Documentation**: https://docs.temporal.io/develop/python/message-passing#signals
- **Temporal Updates Documentation**: https://docs.temporal.io/develop/python/message-passing#updates
- **Temporal Queries Documentation**: https://docs.temporal.io/develop/python/message-passing#queries

---

**Need more help?** Return to the [main migration guide](./README.md) or check [Troubleshooting](./conductor-troubleshooting.md) for common issues.

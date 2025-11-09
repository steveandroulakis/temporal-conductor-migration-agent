# Conductor to Temporal Comparison – Schema Approval Workflow

| Conductor Element | Temporal Implementation | Notes |
|-------------------|-------------------------|-------|
| Workflow name `schema_approval` | `SchemaApprovalWorkflow` class in `schema_approval/workflow.py` | Workflow name preserved as class docstring reference. |
| `DO_WHILE` task `repeat_until_approved` | Python `while not approved:` loop | Loop repeats until an approval record is produced; workflow state tracks attempts and approvals. |
| `SIMPLE` task `upload_schema` | Activity `upload_schema` in `schema_approval/activities.py` | Generates a `SchemaSubmission` dataclass for each attempt. |
| `FORK_JOIN` `my_fork_join_ref` | Two concurrent `workflow.start_activity` calls | Review1.a and Review1.b activities run in parallel before continuing. |
| `SIMPLE` task `Review1.a` | Activity `review_primary_a` | Uses shared review helper to determine approval for the attempt. |
| `SIMPLE` task `Review1.b` | Activity `review_primary_b` | Same as above for the second reviewer. |
| `JOIN` `notification_join_ref` | Await both futures | Workflow waits on both review activities before proceeding. |
| `SWITCH` `Review1Check` | `_all_approved(primary_decisions)` conditional | If either reviewer rejects, loop restarts without completing review. |
| `SIMPLE` task `Review2` | Activity `review_secondary` | Returns `skip_additional_review` flag mirroring Conductor branch logic. |
| `SWITCH` `Review2Check` | `if secondary_decision.skip_additional_review` branch | Skips Review3 when secondary reviewer indicates it is optional. |
| `SIMPLE` task `Review3` | Activity `review_tertiary` | Executes only when secondary reviewer requires additional review. |
| `SWITCH` `Review3Check` | Approval check on tertiary decision | If tertiary review rejects, loop restarts. |
| `SIMPLE` tasks `CompleteReview_1` and `CompleteReview_2` | Activity `complete_review` | Single activity handles both completion paths; receives approvals list. |
| Workflow variables (`approved`) | Local variables `approved`, `attempt_details` | Workflow stores approval status and attempt history explicitly. |
| `user_action.output.approved` references | Activity return values (`ReviewDecision.approved`) | Data flow from activities supplies branch conditions. |

## Control Flow Patterns

- **Looping**: The Temporal workflow's `while not approved` loop replaces the Conductor
  `DO_WHILE` task. Attempt counters and version increments emulate iterative uploads.
- **Parallelism**: Fork/Join is implemented using `workflow.start_activity` to launch
  primary review activities concurrently, matching Conductor's parallel stage.
- **Conditionals**: Nested `if` statements replicate the switch cases, ensuring the
  same approval paths are followed.

## Data Flow

- Shared dataclasses in `schema_approval/shared.py` replace Conductor's JSONPath
  references and provide typed data passing between activities and workflow logic.
- The workflow aggregates all review decisions per attempt to supply meaningful
  context to the final `complete_review` activity, similar to the `notification_join`
  and `CompleteReview_*` tasks.

## Human Interaction

While the Conductor definition referenced `user_action` outputs, the migrated project
uses deterministic activities to simulate approvals. These can be replaced with
activities backed by human input mechanisms (e.g., Temporal Signals or Updates) if
an interactive approval process is required.

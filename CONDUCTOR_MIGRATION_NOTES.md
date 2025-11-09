# Conductor Migration Notes – Schema Approval Workflow

## Assumptions

- The original Conductor workflow implies human-driven approvals (`user_action` references)
  but does not define explicit HUMAN_TASK or WAIT primitives. The Temporal migration uses
  deterministic activities to simulate the approval responses. Replace these with real
  human-interaction patterns (signals or updates) if manual approvals are required.
- Workflow variable `approved` is represented as a local boolean (`approved`) inside the
  workflow loop. The value is derived from activity results rather than separate variable
  assignments.
- The Conductor workflow does not define input parameters; the Temporal version introduces
  a typed `WorkflowInput` dataclass to capture schema metadata and review configuration.

## Behavioral Differences

- When any reviewer rejects a submission, the workflow iteration ends without invoking
  the `complete_review` activity. This mirrors the Conductor branches where completion
  tasks only exist on the approval path.
- The `complete_review` activity unifies `CompleteReview_1` and `CompleteReview_2`. The
  behavior is identical but consolidated for simplicity.
- Activity implementations currently simulate approval outcomes based on the configured
  required attempt count. They can be extended to query external services or prompt users
  without altering the workflow logic.

## Follow-Up Opportunities

- Implement Temporal Signals to collect real-time approvals rather than deterministic
  activities.
- Extend `WorkflowInput` with reviewer configuration (names, escalation policies) to
  align with production requirements.
- Replace the placeholder schema payload with validation logic to ensure only valid
  schemas progress through the approval process.

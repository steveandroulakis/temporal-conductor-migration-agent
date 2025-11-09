# Netflix Conductor to Temporal Python Migration Guide

## Introduction

This guide provides comprehensive instructions for migrating Netflix Conductor JSON workflow definitions to production-ready Temporal Python projects.

**Use this guide when:**
- You have a Conductor JSON workflow definition file
- You want to migrate from Conductor's declarative JSON DSL to Temporal's code-first Python approach
- You need a complete documented Temporal project as output

**What this migration produces:**
- Complete Python project with workflows, activities, and worker
- Type-safe code with mypy strict validation
- Full documentation and setup instructions

---

## Quick Start (TL;DR)

For experienced users who understand both Conductor and Temporal:

1. **Ensure prerequisites**: Python 3.11+, UV, jq
2. **Validate Conductor JSON**: `jq empty workflow.json`
3. **⚠️ CRITICAL - Before writing code**: Cross-reference your Conductor JSON with [Primitives Reference](./conductor-primitives-reference.md). If HUMAN_TASK/WAIT/approvals exist, read [Human Interaction Patterns](./conductor-human-interaction.md)
4. **Follow migration phases**: Analyze → Generate → Validate
5. **Key mappings**: SIMPLE→Activity, FORK_JOIN→asyncio.gather, SWITCH→if/elif, DO_WHILE→while, HUMAN_TASK→Update/Signal
6. **Run end-to-end**: Start dev server → Start worker → Execute workflow → Validate
7. **Success criteria**: mypy strict passes, workflow executes successfully

---

## ⚠️ Critical Migration Requirements

**BEFORE writing any Temporal workflow code, you MUST:**

### 1. Examine Your Conductor JSON Against the Primitives Reference

**Every Conductor task type has specific Temporal mappings.** You must cross-reference your Conductor JSON workflow definition with the [Primitives Reference](./conductor-primitives-reference.md) to ensure correct translation.

**Required actions:**
- Identify each task type in your Conductor JSON (`SIMPLE`, `FORK_JOIN`, `SWITCH`, `DO_WHILE`, `HTTP`, `WAIT`, `HUMAN_TASK`, etc.)
- Look up each task type in [conductor-primitives-reference.md](./conductor-primitives-reference.md)
- Follow the documented Temporal pattern for each primitive
- Pay special attention to configuration details (retry policies, timeouts, loop conditions, etc.)

**Example:** If your Conductor JSON has a `DO_WHILE` task, you MUST read the "While Loops" section in the primitives reference to understand:
- How `loopCondition` translates to Python while logic
- When to use `continue-as-new` for long-running loops
- How iteration counters map from `${taskRef.output.iteration}` to Python variables

### 2. Identify and Implement Human-in-the-Loop Patterns

**If your workflow has human interaction, you MUST read the Human Interaction guide.**

**Check your Conductor JSON for these patterns:**
- `HUMAN_TASK` task types
- `WAIT` tasks waiting for external events
- DO_WHILE loops checking for approval status
- References like `${user_action.output.approved}` or `${reviewer.output.decision}`

**If ANY of these exist, you MUST:**
1. Read [conductor-human-interaction.md](./conductor-human-interaction.md) completely
2. Determine whether to use Signals (fire-and-forget) or Updates (request-response)
3. Implement proper timeout handling for human responses
4. Follow the documented patterns for approval workflows, multiple reviewers, or approval loops

**Why this matters:**
- Human interaction patterns are NOT straightforward task-to-activity mappings
- Signals and Updates have different semantics and use cases
- Incorrect implementation can lead to workflows that hang indefinitely or fail validation

---

## Documentation Structure

This guide is organized into specialized documents for different aspects of the migration process:

### 📚 [Architecture Reference](./conductor-architecture.md)
**Understanding Conductor vs Temporal**

Learn the fundamental architectural differences between Conductor and Temporal, and how to map Conductor concepts to Temporal implementations.

**Topics covered:**
- Core architectural shifts (JSON DSL → Python code)
- Task type mappings (SIMPLE, HTTP, FORK_JOIN, SWITCH, etc.)
- Control flow pattern translations with code examples
- Data passing from JSONPath to Python
- Key differences in determinism, state persistence, and error handling

**Use this when:**
- You're new to Temporal and need to understand the conceptual differences
- You need a reference for how specific Conductor task types map to Temporal
- You're translating complex control flow patterns

---

### 🛠️ [Migration Guide](./conductor-migration-guide.md)
**Step-by-Step Migration Instructions**

Complete, phase-by-phase instructions for migrating a Conductor workflow to Temporal.

**Topics covered:**
- **Prerequisites**: Required tools and setup
- **Phase 1: Analysis & Setup**: Parse Conductor JSON and create project structure
- **Phase 2: Code Generation**: Generate activities, workflows, worker, and starter
- **Phase 3: Deployment**: Documentation

**Use this when:**
- You're actively performing a migration
- You need detailed step-by-step instructions for each phase
- You want verification commands and common issues for each step

---

### ✅ [Quality Assurance](./conductor-quality-assurance.md)
**Validation, and Success Criteria**

Standards and procedures for ensuring your migration meets production-quality requirements.

**Topics covered:**
- Validation procedures (syntax, type checking)
- Migration success criteria and quality gates
- Code quality standards and best practices
- Performance standards and documentation requirements

**Use this when:**
- You need to verify your migration meets quality standards
- You want to establish quality gates for your project

---

### 🔧 [Troubleshooting Guide](./conductor-troubleshooting.md)
**Solutions to Common Issues**

Comprehensive troubleshooting reference with solutions from real migrations.

**Topics covered:**
- Common migration issues (JSON parsing, timeouts, type errors, etc.)
- **Critical documented pitfalls** with tested solutions:
  - Workflow sandbox violations (CRITICAL)
  - Wrong RetryPolicy import
- Quick diagnostic checklist
- Next steps after migration
- Reference migration script template

**Use this when:**
- Your migration is failing and you need to diagnose the issue
- You encounter workflow sandbox violations
- You want to avoid common pitfalls encountered in real migrations
- You need guidance on production readiness and optimization

---

## Getting Started

### First-Time Users
1. Start with the [Architecture Reference](./conductor-architecture.md) to understand the conceptual differences
2. Review prerequisites in the [Migration Guide](./conductor-migration-guide.md)
3. **CRITICAL:** Before writing code, examine your Conductor JSON:
   - Cross-reference each task type with [Primitives Reference](./conductor-primitives-reference.md)
   - Check for human interaction patterns (HUMAN_TASK, WAIT, approval loops)
   - If human interaction exists, read [Human Interaction Patterns](./conductor-human-interaction.md)
4. Follow the phase-by-phase instructions in the [Migration Guide](./conductor-migration-guide.md)
5. Use the [Quality Assurance](./conductor-quality-assurance.md) checklist to verify your migration
6. Refer to [Troubleshooting](./conductor-troubleshooting.md) if you encounter issues

### Experienced Users
1. Validate your Conductor JSON: `jq empty workflow.json`
2. **CRITICAL:** Examine your Conductor JSON against [Primitives Reference](./conductor-primitives-reference.md) and [Human Interaction Patterns](./conductor-human-interaction.md)
3. Jump directly to [Migration Guide](./conductor-migration-guide.md) Phase 1
4. Use [Troubleshooting](./conductor-troubleshooting.md) Quick Diagnostic Checklist if issues arise
5. Verify completion with [Quality Assurance](./conductor-quality-assurance.md) checklist

---

## Success Criteria

Your migration is complete when:

✅ All Python files pass syntax validation
✅ `mypy --strict` passes with no errors
✅ Documentation is complete
✅ Code follows quality standards

See [Quality Assurance](./conductor-quality-assurance.md) for detailed criteria.

---

## Additional Resources

- **Temporal Documentation**: https://docs.temporal.io/
- **Temporal Python SDK**: https://github.com/temporalio/sdk-python
- **Temporal Samples**: https://github.com/temporalio/samples-python
- **Conductor Documentation**: https://conductor.netflix.com/
- **Community Support**: https://temporal.io/slack

---

## Quick Links

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [Architecture Reference](./conductor-architecture.md) | Understand concepts and mappings | Learning, reference during translation |
| [Primitives Reference](./conductor-primitives-reference.md) | Detailed primitive-by-primitive mappings | Translating specific Conductor constructs |
| [Migration Guide](./conductor-migration-guide.md) | Step-by-step instructions | Active migration, detailed procedures |
| [Human Interaction Patterns](./conductor-human-interaction.md) | Signals, updates, and approvals | Workflows with HUMAN_TASK or human input |
| [Quality Assurance](./conductor-quality-assurance.md) | Standards and validation | Verifying quality, defining requirements |
| [Troubleshooting](./conductor-troubleshooting.md) | Issue resolution | Debugging, avoiding pitfalls |

---

**Ready to begin your migration? Start with the [Architecture Reference](./conductor-architecture.md) or jump straight into the [Migration Guide](./conductor-migration-guide.md)!**

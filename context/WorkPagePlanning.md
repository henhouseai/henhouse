# Work Page Planning

This document describes how agents should create and structure WorkPage modules (dockets, asks, tasks, steps) when planning work with the human operator.

## Work-Ready State

Work is considered "ready to start" when:
- The ask has been broken down into appropriate tasks
- Each task has been broken down into appropriate steps (unless the task is simple enough to not need steps)
- Each tier has page text appropriate for its scope
- Parent tiers synthesize their children rather than repeating detailed information

## Page Text Detail Level

The amount of detail in page text depends on whether the work item has children:

**If it has children**: The page text should be a broad-level synthesis/summary of all its children. It should not repeat fine-grained details that are already in the children's page texts. Instead, it should synthesize and summarize what all the children accomplish together.

**If it has no children (lowest tier)**: The page text should be fully descriptive with all implementation details needed to complete that work item.

## Hierarchy and Scope

### Tasks Are High-Level Work Units

Tasks should represent major phases of work, not individual implementation steps. Common task types include:
- **Code Review**: Verify planning matches codebase, catch planning errors before implementation
- **Implementation**: The actual code changes
- **Testing**: Smoke tests, thorough tests, edge case testing
- **Documentation**: Updating docs, cross-referencing
- **Audit**: Review and validation after completion

### Steps Are Detailed Breakdowns

Steps break down tasks into specific, actionable work items. Each step should have detailed page text describing exactly what needs to be done.

### When to Skip Tiers

- **Single-step task**: If a task would only have one step, put all the detail in the task's page text instead of creating a trivial single step.
- **Simple ask**: If an ask is so simple that breaking it into tasks seems unnecessary, the ask itself can be the lowest tier with fully detailed page text.

These decisions are made on a case-by-case basis based on the actual scope of the work.

## Planning Workflow

### Initial Planning

When an agent creates a new ask, it may start as a quick jot-down or general idea. This is acceptable - not all asks need to be fully planned immediately.

### Fleshing Out Work

When preparing work to be "work-ready" (ready for implementation), the ask should be:
1. Broken down into appropriate tasks (high-level work units)
2. Each task broken down into appropriate steps (detailed work items)
3. Page texts updated appropriately:
   - Steps: Fully detailed implementation instructions
   - Tasks: Synthesis of what all their steps accomplish
   - Asks: Synthesis of what all their tasks accomplish

## Determining Appropriateness

Agents should review all tiers of a work item to determine if it's ready:
- Does each tier have page text appropriate for its scope?
- Do parent tiers synthesize their children rather than repeat details?
- Is the work broken down to an appropriate level (typically to the step level)?
- Are tasks high-level work units (not just implementation steps)?

If all criteria are met, the work is ready to start. If not, it needs further planning and refinement.

## Key Principles

- **Synthesis over repetition**: Parent tiers should synthesize children, not duplicate their details
- **Appropriate granularity**: Work should be broken down to the step level for implementation
- **Context-aware decisions**: Agents should make decisions based on the actual scope and complexity of the work, not rigid rules
- **Work-ready or not**: Work is either ready to start (meets all criteria) or it's not (needs more planning)


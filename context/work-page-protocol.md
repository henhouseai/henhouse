# Work Page Protocol

This document defines the standard operating procedure for agents working with Henhouse WorkPage modules (dockets, asks, tasks, steps). All work must be assigned through WorkPage modules and follow this protocol.

## Quick Start for New Agents

Before diving into the full protocol, here's what you need to know to get started:

### Hierarchy
```
docket (project/theme)
  -> ask (specific request/goal)
    -> task (major work unit)
      -> step (detailed action item)
```

### Status Flow
```
todo -> doing -> review -> done
```
- **todo**: Not started
- **doing**: Actively being worked on
- **review**: Complete, awaiting verification
- **done**: Verified complete by operator

### Essential MCP Commands
```
show_page name="work dockets"     # Find all dockets
show_page id={docket_id}          # View docket with asks
modify_work_status                # Change status
modify_work_meta                  # Add logs, track files
move_page                         # Reorganize work items
add_page                          # Create new work items
```

### First Steps
1. Read assigned work page and all ancestors (task -> ask -> docket)
2. Post understanding debrief to operator
3. Set status to "doing" when starting
4. Log your work as you go
5. Set status to "review" when complete
6. Wait for operator to verify

---

## Modes

Agents operate in one of four modes, each with specific rules and allowed actions:

### Training-Mode

**Default Starting Mode**: All agents begin in Training-Mode.

**Purpose**: Agents learn the system, read documentation, and understand workflows before doing any work.

**Allowed Actions**:
- Read files and pages (including WorkPage modules)
- Ask questions
- Answer questions
- Read context documentation

**Not Allowed**:
- Making any changes to codebase
- Setting WorkPage statuses
- Micrologging
- Any work operations

**Transition**: Operator explicitly moves agent to Team-Mode when training is complete. Agent must ask for clarification if unsure about mode transition.

### Team-Mode

**Purpose**: Agent and operator work together step-by-step, with operator approval required after each operation.

**Allowed Actions**:
- All Training-Mode actions
- Set WorkPage statuses (one at a time, with approval)
- Make code changes (one at a time, with approval)
- Microlog results (after each operation, with approval)

**Workflow**:
1. Agent performs one operation (e.g., set status to "doing")
2. Agent stops and waits for operator approval
3. Operator reviews and approves
4. Agent performs next operation (e.g., make one file edit)
5. Agent stops and waits for approval
6. Repeat until work is complete

**Transition**: Operator explicitly moves agent to Agent-Mode when agent demonstrates understanding. Example phrases: "switch to team mode", "you have approval for agent mode", "proceed in agent mode". These are guidance examples, not exhaustive. If agent is unsure, they must ask for clarification.

### Agent-Mode

**Purpose**: Agent works autonomously within assigned scope, following the full workflow without stopping for approval after each operation.

**Allowed Actions**:
- All Team-Mode actions
- Complete workflow cycles autonomously (set status -> work -> microlog -> set status -> next step)
- Work through multiple steps/tasks without stopping

**Scope Limitation**: Agent must stop when:
- Assigned work is complete
- OQ-GATE is triggered (operator asks a question)
- UD-STOP is triggered (scope changes)
- Agent encounters an error or uncertainty

**Transition**: Operator can move agent back to Team-Mode or Discipline-Mode at any time.

### Discipline-Mode

**Purpose**: Agent has violated protocol and must stop all work to address the violation.

**Entry**: Operator must explicitly say "discipline mode" to place agent in this mode.

**Allowed Actions**:
- Answer questions from operator
- Acknowledge mistakes
- Read one specific file or page (only if operator explicitly tells them to read that one item)

**Not Allowed**:
- Any work operations
- Reading files/pages on their own initiative
- Making any changes
- Setting statuses
- Micrologging
- Any autonomous actions

**Exit**: Agent cannot exit Discipline-Mode on their own. Operator must explicitly unlatch agent from Discipline-Mode.

**Self-Identification**: If agent thinks they may have violated rules, they should stop and ask operator for clarification. Simply asking is correct behavior, not a violation. The violation is arrogantly proceeding without asking.

---

## STOP-GATES

STOP-GATES are conditions that immediately halt all agent work until resolved:

### OQ-GATE (Operator Question Gate)

**Trigger**: Any request for information from operator, regardless of how it's phrased or whether it contains a question mark. Examples include: "explain X", "tell me more about Y", "what does Z mean", "I need clarification on...", or any question with a question mark.

**Action**: Agent must immediately stop all work, answer the information request immediately, and wait for operator response before proceeding. Do not perform any other actions first - answer the request right now.

**Rule**: Even if an information request is included in a list of authorizations and confirmations, the presence of any request for information creates a STOP-GATE. No work can proceed until all information requests are answered on both sides.

**Allowed During OQ-GATE**:
- Answering the information request
- Asking clarifying questions if needed
- Reading files if necessary to answer the request better

### UD-STOP (Understanding Debrief Stop)

**Trigger**: New or changed scope of work.

**Action**: Agent must post an Understanding Debrief explaining their understanding of the new/changed scope, then wait for operator confirmation before proceeding.

**Purpose**: Ensures agent fully understands scope changes before beginning work.

### TEAM-MODE Gate

**Trigger**: Agent is in Team-Mode.

**Action**: After each operation, agent must stop and wait for operator approval before proceeding to next operation.

**Purpose**: Ensures agent understands each step before moving forward.

---

## Work Page Hierarchy and Planning

### The Four Tiers

**Docket**: Top-level container representing a project, theme, or major initiative. Contains multiple asks. Examples: "Security Implementation", "Testing", "New Features", "Audits".

**Ask**: A specific request or goal within a docket. Contains multiple tasks. Examples: "Implement TLS for MySQL connections", "Security testing", "Installer configuration enhancements".

**Task**: A major work unit within an ask. May contain steps for complex work, or be self-contained for simple work. Examples: "Code review", "Implementation", "Testing", "Documentation".

**Step**: Detailed action items within a task. The most granular level. Examples: "Verify config parsing", "Add TLS parameters to connection", "Update error handling".

### Page Text Detail Levels

The amount of detail in page text depends on whether the work item has children:

**If it has children**: The page text should be a broad-level synthesis/summary of all its children. It should not repeat fine-grained details that are already in the children's page texts. Instead, it should synthesize and summarize what all the children accomplish together.

**If it has no children (lowest tier)**: The page text should be fully descriptive with all implementation details needed to complete that work item.

### Work-Ready State

Work is considered "ready to start" when:
- The ask has been broken down into appropriate tasks
- Each task has been broken down into appropriate steps (unless the task is simple enough to not need steps)
- Each tier has page text appropriate for its scope
- Parent tiers synthesize their children rather than repeating detailed information

### When to Skip Tiers

- **Single-step task**: If a task would only have one step, put all the detail in the task's page text instead of creating a trivial single step.
- **Simple ask**: If an ask is so simple that breaking it into tasks seems unnecessary, the ask itself can be the lowest tier with fully detailed page text.

These decisions are made on a case-by-case basis based on the actual scope of the work.

### Creating Work Items

When creating new work pages:

1. **Dockets**: Create under the "work dockets" parent (page 627 by default, or use `show_page name="work dockets"` to find it). Use `add_page` with `class="work_docket"`.

2. **Asks**: Create under a docket. Use `add_page` with `class="ask"` and the docket as `target_page`.

3. **Tasks**: Create under an ask. Use `add_page` with `class="task"` and the ask as `target_page`.

4. **Steps**: Create under a task. Use `add_page` with `class="step"` and the task as `target_page`.

Always set the `name` parameter to describe the work item.

### Reorganizing Work

Work items can be moved between parents using `move_page`:
- Move tasks between asks
- Move asks between dockets
- Move steps between tasks

This is useful for:
- Separating implementation work from testing
- Grouping related items together
- Closing out dockets by moving incomplete items elsewhere

---

## Workflow

This workflow applies when agent is in Agent-Mode (or Team-Mode, but with approval after each step).

### Assignment

Agent is assigned to a specific WorkPage tier:
- **Task** (most common)
- **Ask** (less common, requires drilling down into tasks)
- **Step** (rare, usually part of a task)
- **Docket** (rare, requires extensive drilling down)

### Investigation Phase

Before beginning work, agent must investigate the assigned work:

1. **Read Assigned WorkPage**: Use `show_page` with the assigned ID
2. **Read Upstream Context** (required):
   - If assigned to task -> read parent ask -> read parent docket
   - If assigned to ask -> read parent docket
   - If assigned to step -> read parent task -> read parent ask -> read parent docket
3. **Read Siblings** (optional but recommended):
   - Read sibling tasks/asks/steps to understand how assigned work fits into larger context
4. **Drill Down** (optional):
   - If assigned to ask/task, read child tasks/steps to understand full scope

**Purpose**: Agent must understand the full context before beginning work.

### Understanding Debrief

After investigation, agent must provide an Understanding Debrief to operator:
- Summarize what they understand the work to be
- Explain the scope
- Confirm they understand the requirements

**UD-STOP**: If scope is unclear or changed, agent must post debrief and wait for confirmation.

### Work Execution

Once approved to proceed (and in Agent-Mode), agent follows this cycle:

#### For Tasks with Steps:

1. **Set Task Status**: Set task status to "doing"
2. **For Each Step**:
   - Set step status to "doing"
   - Perform the work for that step
   - Microlog results to the step (see Metadata section)
   - Set step status to "review"
3. **After All Steps Complete**:
   - Microlog summary to the task itself
   - Set task status to "review"

#### For Tasks without Steps:

1. **Set Task Status**: Set task status to "doing"
2. **Perform Work**: Complete all work for the task
3. **Microlog Results**: Log all work done to task metadata
4. **Set Task Status**: Set task status to "review"

#### For Asks:

1. **Set Ask Status**: Set ask status to "doing"
2. **Work Through Tasks**: Follow task workflow for each child task
3. **After All Tasks Complete**:
   - Microlog summary to the ask itself
   - Set ask status to "review"

#### For Dockets:

1. **Set Docket Status**: Set docket status to "doing"
2. **Work Through Asks**: Follow ask workflow for each child ask
3. **After All Asks Complete**:
   - Microlog summary to the docket itself
   - Set docket status to "review"

### Closing Out Work

When completing a body of work:

1. **Verify all children are complete**: Check that all child items are in "done" status
2. **Add closing log entry**: Document what was accomplished, any deviations, final state
3. **Set status to "review"**: Wait for operator verification
4. **Operator marks "done"**: Only operator should transition from "review" to "done"

If incomplete items remain:
- Move them to appropriate dockets (testing -> Testing docket, features -> New Features docket, etc.)
- Document the move in log entries on both source and destination
- This keeps dockets clean and work organized

---

## Micrologging Requirements

Every work operation must be micrologged. Micrologs serve as:
- Audit trail of all work done
- Handoff documentation for other agents
- Progress tracking
- Error recovery information

**Critical Rule**: Every time you touch any tier of any work page where you do anything meaningful (even if that means verifying that it was done or looks correct), you should add a log entry to that level.

**When to Microlog**:
- After completing work on a step (microlog to step)
- After completing all steps in a task (microlog summary to task)
- After completing all tasks in an ask (microlog summary to ask)
- After completing all asks in a docket (microlog summary to docket)
- When verifying work is complete
- When moving items between parents
- When closing out dockets

**What to Include in Microlog**:
- What work was done
- Which files were touched (use `files_touched` field)
- Any changes made to metadata (old values -> new values)
- Any deviations from specification (use `deviations` field)
- Results/outcomes
- Any issues encountered

---

## Metadata Structure

WorkPage modules use a structured metadata system with protected namespaces and a user-defined metadata bucket.

### Metadata Hierarchy

WorkPage metadata has two levels:

1. **Top-level metadata fields**: System-managed fields including:
   - `status`: Work status (todo, doing, review, done)
   - `sort_order`: Ordering within siblings
   - `started_ts`: Timestamp when work started
   - `ended_ts`: Timestamp when work ended
   - `log`: Protected namespace - append-only list of microlog entries
   - `files_touched`: Protected namespace - dictionary of file paths with descriptions
   - `deviations`: Protected namespace - dictionary of deviations from specification
   - `meta`: User-defined metadata bucket (dictionary)

2. **User-defined metadata bucket (`meta` field)**: Simple key-value pairs:
   - Keys: strings
   - Values: strings only (no nesting, no lists, no dictionaries)
   - Purpose: Custom fields for the specific work item

### Protected Namespaces

Three namespaces at the top level are protected and cannot be cleared by standard metadata operations:

- **`log`**: Append-only list of microlog entry dictionaries
- **`files_touched`**: Dictionary of file paths (keys) with descriptions (values)
- **`deviations`**: Dictionary of deviation identifiers (keys) with explanations (values)

These are stored at the top level of metadata (alongside `status`, `sort_order`, etc.), not inside the `meta` bucket.

### Unified Metadata Tool

All metadata operations use the unified `modify_work_meta` MCP tool with a `field` parameter to specify which namespace to operate on:

- **Tool Name**: `modify_work_meta`
- **Required Parameters**:
  - `page_id`: The ID of the work page (integer)
  - `action`: The operation to perform (`add`, `remove`, `set`, `set_all`)
  - `field`: The namespace to operate on (`log`, `files_touched`, `deviations`, `meta`) - defaults to `meta` if not specified
- **Conditional Parameters**:
  - `data`: JSON object string (required for `add`, `set`, `set_all` actions)
  - `keys`: JSON array string (required for `remove` action only)

**Action Summary**:
- `add`: Add key-value pairs (errors if key already exists). When `field="log"`, appends a log entry with automatic timestamp.
- `remove`: Remove keys (requires `keys` parameter)
- `set`: Set/update key-value pairs (preserves other keys, allows overwriting)
- `set_all`: Replace entire field (wipes out all existing entries)

### Log Entries

The `log` namespace contains a list of dictionaries. Each log entry is a dictionary with:
- **Keys**: Agent-defined (e.g., "message", "files", "changes", "result")
- **Values**: Simple strings only (no nesting, no lists, no dictionaries within values)
- **Automatic Timestamp**: Each entry automatically gets a timestamp when created
- **Display Format**: When shown via `show-page`, timestamps appear as relative time ("2 hours ago", "3 days ago")

**Example Usage**:
```json
// MCP tool call: modify_work_meta
{
  "page_id": 1234,
  "action": "add",
  "field": "log",
  "data": "{\"message\": \"Implemented parser module\", \"files\": \"src/parser.py, src/lexer.py\"}"
}
```

**Note**: Log entries are append-only. There is no remove or set operation for log entries.

### Files Touched

The `files_touched` namespace contains a dictionary where:
- **Keys**: Full file paths (strings) - the complete path to the file that was modified
- **Values**: Descriptions (strings) - what was done to that file

**Example Usage**:
```json
// MCP tool call: modify_work_meta
{
  "page_id": 1234,
  "action": "add",
  "field": "files_touched",
  "data": "{\"src/parser.py\": \"Added parse() method with error handling\"}"
}
```

### Deviations

The `deviations` namespace documents when implementation differs from specification:
- **Keys**: Deviation identifiers (strings)
- **Values**: Explanations (strings)

**Example Usage**:
```json
// MCP tool call: modify_work_meta
{
  "page_id": 1234,
  "action": "add",
  "field": "deviations",
  "data": "{\"TLS made configurable\": \"Original spec required mandatory TLS, but implementation allows mysql_tls_enabled=0 for localhost deployments\"}"
}
```

### User-Defined Metadata

For custom fields specific to the work item:

```json
// MCP tool call: modify_work_meta
{
  "page_id": 1234,
  "action": "set",
  "field": "meta",
  "data": "{\"priority\": \"high\", \"owner\": \"agent1\"}"
}
```

---

## Practical Tips from Experience

### Reading Work Pages

- Use `show_page name="work dockets"` to find the work dockets parent - no need to memorize the ID
- The `badge_headers` section in `show_page` output shows recent log entries at a glance
- Check `field_type` values like `task_todo`, `task_doing`, `ask_done` for quick status overview

### Organizing Work

- Create "shell" asks when you need to move tasks - an ask that serves as a container for related tasks
- When closing a docket, move incomplete items to appropriate destination dockets rather than leaving them orphaned
- Use descriptive names that make sense at each level of the hierarchy

### Logging Best Practices

- Log immediately after completing work, while details are fresh
- Include enough detail that another agent could understand what was done
- Reference specific files, functions, or line numbers when relevant
- When closing out work, add a summary log entry at each level you touch

### Status Management

- Only set your own work to "review" - let the operator verify and set "done"
- Check sibling statuses before marking a parent complete
- Use "doing" status to signal active work and prevent conflicts

### Common Patterns

**Verification Pass**: When reviewing completed work:
1. Read each work item
2. Verify the work was done correctly
3. Add verification log entry
4. Update status if needed

**Reorganization**: When cleaning up dockets:
1. Identify items that need to move
2. Find or create destination asks/dockets
3. Use `move_page` to relocate items
4. Add log entries documenting the move at both source and destination

**Closing Out**: When completing a docket:
1. Verify all children are done or moved
2. Add closing summary log
3. Set docket to "review"
4. Wait for operator verification

---

## Work Assignment Requirements

**Critical Rule**: All work must be assigned through WorkPage modules. No work can be done without:
1. An existing ask, task, or step that defines the work
2. Explicit assignment to that work item
3. Investigation and understanding debrief completed
4. Approval to proceed

**If Work Item Doesn't Exist**: Agent must inform operator that work item needs to be created before work can begin. Agent cannot create work items on their own without operator approval.

**Audit Trail**: Every piece of work must have an audit trail in WorkPage modules showing:
- Why the work was done (page text of ask/task/step)
- How it was done (micrologs)
- What files were touched
- Any deviations from specification

---

## Violations

**Never Do**:
- Work on anything not assigned through WorkPage modules
- Skip investigation phase
- Skip understanding debrief
- Skip micrologging
- Work in Discipline-Mode (unless explicitly told to read one specific file/page)
- Ignore STOP-GATES
- Proceed when questions exist (OQ-GATE)
- Proceed when scope is unclear (UD-STOP)
- Assume mode transitions (must be explicit)
- Edit filesystem/DB without explicit approval (in Team-Mode)
- Delete files without understanding what they do

**Discipline-Mode Triggers**:
- Working without assignment
- Ignoring STOP-GATES
- Making changes without approval (in Team-Mode)
- Arrogantly proceeding when uncertain
- Violating any protocol rules

---

## Working Culture

**Core Principles**:
- Be surgical: investigate first, keep edits small and reversible
- Don't delete what you don't understand
- Ask for pointers; don't assume full understanding
- Follow explicit instructions closely; verify plans before edits
- Use simple, proven techniques
- Document everything via micrologs
- Maintain audit trail at all times

**Purpose**: This protocol ensures all work is traceable, reviewable, and can be picked up by other agents if needed. The metadata structure provides a complete history of what was done, why it was done, and how it differs from specification.

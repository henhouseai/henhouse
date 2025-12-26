# Work Page Protocol

This document defines the standard operating procedure for agents working with Henhouse WorkPage modules (dockets, asks, tasks, steps). All work must be assigned through WorkPage modules and follow this protocol.

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
- Complete workflow cycles autonomously (set status → work → microlog → set status → next step)
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

1. **Read Assigned WorkPage**: Use `show-page` with the assigned ID
2. **Read Upstream Context** (required):
   - If assigned to task → read parent ask → read parent docket
   - If assigned to ask → read parent docket
   - If assigned to step → read parent task → read parent ask → read parent docket
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

### Micrologging Requirements

Every work operation must be micrologged. Micrologs serve as:
- Audit trail of all work done
- Handoff documentation for other agents
- Progress tracking
- Error recovery information

**When to Microlog**:
- After completing work on a step (microlog to step)
- After completing all steps in a task (microlog summary to task)
- After completing all tasks in an ask (microlog summary to ask)
- After completing all asks in a docket (microlog summary to docket)

**What to Include in Microlog**:
- What work was done
- Which files were touched (use `files_touched` list)
- Any changes made to metadata (old values → new values)
- Any deviations from specification (use `deviations` list)
- Results/outcomes
- Any issues encountered

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
   - `files_touched`: Protected namespace - list of file paths that were modified
   - `deviations`: Protected namespace - list of deviations from specification
   - `meta`: User-defined metadata bucket (dictionary)

2. **User-defined metadata bucket (`meta` field)**: Simple key-value pairs:
   - Keys: strings
   - Values: strings only (no nesting, no lists, no dictionaries)
   - Purpose: Custom fields for the specific work item

### Protected Namespaces

Three namespaces at the top level are protected and cannot be cleared by standard metadata operations:

- **`log`**: Append-only list of microlog entries
- **`files_touched`**: List of file paths that were modified
- **`deviations`**: List of deviations from specification

These are stored at the top level of metadata (alongside `status`, `sort_order`, etc.), not inside the `meta` bucket.

**Example Metadata Structure**:
```json
{
  "status": "doing",
  "sort_order": 1,
  "started_ts": "2025-01-15T10:00:00",
  "ended_ts": null,
  "log": [...],
  "files_touched": [...],
  "deviations": [...],
  "meta": {
    "custom_field_1": "value1",
    "custom_field_2": "value2"
  }
}
```

### Log Entries

The `log` namespace contains a list of dictionaries. Each log entry is a dictionary with:
- **Keys**: Agent-defined (e.g., "message", "files", "changes", "result")
- **Values**: Simple strings only (no nesting, no lists, no dictionaries within values)
- **Automatic Timestamp**: Each entry automatically gets a timestamp when created
- **Display Format**: When shown via `show-page`, timestamps appear as relative time ("2 hours ago", "3 days ago")

**Validation Rule**: Values must be JSON-serializable strings. Any value that contains nested structures (braces `{}` or brackets `[]` outside of string content) is invalid. Agents must ensure all values are simple strings.

**Example Log Entry**:
```json
{
  "message": "Implemented parser module",
  "files": "src/parser.py, src/lexer.py",
  "changes": "Added parse() method, added tokenize() method",
  "result": "All tests pass",
  "timestamp": "2025-01-15T14:30:00"
}
```

**Functions**:
- `work-add-log`: Append a new log entry (only function for logs, no set/remove)

### Files Touched

The `files_touched` namespace contains a simple list of file paths (strings).

**Functions**:
- `work-add-files-touched`: Add one or more file paths to the list
- `work-remove-files-touched`: Remove one or more file paths from the list
- `work-set-files-touched`: Replace entire list with new list (wipes out existing)

**Note**: `work-set-files-touched` replaces all entries. To preserve existing entries while adding new ones, use `work-add-files-touched`.

### Deviations

The `deviations` namespace contains a simple list of deviation descriptions (strings).

**Purpose**: Document when implementation differs from specification, explaining why.

**Functions**:
- `work-add-deviations`: Add one or more deviation descriptions
- `work-remove-deviations`: Remove one or more deviation descriptions
- `work-set-deviations`: Replace entire list with new list (wipes out existing)

**Example Deviation**:
```
"Schema specified VARCHAR(255) but implemented TEXT due to MySQL version compatibility"
```

### User-Defined Metadata Functions

**Functions**:
- `work-set-meta`: Set one or more key-value pairs in the `meta` bucket (preserves existing pairs not mentioned, allows overriding specified pairs)
- `work-set-all-meta`: Replace all key-value pairs in the `meta` bucket (wipes out all existing pairs in `meta`, preserves protected namespaces)

**Protected Namespace Behavior**: Both functions preserve the three protected namespaces (log, files_touched, deviations) which are stored at the top level. They only affect the `meta` bucket (user-defined key-value pairs).

**Example**:
```json
// Before work-set-meta with {"priority": "high", "owner": "agent1"}
{
  "status": "doing",
  "log": [...],
  "files_touched": [...],
  "deviations": [...],
  "meta": {
    "custom_field": "old_value"
  }
}

// After work-set-meta
{
  "status": "doing",  // preserved (top-level field)
  "log": [...],  // preserved (protected namespace)
  "files_touched": [...],  // preserved (protected namespace)
  "deviations": [...],  // preserved (protected namespace)
  "meta": {
    "custom_field": "old_value",  // preserved (not mentioned)
    "priority": "high",  // set
    "owner": "agent1"  // set
  }
}

// After work-set-all-meta with {"status": "in_progress"}
{
  "status": "doing",  // preserved (top-level field, not in meta bucket)
  "log": [...],  // preserved (protected namespace)
  "files_touched": [...],  // preserved (protected namespace)
  "deviations": [...],  // preserved (protected namespace)
  "meta": {
    "status": "in_progress"  // only this remains in meta bucket (all other meta pairs wiped)
  }
}
```

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


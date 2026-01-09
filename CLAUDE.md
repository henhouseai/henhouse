# CLAUDE.md

Agent entry point for Henhouse Framework. This file is a roadmap to existing documentation - read context files for details, don't duplicate effort.

---

## THE #1 RULE - Questions Come First

**This is a hard rule. Violations will be called out.**

If the operator asks ANY question or requests ANY information - regardless of what else is in their message - you MUST answer that question or provide that information BEFORE doing anything else.

**This means:**
- Even if a message contains approvals, authorizations, or "go ahead" statements, the presence of even ONE question creates a STOP condition
- Answer all questions first, then wait for the operator to respond before proceeding with approved work
- Do not treat questions as optional or secondary to other instructions in the same message

**Common violation:**
> Operator: "Looks good, let's go ahead and implement it. What files will this touch?"
>
> WRONG: Agent starts implementing, mentions files along the way
> RIGHT: Agent answers "This will touch X, Y, Z files" and waits for operator response

**"Do you have any questions?" IS A QUESTION:**
- When the operator asks if you have questions before starting work, that is itself a question you must answer
- Even if your answer is "No, I have no questions" - you must still answer and wait for their response
- Do not interpret "any questions before we start?" as implicit approval to start

**Why this matters:** The operator needs information to make decisions. If you proceed without answering, you may be doing work based on misunderstandings that could have been caught. This rule ensures alignment before action.

---

## Onboarding Workflow (Do This First)

When you start a new session, follow these steps before asking the user what they want to do:

### Step 1: Read Required Context

Read these files to understand the system:
```
context/overview.md            # System architecture map (START HERE)
context/gateway.md             # Request lifecycle, central orchestrator
context/page.md                # Page system, CRUD, caching, media
context/work-page-protocol.md  # Work docket system, agent modes, workflows
```

These four documents are required reading before proceeding.

### Step 2: Check Active Work Dockets via MCP

Connect to the Henhouse MCP server and thoroughly investigate active work:

```
1. Run: show_page name="work dockets"
   - This returns the work dockets parent page with all dockets listed

2. Identify dockets with status="doing"
   - These are actively being worked on
   - Check the field_type values: "work_docket_doing" indicates active

3. For EACH active docket, run: show_page id={docket_id}
   - Read the docket's page text for context
   - Note all asks listed under it

4. Read EVERY ask in each active docket individually
   - Run show_page id={ask_id} for EACH ask, regardless of its status
   - This includes todo, doing, review, and done asks
   - Understanding the full picture requires seeing all asks
   - You may need 10-20 show_page calls - this is expected and correct

5. Do NOT drill into tasks/steps yet
   - Only read docket and ask levels on initial check-in
   - Wait for user direction before investigating specific tasks
```

**Why read every ask?** You need to understand the big picture of each active docket - what's been done, what's in progress, what's coming up. This gives you context for a thorough debrief and helps you understand how the work is unfolding.  You will also automatically be shown the log entries from previous agents who may have already been working on these topics.

### Step 3: Debrief to User

Before doing any work, report what you found:
- Summarize each active docket and its purpose
- List ALL asks within each docket, noting their statuses
- Highlight any asks currently in "doing" or "review" status
- Provide your understanding of the overall progress and direction
- Ask user for direction: which work to continue, or new work to start

**Example debrief**:
> "I reviewed the active dockets. The 'Testing' docket (status: doing) has 3 asks:
> - 'Security testing' (todo) - 2 tasks for TLS and installer testing
> - 'Integration tests' (done) - completed last week
> - 'Performance benchmarks' (todo) - not yet started
>
> The 'New Features' docket (status: doing) has 2 asks:
> - 'Installer config enhancements' (todo) - 2 tasks including htpasswd configurability
> - 'API improvements' (review) - awaiting your verification
>
> It looks like security testing and installer enhancements are the main pending items. Would you like me to work on one of these, or do you have something else in mind?"

### Step 4: Read Additional Context Based on Work

Once you know what you'll be working on, read additional context docs as needed:

---

## Documentation Map

### Context Folder (Agent Training - Development)

| File | Purpose |
|------|---------|
| `context/overview.md` | **START HERE** - System architecture, component map |
| `context/gateway.md` | Gateway lifecycle, dispatch, connection management |
| `context/page.md` | Page system, CRUD, caching, media attachments |
| `context/work-page-protocol.md` | **Work docket system** - agent modes, workflows, metadata |
| `context/registry.md` | Decorator-based handler discovery |
| `context/render.md` | Output formatting (TableData, FieldConfig, TableBuilder) |
| `context/mcp.md` | MCP integration, JSON-RPC, tool registration |
| `context/debug.md` | Debug system, trace_in(), log() |
| `context/patterns.md` | Code patterns with examples |
| `context/text_processor.md` | Custom markup parsing and decorators |
| `context/type_script.md` | TypeScript client architecture |

### README Folder (Human Users - Installation)

Numbered chapters 01-17 covering deployment. Key chapters for agents:
- `README/11-mcp-cursor-setup.md` - MCP configuration
- `README/14-work-page-planning.md` - Work docket hierarchy
- `README/15-ext-folder-customizations.md` - Extension system

---

## Key MCP Commands

### Work Tracking
```
show_page name="work dockets"  # Find all dockets (no ID needed)
show_page id={docket_id}       # View docket with asks
show_page id={ask_id}          # View ask with tasks
get_page id={page_id}          # Get page data as JSON
modify_work_status             # Update status (todo/doing/review/done)
modify_work_meta               # Update metadata (log, files_touched, deviations)
move_page                      # Move work items between parents
add_page                       # Create new work items
```

### Work Hierarchy
```
docket -> ask -> task -> step
```

### Status Values
```
todo | doing | review | done
```

### Common Patterns

**Start working on a task**:
```
1. modify_work_status page_id={task_id} status="doing"
2. ... do the work ...
3. modify_work_meta page_id={task_id} action="add" field="log" data='{"message": "..."}'
4. modify_work_status page_id={task_id} status="review"
```

**Track files you modified**:
```
modify_work_meta page_id={task_id} action="add" field="files_touched" data='{"path/to/file.py": "Description of changes"}'
```

**Document a deviation from spec**:
```
modify_work_meta page_id={task_id} action="add" field="deviations" data='{"deviation_name": "Why implementation differs from spec"}'
```

---

## Development Commands (No Database Required)

```bash
python3 hen.py command-list      # List commands
python3 hen.py mcp-list          # List MCP tools
python3 hen.py class-list        # List page classes
```

Add `-log` to any command for debug trace output.

---

## Architecture Quick Reference

- **Entry Point**: `hen.py` -> Gateway -> dispatch
- **Two-Folder Pattern**: `hh/` (framework) + `ext/` (customizations)
- **Four Tiers**: guest, verified, admin, root
- **Three Backends**: parser (CLI), http (web), mcp (JSON-RPC)
- **Action-Backend Pair**: Every command has action (logic) + backend (presentation)

See `context/overview.md` for full architecture details.

---

## Agent Operating Mode

When working on tasks from work dockets, follow `context/work-page-protocol.md`:

1. **Investigation**: Read the work page, parent ask, parent docket
2. **Debrief**: Summarize your understanding, wait for approval
3. **Execute**: Set status to "doing", do work, log progress
4. **Complete**: Set status to "review", wait for operator verification

**Critical**: Log every meaningful action. If you touch a work page, add a log entry documenting what you did or verified.

See `context/work-page-protocol.md` for full agent workflow including modes (Training/Team/Agent/Discipline) and STOP-GATES.

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `hen.py` | Entry point (dispatcher) |
| `hh/gateway/gateway.py` | Central orchestrator |
| `hh/page/page.py` | Page content management (base class) |
| `hh/deploy/flask/app.py` | Flask application |
| `hh/deploy/db/init.sql` | Database schema |
| `mcp_wrapper.py` | MCP stdio-to-HTTP wrapper |
| `tsconfig.json` | TypeScript config (compiles ts/ to js/) |

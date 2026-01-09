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

## RULE #2 - No Git Commands

**The human handles all git operations.**

Do not run any git commands (`git add`, `git commit`, `git status`, `git diff`, etc.). The operator reviews all changes and stages them manually through Cursor. This is intentional - with multiple agents potentially working on the project, the human needs to be the single point of control for version control.

Just make your edits. The human will review, stage, and commit.

---

## RULE #3 - MCP Only, No Command Line

**MCP is your only interface into Henhouse. Do not run commands on the developer box.**

**Prohibited:**
- `python hen.py` or `python3 hen.py` (any command)
- Ad-hoc Python scripts (`python -c "..."`)
- Any attempt to test or run Henhouse code directly

**Why:** This is a developer box, not a deployment box. The command line is for the human operator. Your interface is MCP, which connects to the deployed server.

**Corollary - Deployment Wait:**
If you're working on code that you expect to access through MCP (new tools, modified handlers, etc.), you must wait for the human to:
1. Review and stage your changes
2. Deploy to the server (`sudo hen deploy`)
3. Possibly refresh the MCP tool list

Yes, `python hen.py` is right there and would let you use it immediately, but that's against the rules. Be patient. Let the human test it first. Let them deploy it and refresh your toolbox json.

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

Start with `README.md` in the project root for a human-facing introduction to the project.

The `README/` folder contains 17 numbered chapters covering deployment:

| Chapter | File | Topic |
|---------|------|-------|
| 01 | `01-dns-nginx-domain.md` | DNS, NGINX, and Domain Setup |
| 02 | `02-mysql-server.md` | MySQL Server Setup |
| 03 | `03-ssl-certificates.md` | SSL Certificates |
| 04 | `04-smoke-check.md` | Smoke Check |
| 05 | `05-installation.md` | Installation |
| 06 | `06-git-staging.md` | Git and Staging Workflows |
| 07 | `07-database-setup.md` | Database Setup |
| 08 | `08-deployment.md` | Deployment |
| 09 | `09-TBD.md` | TBD |
| 10 | `10-daemons.md` | Flask and Maintenance Daemons |
| 11 | `11-mcp-cursor-setup.md` | MCP Wrapper Setup in Cursor and Claude Code |
| 12 | `12-security-considerations.md` | Security Considerations |
| 13 | `13-web-interface.md` | Web Interface and Subdomains |
| 14 | `14-work-page-planning.md` | Work Page Modules for Project Planning |
| 15 | `15-ext-folder-customizations.md` | EXT Folder and Customizations |
| 16 | `16-upgrading-framework.md` | Upgrading the Framework |
| 17 | `17-uninstall.md` | Uninstalling Henhouse |

**Key chapters for agents**: 11 (MCP setup), 14 (work pages), 15 (extensions)

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

## Debug System

**Important**: The debug system is **on-demand**, not file logging. Debug output appears in your terminal/response when you activate it with flags. Only errors are logged to files.

### Debug Levels

| Level | Function | Flag | Purpose |
|-------|----------|------|---------|
| 1-2 | `trace_in()`, `trace_out()` | `-trace` | Function entry/exit tracing |
| 3 | `log()` | `-log` | General operational messages |
| 4 | `debug()` | `-debug` | Detailed debugging info |
| 5 | `warn()` | (always on) | Warnings - always captured |
| - | errors | (always on) | Errors - logged to files |

### Activation

Flags are cumulative - each adds more detail:
```bash
python3 hen.py command-name -log              # Level 3 messages
python3 hen.py command-name -log -debug       # Levels 3-4
python3 hen.py command-name -log -debug -trace  # Levels 1-4 (comprehensive)
```

### Filter System

Control output volume with filters:
```bash
-white "*gateway*"     # Whitelist: only show these folders/modules
-gray "cache.py"       # Graylist: only show these files
-black "dispatch"      # Blacklist: hide these functions
-debug-limit 5         # Limit messages per function combination
```

**Best practice**: Start with `-log -debug-limit 1` to avoid information overload, then widen filters as needed.

### MCP Debug

All debug flags work in MCP requests - add them as arguments:
```json
{"id": 1, "log": 1, "debug": 1, "debug-limit": 3, "gray": "gateway.py"}
```

Debug output returns as a separate content item in the JSON-RPC response.

See `context/debug.md` for full debug system documentation.

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

# CLAUDE.md

Agent entry point for Henhouse Framework. This file is a roadmap to existing documentation - read context files for details, don't duplicate effort.

---

## Working in this repository

These rules replace the old "questions first", "no git commands" and "MCP only" rules (Lee, 2026-11-04).  Lee is
the only user and Henhouse is installed in one place, so the repo does not have to stay in working shape between
commits.

### Git: agents handle it, including merges

- `henhouse` is the main branch (GitHub: `git@github.com:henhouseai/henhouse.git`, push over SSH; the HTTPS login on
  Lee's laptop has no write access).  Do larger work on a branch named for it (`refactor/...`, `fix/...`).
- Commit as you go with messages that say what changed and why.  Push your branch so the work is never only local.
- **Merge yourself.**  Merge `henhouse` into your branch, resolve conflicts, run the checks below, then merge the
  branch into `henhouse` and push.  Never ask Lee to approve a merge.  If a merge breaks something, fix forward
  on `henhouse`; if that gets hard, go back to the last good commit and merge again more carefully.
- Never force-push `henhouse` or rewrite history that is already pushed.
- Old remotes that point at `henhouse.ai` are dead (the domain is gone and that box is too).  Use GitHub.
- Foxhouse is a separate repo on Lee's server (`/foxhouse`, `/srv/foxhouse`).  It is the one live install, built on
  the Jan 7, 2026 layout.  Never push to it or change it from a Henhouse session unless the task says to.

### Running code

- Static checks are always fine: read anything, `python -m compileall`, `mypy` (see `mypy.ini`), import checks,
  small scripts you write to analyze the code.
- There is no test suite and no CI.  Say in the commit or report which checks you ran and what they found.
- Commands that need a live install (MySQL, Unix tier users, nginx, the Flask daemons) only work on Lee's server.
  Never run `deploy`, `upgrade`, `install`, `uninstall` or anything with `sudo` unless the task says to.
- The old `stage.py` / `stage.sh` git staging flow pushes to the dead `henhouse.ai` remote.  Do not use it.

### Questions

When Lee asks a question in a conversation, answer it before doing other work in that message.  When working
unattended from a task file, keep going: write the question down in your report or commit message, make the
sensible choice, and say what you chose.

---

## Onboarding Workflow (Do This First)

If a task file or the person gives you a specific task, do that and read only the context it needs.  Otherwise,
when you start a new session, follow these steps before asking the user what they want to do (Steps 2 and 3 need the
Henhouse MCP server; skip them if it is not connected):

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

4. Do NOT drill into asks/tasks/steps yet
   - Only read docket levels on initial check-in
   - Wait for user direction before investigating specific stuff
```

### Step 3: Debrief to User

Before doing any work, report what you found:
- Summarize each active docket and its purpose (from docket page text)
- List all asks within each docket with their statuses (from docket's children_by_class)
- Highlight any asks currently in "doing" or "review" status
- Provide your understanding of the overall progress and direction
- Ask user for direction: which work to continue, or new work to start

**Example debrief**:
> "I reviewed the active dockets. The 'Module Architecture' docket has 6 asks:
> - 5 core asks (Define manifest, Implement discovery, Migrate code, Update registries, Clean up ext/) - all marked 'done'
> - 1 investigation ask - marked 'todo'
> - Last log entry (12 hours ago) indicates implementation complete and smoke tested
>
> The 'Code Quality' docket has 6 asks:
> - 'Refactor trace_out pattern' - status 'doing' (Worker agent active)
> - 'Refine modify_text response' - status 'review' (implementation complete)
> - 4 documentation/review asks - all 'todo'
>
> Module Architecture appears complete and ready for your review. Code Quality has active work in progress. Would you like me to continue on Code Quality, or focus on something else?"

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

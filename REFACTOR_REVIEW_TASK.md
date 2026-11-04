# Task: review the module refactor and hookified deployment work

Written 2026-11-04 for an unattended cloud session on branch `refactor/hookified-modules`.  Read `CLAUDE.md`
first (its "Working in this repository" rules apply), then this file, then do the task without waiting for input.

## Background

Henhouse is Lee's Python content and project-management framework: pages in MySQL, media, four access tiers,
and three ways in (CLI `hen.py`, Flask web, MCP).  Lee is the only user.  The one live install is **Foxhouse**, a
separate repo on Lee's Ubuntu server that uses Henhouse for an accounting system.  Foxhouse is built on the
**Jan 7, 2026 layout** (commit `48c641a3` here): framework in `hh/`, project add-ons in `ext/`, accounting in
`ext/`.  Accounting is the part Lee cares about most and wants to keep building on.

In January Lee started two linked changes and stopped partway (out of time and money, not because they were a bad
idea):

1. **Folder migration:** move features out of the monolithic `hh/` and out of `ext/` into top-level modules
   (`hh_audio`, `hh_video`, `hh_image`, `hh_file`, `hh_page`, `hh_subpage`, `hh_flask`, `hh_nginx`, `hh_srv`,
   `hh_git`, `hh_user_tiers`, `maintenance`, `accounting`, `self_doc`, `users`, `work`, `puzzle`, `help`,
   `mcp_request`, `mcp_action_request`, ...).
2. **Hookified install and deploy:** each module owns its install, database and deploy steps in its own `deploy/`
   folder, registered with `@register_module_hook` (`hh/gateway/registry/module_hooks.py`); framework scripts become
   thin orchestrators that call `run_hooks()`.  Design: `context/deploy_hooks.md` and `context/modules.md`.  The
   longer-term aim was a "bare metal" core where every feature is optional: Level 0 is gateway, registry,
   hooks and MCP with no database; Level 1 adds database and user tiers; Level 2 pages and media; Level 3
   nginx and Flask.

History on this branch:

- `48c641a3` (Jan 7): old layout, same as Foxhouse.
- Commits from Jan 7 to Jan 21 (`e3a6a719`, "warning test"): most of the migration so far.
- `6137e897`: a snapshot of uncommitted work from Jan 21 to 28, committed as-is.  It is probably half-done: files
  deleted from `hh/`, `audio/` and `video/`, new `hh_audio/`, `hh_file/` and similar folders, database setup
  moved into hooks, and edits to `accounting/`.  Expect broken imports.

## What to do

**Review only.**  Do not change any code; the next session fixes things using your report.  Write
`REFACTOR_REPORT.md` at the repository root, commit it to `refactor/hookified-modules` and push.  Do not merge into
`henhouse`.

Work out what is done and what is left, from the code itself, not from what the docs claim.  Useful checks:

- **Module inventory:** every top-level module: what it contains, whether its `__module__.py` and registrations
  look complete, what it still imports from old locations.  Note code still sitting in `hh/` or `ext/` that
  belongs in a module.
- **Hooks:** list every hook name the framework calls with `run_hooks(...)` and every hook name modules register.
  Report hooks called but never registered, registered but never called, and install/deploy/remove/db phases a
  module needs but lacks.  Note which framework deploy scripts are already thin orchestrators and which still
  hard-code module logic.
- **Broken references:** imports of modules or paths that no longer exist, files referenced by whitelists or
  configs that are gone, and references to the old `audio/`, `video/` and `hh/deploy/db` locations.  Use
  `python -m compileall`, `mypy` with `mypy.ini`, and import checks or small scripts of your own.  You cannot
  connect to MySQL or the server, so stop at what static checks can show.
- **The snapshot commit:** what `6137e897` changed compared with `e3a6a719`, and whether each part looks finished,
  half-done or abandoned.
- **Accounting:** state of `accounting/` as a module, and what moving Foxhouse from the Jan 7 layout (accounting in
  `ext/`) onto this layout would involve.  Use `git show 48c641a3:...` to see the old layout.
- **Docs:** which of `CLAUDE.md` (Architecture Quick Reference and Key Files sections), `context/` and `README/`
  (especially chapters 05, 07, 08, 15 and 16) describe the old layout and need rewriting.

## The report

Start with a short summary: how far along the refactor is, whether the code at the branch tip would even
import, and the three or four biggest gaps.  Then:

1. A table of modules: done / partly done / not started, with one line on what is missing.
2. Hook coverage: called versus registered, and gaps by phase.
3. Broken references, grouped by cause, with file paths.
4. What the snapshot commit did and how finished each part is.
5. Accounting and the Foxhouse migration path.
6. Docs that need rewriting.
7. Recommended order for finishing the work, in chunks one session could do, each with a rough size.
8. Questions for Lee: decisions you could not make from the code.

Name files and line numbers so the next session can act on them.  Say which checks you ran and what they
printed (counts are enough).  End your session with a few lines saying what you found and where the report is.

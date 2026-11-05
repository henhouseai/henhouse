# Refactor review: module migration and hookified install/deploy

Written 2026-11-05 by a review-only session, following `REFACTOR_REVIEW_TASK.md`, on branch
`refactor/hookified-modules` at `50d71ae`.  No code was changed.

## Summary

The folder migration is about **80% done**, but the parts that make the system actually start up are behind.

- **Imports are clean.**  566 of 567 Python modules at the branch tip import without error.  There are no
  imports of modules or names that no longer exist.  The one failure is a real bug (see gap 4).
- **Almost everything has moved out of `hh/`.**  Only `hh/gateway`, `hh/render`, `hh/tp` and `hh/deploy` (the
  orchestrators and their shared helpers) are left.  Pages, media, help, work, MCP requests, Flask and the
  maintenance daemon all live in top-level modules now.
- **The hookified deploy is mostly wired up.**  51 hook names are called and 103 are registered.  Each of the 10
  framework scripts in `hh/deploy` is now a thin loop over a phase list.

The biggest gaps:

1. **Module database schemas are never loaded.**  The snapshot replaced `hh/deploy/db/init_db.py`, which ran every
   active module's `deploy/db/schema.sql` and `example_data.sql`, with hooks.  Only the 5 page and media modules got
   `init_db_*` hooks, so `users`, `history`, `hh_user_tiers`, `puzzle`, `self_doc` and `accounting` schemas no longer
   run.
2. **The `maintenance_jobs` table was dropped.**  It was in the old `hh/deploy/db/init.sql` (line 330) but is in
   none of the new per-module SQL files.  The job queue, the worker, `hh_audio/audio.py` and `hh_video/video.py`
   all still use it.
3. **Three code scanners still only look in `hh/` (and sometimes `ext/`)**, so tools that moved into modules can't
   be found.  At the branch tip the maintenance scan finds no real tools, only the word `tool_name` from a
   docstring, and the download scan finds none.  `upgrade` only copies `hh/`, `context/` and `README/`, so it
   can't carry modules into an install.
4. **`maintenance/page_cache_refresh.py:133`** uses `register_maintenance_tool(...)` as a decorator.  That function
   returns `None`, so importing the file raises `TypeError`.  This is new in the snapshot.

"Bare metal" Level 0 is not reachable yet.  `hh/gateway/gateway.py:34` imports `hh_page`, and `hh/tp` imports
`hh_page` and `hh_image`, so the core can't start without the page module.

## Checks run

| Check | Result |
|---|---|
| `python -m compileall -q .` | exit 0, no syntax errors |
| `mypy --config-file mypy.ini --explicit-package-bases` on `hen.py`, `mcp_wrapper.py` and all 24 modules | 593 files, 5 errors: 1 real bug (`page_cache_refresh.py:124/133`), 1 missing `wcwidth` stub, 2 missing annotations (`maintenance/deploy/flask_aggregator.py:21`, `hh/gateway/registry/maintenance_tasks.py:95`) |
| My own AST import resolver (every `from X import Y` against the tree) | 0 missing modules, 0 missing names |
| Importing every module in one process, from a clean `git archive` copy | 566 ok, 1 failed (`maintenance.page_cache_refresh`) |
| My own AST hook scan (`run_hooks`, `get_hook_handlers`, `register_module_hook`, plus the phase tuples in the orchestrators) | 51 called, 103 registered, details in section 2 |
| `tsc --noEmit` over `hh`, `accounting`, `self_doc` and `users` TypeScript (tsc 6.0) | 4 errors, all side-effect imports of `./sortable.min.js` (TS 6 strictness, not caused by the refactor) |
| Calling the scanners at runtime (`maintenance.all_tools`, `download.all_tools`, `get_active_modules`) | `{'tool_name'}`, `[]`, and 20 active modules (accounting, puzzle, example and history are blacklisted in `ext/deploy/conf/module_blacklist.py`) |
| Path check on every string literal in `*/deploy/conf/*.py` | 12 paths that don't exist (section 3) |
| Foxhouse comparison: 34 files staged from Lee's laptop copy (`henhouse MISC\foxhouse\ext`) and diffed against `accounting/` | section 5 |

Nothing could reach MySQL, the server or Foxhouse's live database, so anything about runtime SQL is from reading
the code.

## 1. Modules

| Module | State | What's missing |
|---|---|---|
| `hh` (core) | Partly done | Still imports `hh_page` (`gateway/gateway.py:34`, `tp/tp.py:7`) and `hh_image` (`tp/tp.py:8`, `tp/tp_decorators.py:7`, `tp/tp_image_decorators.py:8`).  `hh/tp` should probably become its own module.  `hh/deploy/site` still holds all 40 TS files, including media viewers that belong to `hh_audio` and the other media modules. |
| `hh_page` | Mostly done | Imports all four media modules (`page.py`, `media_operations.py`, `data_operations.py` and 8 action files), so pages can't run without media.  `deploy/conf/deploy_whitelist.py:4` lists `page/deploy/conf`, which should be `hh_page/...`.  Empty `schema.sql` and `example_data.sql`.  Cache cleanup path is the old one (`page_class_registry.py:271,281`). |
| `hh_subpage` | Shell only | 5 files.  Whitelist line 4 says `subpage/deploy/conf`.  Empty SQL placeholders.  No hooks. |
| `hh_image`, `hh_file`, `hh_audio`, `hh_video` | Mostly done | Each has `db_hooks.py`, `db_user_hooks.py`, `install_hooks.py`, `tools.py` and its own SQL.  The `hh_audio` and `hh_video` manifests still say `'name': 'audio'` and `'name': 'video'` (`hh_audio/__module__.py:14`, `hh_video/__module__.py:14`).  Each imports `hh_page` (12–13 sites) and `hh_image`.  The viewer TS is still in `hh/deploy/site/ts`. |
| `hh_flask` | Done | Apps in `deploy/apps`, `flask_start`, `flask_status` and `flask_stop` commands, deploy, install and remove hooks.  Empty SQL placeholders. |
| `hh_nginx` | Done | Deploy, install, remove and uninstall hooks. |
| `hh_srv` | Done | Base deploy hooks. |
| `hh_git` | Done | Install hooks and `tsconfig.py` (builds `tsconfig.json` from the active modules).  Whitelist line 4 says `project/deploy/conf`. |
| `hh_user_tiers` | Partly done | Install and uninstall hooks exist, but `install_50_tier_env` is never called (section 2).  `schema.sql` is never loaded. |
| `maintenance` | Partly done | Moved from `hh/deploy/maint` and `hh/deploy/maintenance`.  Its tools aren't discovered (gap 3), `page_cache_refresh.py` crashes on import (gap 4), and the `maintenance_jobs` table is gone (gap 2).  No db hook of its own. |
| `help` | Done | Moved from `hh/help`.  Manifest description is copied from `example` (`help/__module__.py`).  Cache cleanup path is old (`help/help_query.py:293,302`).  Empty SQL placeholders. |
| `work` | Done | Moved from `hh/ask`, `task`, `step`, `work` and `work_docket`.  No `deploy/db` and no hooks, since work pages live in the core `pages` table. |
| `mcp_request`, `mcp_action_request` | Done | Moved from `hh/`.  Only `deploy/conf`. |
| `users` | Partly done | Has a `deploy_hooks.py`, but its 7 KB `schema.sql` and `users_data.sql` are never loaded. |
| `history` | Not wired | Registers `deploy_before_schema` and `deploy_after_schema`, which nothing calls.  `history.sql` and `schema.sql` are never loaded.  Blacklisted by default. |
| `self_doc` | Partly done | Deploy helpers and site TS are in place.  `schema.sql` and `example_data.sql` are never loaded. |
| `accounting` | Partly done | Code is complete (section 5).  `schema.sql` is an empty template.  The 8 TS page classes aren't in the checked-in `tsconfig.json`, though `hh_git/tsconfig.py` should add them.  `deploy/conf/upgrade_preserve.py:14-21` still lists Foxhouse's `ext/` paths.  Blacklisted by default. |
| `puzzle`, `example` | Templates | Blacklisted by default.  `puzzle` has SQL that is never loaded. |
| `ext` | Done (config only) | Only `deploy/conf` overrides are left, and it is itself discovered as a module (`ext/__module__.py`). |

## 2. Hook coverage

**Wired end to end (51 names):** every phase of `init_db`, `add_db_users`, `remove_db_users`, `clean_db`,
`export_db` and `import_db` (`*_00_pre_validate` through `*_95_render`), plus `install_00/01/02/95`,
`deploy_00/95`, `remove_00/95` and `uninstall_95`.  The other install, deploy, remove and uninstall phases are
called through the phase tuples in `hh/deploy/install.py:81-96`, `deploy.py:57-87`, `remove.py:53-61` and
`uninstall.py:53-62`, and every one of them has a registration.

**Registered but never called:**

| Hook | Where registered | Effect |
|---|---|---|
| `install_50_tier_env` | `hh_user_tiers/deploy/install_hooks.py:410` | Tier user environments are never set up on install.  The phase list calls `install_50_user_env` (core human and root users) instead.  This was already true at `e3a6a719`. |
| `deploy_before_schema`, `deploy_after_schema` | `history/deploy/deploy_hooks.py:10,26` | Old-style hook names that nothing calls, so the history database is never created. |

**Called but never registered:** none.

**Gaps by phase:**

- **init_db:** core (`hh/deploy/init_db_hooks.py`) creates the two databases.  Only `hh_page`, `hh_image`,
  `hh_file`, `hh_audio` and `hh_video` register `init_db_15..30`.  These modules have SQL that nothing runs:
  `users`, `history`, `hh_user_tiers`, `puzzle`, `self_doc` and `accounting` (empty).  The old generic loader
  (`e3a6a719:hh/deploy/db/init_db.py:366` for schema, `:463` for example data) wasn't carried over.  The fix
  is either one generic init_db hook in core that runs each active module's `schema.sql`, or a `db_hooks.py`
  per module.
- **clean_db, add_db_users, remove_db_users, export_db, import_db:** same 5 modules only.  `users` and
  `history` tables won't be cleaned, granted, exported or imported.
- **Daemon start after reboot:** no phase registers a systemd unit or `@reboot` entry.  The Linux worker found
  this on the live box (Oct 26 reboot).
- **Two different db layouts:** media modules use `deploy/db/init.sql` and `init_cache.sql`, while other modules
  use `deploy/db/schema.sql`.  Pick one convention.

**Orchestrators:** all 10 scripts in `hh/deploy` (`install`, `uninstall`, `deploy`, `remove`, `init_db`,
`add_db_users`, `remove_db_users`, `clean_db`, `export_db`, `import_db`) are phase loops over `run_hooks`.  Some
module logic is still hard-coded:

- `hh/deploy/uninstall.py:74` imports `hh_user_tiers.deploy.uninstall_hooks.tier_config`.
- `hh/deploy/deploy.py:9` imports `hh_srv.deploy.http.deploy_helpers`.
- `hh/deploy/install_hooks.py` and `uninstall_hooks.py` still own user, group and env work that could belong to
  `hh_user_tiers`.

## 3. Broken references

**Code bug**
- `maintenance/page_cache_refresh.py:133`: `@register_maintenance_tool("page-cache-refresh")` is used as a decorator,
  but `hh/gateway/registry/maintenance.py:131` returns `None`.  Delete the decorator line.  Line 276 already
  registers it the right way.

**Scanners that only look at `hh/` (and `ext/`)**
- `hh/gateway/registry/maintenance.py:70-90` (`_scan_for_maintenance_tools`) misses all 22 tools in
  `maintenance/`, `accounting/` and `hh_image/add_image.py:98`.  The regex also matches its own docstring.
- `hh/gateway/registry/download.py:80-86` misses `hh_file/get_file_info.py`.
- `hh/gateway/system/dependency_list.py:58-61` only scans `hh/`.
- The fix: use `hh/deploy/deploy_utils.py:720` `get_module_paths()`, which `scan_for_decorator()` already uses.
- `hh/deploy/upgrade/upgrade.py:132-190` copies `hh/`, `context/`, `README/` and top-level files only, and
  `validate_target` (line 56) requires `hh/`.  Module folders are never upgraded.

**Lost database objects**
- The `maintenance_jobs` table (old `init.sql:330`) is used by `maintenance/job_queue.py`,
  `maintenance/deploy/apps/*worker.py`, `maintenance/update_maintenance_job.py`, `page_name_update.py`,
  `maintenance_jobs_status.py`, `hh_audio/audio.py` and `hh_video/video.py`.
- Also dropped from `init.sql`, but nothing references them: `agent_*` (8 tables), `watercooler_*` (10),
  `chunk_*`, `context_chunks`, `keywords`, `keyword_aliases`, `entity_*`, `documents`, `bootstrap_*`,
  `sidecar_*` and `coffee_pot_training`.  These look like an old agent system.  Lee should confirm they are
  abandoned (question 3).

**Stale paths in config**
- `hh/deploy/conf/deploy_whitelist.py:6`: `hh/deploy/maint` no longer exists.
- `hh_page/deploy/conf/deploy_whitelist.py:4` says `page/deploy/conf`, `hh_subpage/...:4` says `subpage/deploy/conf`,
  and `hh_git/...:4` says `project/deploy/conf`.  These are copy-paste leftovers from the template.
- `accounting/deploy/conf/upgrade_preserve.py:14-21` lists `hh/deploy/site/js/ext/deploy/site/ts/...` (Foxhouse
  layout).
- `tsconfig.json` (checked in) includes `ext/deploy/site/ts`, lists `hh/` twice, and leaves out `accounting/`.  It is
  regenerated by `hh_git/tsconfig.py`, so this only matters if someone runs `tsc` by hand.

**Stale cache-cleanup paths** (these only clean the deployed copy's cache)
- `hh_page/page_class_registry.py:271,281` (`hh/page/cache`)
- `help/help_query.py:293,302` (`hh/help/cache`)

**Stale comments**
- `maintenance/deploy/apps/worker.py:125`
- `accounting/deploy/maintenance/migration_worker_disabled.py:131`
- `accounting/deploy/maint/config_labels.py:13`

## 4. The snapshot commit `6137e897` (Jan 21–28 work)

400 files changed (+9,385 / −5,231) compared with `e3a6a719`: 228 renames, 73 new files, 29 deletions and 70 edits.

| Part | What it did | State |
|---|---|---|
| Folder moves | `hh/page` split into `hh_page`, `hh_image`, `hh_file` and `hh_video`.  `hh/{file,image,video}` and top-level `audio/`, `video/` became `hh_*`.  `hh/help` became `help`.  `hh/{ask,task,step,work,work_docket}` became `work`.  `hh/mcp_*` became top-level modules.  `hh/deploy/flask` became `hh_flask/deploy/apps`.  `hh/deploy/{maint,maintenance}` became `maintenance/`. | **Finished.**  All imports were updated, including 33 accounting files (one-line path edits). |
| Database tooling hookified | Deleted `hh/deploy/db/*` (17 scripts, the monolithic `init.sql`, `init_cache.sql` and `clean*.sql`).  Added 6 orchestrators and 6 `*_hooks.py` in `hh/deploy`, shared helpers (`db_config.py`, `db_helpers.py`, `db_user_helpers.py`, `db_import_export_helpers.py`), and per-module `db_hooks.py`, `db_user_hooks.py` and SQL in the 5 page and media modules. | **Half done.**  The pattern works for those 5 modules, but other modules' schemas, `maintenance_jobs`, and the old `check_db` command (deleted, no replacement) are missing. |
| Empty module scaffolds | `help`, `hh_page`, `hh_subpage`, `mcp_action_request` manifests, plus empty `schema.sql` and `example_data.sql` in 7 modules. | **Started.**  Placeholders only. |
| `tools.py` per media module | MCP tool definitions moved next to their actions. | Finished. |
| Maintenance task registry | New `hh/gateway/registry/maintenance_tasks.py` (`@register_maintenance_task`), used in 3 places. | **Half done.**  It sits next to the older `register_maintenance_tool` system instead of replacing it, and its one use in `page_cache_refresh.py` is the import crash. |
| Docs | New `context/deploy_hooks.md`, plus edits to `context/mcp.md`, `patterns.md`, `render.md` and `README/15`. | Partial (section 6). |
| `users/`, `self_doc/` edits | Import path updates. | Finished. |

Nothing in the snapshot looks abandoned.  The pieces still missing are the ones that make the hook pattern apply
to every module.

## 5. Accounting and moving Foxhouse over

**The code is the same.**  I diffed 31 Python, TS and config files from `henhouse MISC\foxhouse\ext` against
`accounting/`.  Every difference is mechanical:

- import paths (`ext.` → `accounting.`, `hh.page.` → `hh_page.`, `hh.deploy.maint.job_queue` →
  `maintenance.job_queue`)
- the `trace_out = lambda arg=None: arg` convention
- per-type `mcp_utils.py` replaced by `tools.py`
- `mcpTool` → `apiTool` in the TS page classes

`currency_math.py`, `config_labels.py`, `upgrade_preserve.py` and `migration_worker_disabled.py` are
byte-identical.  There's no accounting logic in Foxhouse that `accounting/` lacks, and none the other way.

**Accounting has no tables of its own.**  Both Foxhouse's `schema_ext.sql` and `accounting/deploy/db/schema.sql` are
the empty template.  Accounting data lives in the core `pages` table (page `class` plus `metadata` JSON) and in media
tables.  So the data move only needs the core tables to match.  The new per-module `init.sql` files define the
same page, link, media and cache tables as the old monolithic one, minus the agent tables and
`maintenance_jobs`.

**Migration path, roughly:**
1. Fix gaps 1–4 above, so a fresh install creates every table and the maintenance daemon works.
2. On the server, export Foxhouse's databases with Foxhouse's own `export_db`.  Do a fresh install of current
   Henhouse as a new project, say `foxhouse2`, with `accounting` taken off the module blacklist.  Then `init_db`
   and `import_db`.  An in-place `upgrade` can't work, because it only copies `hh/`.
3. Check that page classes registered under `accounting.*` load the same `class` values that Foxhouse stored.  The
   `register_page_class` names are the same.  The Python import paths changed, so check that nothing stores
   module paths in the DB.
4. Carry Foxhouse's `ext/deploy/conf` edits (site links, whitelists, `migration_config.py`) into the new
   project's `ext/deploy/conf`.  The legacy migration tools (`accounting/deploy/maint/*`) still need a
   `legacy_db_connection` config.
5. Switch nginx over once the Flask and maintenance daemons are running on the new install.

Size: steps 2–5 are about one session on the server with Lee present, once step 1 is done.

## 6. Docs to rewrite

Counts are lines that point at old locations (`hh/page`, `hh/deploy/db`, `hh/deploy/maint`, `ext/<accounting>`,
`schema_ext.sql`, monolithic `init.sql`).

| File | Hits | Notes |
|---|---|---|
| `context/page.md` | 34 | Every file path is under `hh/page`. |
| `README/10-daemons.md` | 11 | Flask and maintenance paths under `hh/deploy`. |
| `context/patterns.md` | 8 | |
| `context/mcp.md` | 7 | |
| `README/08-deployment.md` | 5 | |
| `README/15-ext-folder-customizations.md` | 5 | Still teaches `ext/` as the place for project code and `schema_ext.sql` (no longer read). |
| `README/07-database-setup.md` | 4 | Describes `hh/deploy/db/init.sql`. |
| `CLAUDE.md` | 3 | Key Files table lists `hh/page/page.py`, `hh/deploy/flask/app.py` and `hh/deploy/db/init.sql`.  Architecture Quick Reference still says "Two-Folder Pattern: hh/ + ext/". |
| `context/deploy_hooks.md` | 3 | The newest doc; references the old db path in its migration notes. |
| `context/overview.md`, `type_script.md`, `text_processor.md`, `ext/README.md`, `accounting/README.md` | 2 each | |
| `README/12-security-considerations.md` | 1 | |
| `README/16-upgrading-framework.md` | (behaviour) | Describes `upgrade` copying `hh/`, which doesn't cover modules. |
| `README/05-installation.md` | (behaviour) | Doesn't mention module blacklisting or that accounting is off by default. |

`context/modules.md` and `context/deploy_hooks.md` describe the new design and are the right base for the rewrite.

## 7. Recommended order

Each chunk fits in one session.  Sizes are rough.

1. **Small, ~1 hr: get the code healthy.**
   - Remove the bad decorator in `page_cache_refresh.py:133`.
   - Switch the maintenance, download and dependency scanners to `get_module_paths()`.
   - Fix the stale whitelist, cache-cleanup and manifest-name strings.
   - Add the two mypy annotations.
   - Check: the import sweep reaches 567/567 and the maintenance scan finds 22 tools.
2. **Medium, ~2–3 hrs: finish database hookification.**
   - Add one generic core `init_db` phase that runs each active module's `deploy/db/schema.sql` (and
     `example_data.sql` when asked), matching the old behaviour.  The same for `clean_db`.
   - Give `maintenance` its own `deploy/db/init.sql` with `maintenance_jobs`.
   - Convert `history`'s `deploy_before_schema` and `deploy_after_schema` into `init_db_*` hooks.
   - Decide one SQL file convention.
3. **Small, ~1 hr: hook naming gaps.**
   - Call `install_50_tier_env`, or rename it to share `install_50_user_env`.
   - Move `tier_config` and `should_ignore_context_path` behind hooks.
   - Add a daemon start-on-boot phase (systemd units).
4. **Medium, ~2–3 hrs: make `upgrade` module-aware.**  Copy each module folder that isn't `ext/`, and keep the
   preserve list working.  Update `README/16`.
5. **Medium, ~2 hrs: docs pass.**  Rewrite `context/page.md`, `README/07`, `08`, `10`, `15`, and the
   `CLAUDE.md` Key Files and Architecture sections.  Refresh the checked-in `tsconfig.json`.
6. **Large, optional, ~1–2 sessions: bare-metal layering.**
   - Remove `hh_page` and `hh_image` imports from `hh/gateway` and `hh/tp`, using hooks or the media registry.
   - Move `hh/tp` into a module.
   - Break the `hh_page` ↔ media import cycle.
   - Move the media viewer TS into the media modules.
7. **With Lee on the server: move Foxhouse onto the new layout** (section 5, steps 2–5).

Chunks 1–3 are what Foxhouse needs.  Chunk 6 can wait.

## 8. Questions for Lee

1. Should `accounting` stay blacklisted by default in core `ext/deploy/conf/module_blacklist.py`, with Foxhouse's
   own `ext/` turning it on?  Or should it be on by default now that it's the main use?
2. For the Foxhouse move, is a fresh install plus `export_db`/`import_db` acceptable, or do you want `upgrade`
   to migrate an install in place?
3. Are the dropped agent, watercooler, chunk and keyword tables from an abandoned agent system?  Nothing in the
   code uses them any more.
4. `install_50_tier_env` has never been called, even before the snapshot.  Did tier user environments get set up
   some other way on the live box, or is this a bug Foxhouse also has?
5. Should `register_maintenance_task` (new) replace `register_maintenance_tool` (old), or do both stay?

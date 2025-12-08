# File Parity Plan

Goal: Add file feature parity with images (copy/move/delete/sort/upload + visibility later), including UI menu, MCP/app actions, and TS handlers/overlays. No code changes yet—this is the plan.

## Scope
- Parity items: copy_files_app, move_files_app, delete_files_app, sort_files_app, upload_files_app; group name `files` in app actions menu. Later: set_file_visibility, edit description.
- Use existing `upload_files` action; mirror image UX (batch upload, then per-file processing, debug overlays).
- Sorting: drag-and-drop table-based sorter (ranks), separate from image tile sorter.
- Copy/Move/Delete semantics: mirror images (rank-specific per UI; parser legacy “all ranks if rank omitted” acceptable).
- Soft delete when no usages remain (already in PageFilesMixin).

## Backend (Python) work
1) MCP/App actions
- Add MCP tool wrappers for: `upload_files`, `copy_files`, `move_files`, `remove_file`, `set_file_rank` (sort), maybe `delete_files` (alias to remove multiple ranks) if desired.
- Whitelist tiers same as images (read all; write/admin/root; app actions tiers 7/8). Group: `files`. Labels: Copy, Move, Delete, Sort, Upload.
- Expose app actions via MCP whitelist so `available_actions` includes `files` group.

2) Actions (if missing)
- Implement MCP-callable actions (and parsers) invoking PageFilesMixin:
  - copy_files (target_page, file_ids[], optional target_rank)
  - move_files (target_page, file_instances with source_page/source_rank, optional target_rank)
  - remove_file (page_id, file_id, rank)
  - set_file_rank (page_id, file_id, target_rank)
  - upload_files (already exists; confirm wired to response + cache refresh)
- Ensure `show_page` response includes `files` data (already rendered) and flags cache refresh.

3) Upload endpoint
- Reuse `/upload-file` Flask endpoint; allow `type` param (`image` | `file` | future). Default `file`. Image path keeps current behavior; file path uses `store_uploaded_file`. Ensure response shape matches UploadHandler expectations.

## Frontend (TS) work
1) Menu wiring
- In `app.ts`, when `available_actions` includes group `files`, render menu group and attach handlers on PageData.

2) Handlers (new mixin `PageActionsFiles`)
- copy_files_app: Browser in `file` mode? (no file browser exists) → instead mirror image flow using Browser in `image`-like mode? If no file browser, use page browser + list selection UI? Decide: simplest MVP—reuse Browser in `image` mode but with file data? If not available, add file selection overlay with table and checkboxes. (Need decision: do we need a file browser? If yes, add a file-mode Browser.)
- move_files_app: similar to copy, grouping by source_page/source_rank.
- delete_files_app: select instances and call remove_file per instance.
- sort_files_app: new FileGroupSorter (table view), drag-and-drop, calls set_file_rank; mirrors ImageGroupSorter logic.
- upload_files_app: reuse generalized uploader (see below).

3) Upload handler generalization
- Extract shared uploader core (multi-file select, progress, batch upload then per-file processing, debug capture). Add `mode: 'image' | 'file'` (and optional future modes). Image mode: accept images/*, RPC `upload_images`. File mode: accept `*`, RPC `upload_files`, uses same `/upload-file` transport, no image-specific processing.
- Replace existing `Upload` handler call in PageData with `UploadImages` and new `UploadFiles` (or a param-driven `Upload` with mode).

4) File sorter
- New `file-group-sorter.ts`: table-based overlay, fetch via `get_page_section` with section `files` and view_type `table` (overlay=1). Drag-and-drop rows to reorder; call `set_file_rank` sequentially using same “largest distance first” algorithm; debug handling same as images.

5) Browser considerations
- Current Browser supports page/image modes. For MVP, file actions can operate on current page’s file group (no cross-page selection). Copy/move need source selection: if required, extend Browser with `mode: 'file'` returning `{ fileInstances: [{ file_id, source_page_id, source_rank }] }`. Otherwise, start with current page only and adjust later.

## Data/DB considerations
- files table already holds: file_name (original), file_path (stored unique), description (caption analog), mime_type, size_bytes, username, uploaded, last_modified, comments, visibility.
- Soft delete moves stored file to deleted folder (already in FileContentMixin).
- Description edit deferred.
- Length of description: keep as-is for now.

## Testing plan (later)
- Upload: multiple files, debug on/off, bad file path error.
- Copy/move: cross-page to verify ranks and cache refresh.
- Delete: removes instance; when usage=0, soft delete.
- Sort: reorders correctly; final verification; debug overlays.
- Menu presence: files group shows with five actions; handlers attach.

## Checklist
- [ ] Backend: MCP tools + app actions for files (upload/copy/move/remove/set_rank) with whitelist tiers and `files` group.
- [ ] Backend: ensure `upload_files` action/endpoint wiring and cache refresh; `/upload-file` type param defaults to `file`.
- [ ] Frontend: add `files` menu group rendering in `app.ts`.
- [ ] Frontend: add `PageActionsFiles` handlers (copy/move/delete/sort/upload) mirroring image flows.
- [ ] Frontend: generalize uploader core with mode `image|file`; add file upload handler.
- [ ] Frontend: implement file group sorter (table view) calling `set_file_rank`.
- [ ] Optional: add file-mode browser (or confirm current-page-only MVP).
- [ ] Tests: upload, copy/move, delete, sort, menu presence, debug overlay behavior.

## Open questions (need decisions)
- Browser for files: Yes — need file-selection support. Likely extend Browser with a file mode, showing files when selecting files; generalize selection buffer so it can handle images or files.
- Upload mixing: Images remain image-only; generic file uploads can mix any filetypes (no type filtering beyond extension); images still require real images.
- UI labels/icons: Follow existing label/icon patterns; reuse where appropriate; add new entries in `_labels.py` (or equivalent) if needed for files group/actions.


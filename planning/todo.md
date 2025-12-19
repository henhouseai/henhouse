# Linkless Feature Implementation

## Overview
The linkless feature allows pages that would normally have auto-linked names to have their link disabled. This is a derived state (not stored in database) that can be toggled by users.

## Algorithm

### Derived State Calculation
Linkless is derived from the relationship between `name` and `link`:
- **linkless = False** (has link): When `name` exists AND `name == link`
- **linkless = True** (is linkless): When `name` exists but `name != link` (link is NULL)

### Behavior Rules
1. **Linkless can only be applied to pages where `auto_link_name()` returns `True`**
   - Cannot use linkless to enable links on pages that shouldn't have them
   - Linkless is only for disabling links on pages that would normally have them

2. **When making a page linkless (linkless = True)**:
   - If link currently exists, set `link = NULL`
   - Trigger maintenance task to update all text references:
     - Find all pages in `links` table where `resolution_id = this_page.id` and link is not purely numeric
     - Update those pages' text to replace link references with page ID references
     - Update `links` table entries to use page ID instead of link text
     - Reprocess and recache affected pages (background maintenance task)

3. **When making a page not linkless (linkless = False)**:
   - Verify `auto_link_name()` is `True` (error if False)
   - Verify current `name` is unique as a link (check `links` table)
   - If both pass, set `link = name`
   - If name is not unique, return error - user must change name first

## Code Changes Required

### 1. Python Action/Command (`hh/page/modify_linkless.py`)
Create a new action script with built-in parser (similar to `set_image_rank` pattern):
- **Action**: `modify_linkless` or `set_linkless`
- **Command**: `modify_linkless` or `set_linkless`
- **Arguments**: 
  - `id` or `page_id`: Page ID
  - `linkless`: Boolean (True/False) or string ("true"/"false")
- **Logic**:
  - Load page
  - Verify `auto_link_name()` is True (if trying to disable linkless)
  - If enabling linkless: Set link = NULL, trigger maintenance task
  - If disabling linkless: Verify name uniqueness, set link = name
- **Parser**: Simple success/error message output (no show_page)

### 2. Update `modify_name()` Logic
Already fixed to gate through `auto_link_name()` first, but ensure:
- When `auto_link_name()` is True and page is linkless (name != link), don't update link
- When `auto_link_name()` is True and page is not linkless (name == link), update link
- When `auto_link_name()` is False, never update link

### 3. Maintenance Task
Create maintenance task for linkless conversion:
- **Task type**: `page_linkless_conversion` or similar
- **Parameters**: `page_id`, `old_link` (text), `new_link` (page ID as string)
- **Process**:
  1. Query `links` table: `SELECT * FROM links WHERE resolution_id = page_id AND link != CAST(link AS UNSIGNED)`
  2. For each linking page:
     - Load page text
     - Replace link patterns: `[[link]]` → `[[page_id]]`, `{{link}}` → `{{page_id}}`, etc.
     - Update page text in database
     - Update `links` table: set `link = page_id` (as string)
     - Flag page for reprocessing and cache refresh
  3. Run in background via maintenance daemon (can affect many pages)

### 4. TypeScript Frontend
- **Action button**: Add "Linkless" option to page actions menu
- **Overlay**: Similar to delete page overlay (confirmation checkbox + confirm/cancel buttons)
- **MCP call**: Call `modify_linkless` action with page_id and linkless boolean
- **UI state**: Show current linkless state (derived from name == link check)
- **Location**: Add to page actions menu in TypeScript page manager

### 5. Helper Method: `is_linkless()`
Add method to `Page` class:
```python
def is_linkless(self) -> bool:
    """Return True if page is linkless (name exists but name != link)."""
    return (self.name is not None and len(self.name) > 0) and (self.name != self.link)
```

## Implementation Order

1. ✅ Fix `modify_name()` to gate through `auto_link_name()` (already done)
2. Add `is_linkless()` helper method to `Page` class
3. Create `modify_linkless` action/command with parser
4. Create maintenance task for linkless conversion
5. Add TypeScript UI for linkless toggle
6. Test with home page (example of linkless page)

## Notes

- Linkless is a derived state, not stored in database
- The state is determined by whether `name == link` when name exists
- Maintenance task must run in background (can affect many pages)
- Only pages with `auto_link_name() == True` can be made linkless
- When making linkless, all text references must be updated to use page ID instead of link text

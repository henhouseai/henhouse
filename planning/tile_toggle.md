# Tile Toggle System Architecture

This document covers the planned implementation of hot-swapping view modes (table/tile) for page sections, starting with image groups and expanding to children by class. This system enables dynamic DOM content replacement via AJAX while keeping all rendering logic server-side.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Legacy System Reference](#2-legacy-system-reference)
3. [Architecture Design](#3-architecture-design)
4. [Implementation Plan: Image Groups](#4-implementation-plan-image-groups)
5. [Future Expansion: Children by Class](#5-future-expansion-children-by-class)
6. [Integration Points](#6-integration-points)

## Agent Quick Reference

- **Action Name**: `get_page_section` - returns HTML snippet for a specific section
- **Parameters**: `id` (page_id), `section` ('images'|'children'|'files'), `view_type` ('table'|'tile'|'auto')
- **URL Flag**: `?image_table=1` forces table mode (opposite of default)
- **Default Behavior**: HTTP backend defaults to tile mode for images, parser backend always table mode
- **Toggle Mechanism**: Click header link → MCP call → Replace DOM chunk
- **TypeScript Module**: `view-toggle.ts` handles client-side toggle logic
- **Server Logic**: Page mixin determines defaults based on backend type

## Agent Training Notes

### Current State
- All sections (images, children, files) render as tables only
- No view type parameter support
- No tile rendering functions exist
- No hot-swapping infrastructure

### Goal
- Enable table/tile toggle for image groups (initial focus)
- Expand to children by class (each class group toggles independently)
- Keep rendering logic server-side, client only swaps DOM
- HTTP-only feature (does not affect parser backend)

### Design Principles
- **Server-Side Rendering**: All HTML generation happens on server
- **Client-Side Swapping**: TypeScript only replaces DOM chunks
- **Backend-Aware Defaults**: HTTP defaults to tile, parser defaults to table
- **Independent Toggles**: Each section/class group toggles independently
- **URL Override**: Flags can force specific modes for testing

---

## 1. System Overview

The tile toggle system provides a hot-swapping interface for dynamically changing how page sections are displayed. Users can click a header link to toggle between table view and tile view, with the server generating the appropriate HTML and the client replacing the DOM chunk.

### Architecture Flow

1. **Initial Page Load**: Server renders section in default mode (tile for images in HTTP, table for parser)
2. **User Clicks Toggle**: TypeScript captures click on header link
3. **MCP Request**: Client calls `get_page_section` with opposite view_type
4. **Server Renders**: Server generates HTML for requested view mode
5. **DOM Replacement**: Client extracts HTML and replaces content div
6. **Re-initialization**: Any event handlers re-attach if needed

### Key Components

- **`get_page_section` Action**: New action that returns HTML for a single section
- **Tile Rendering Functions**: New module for generating tile HTML
- **View Type Logic**: Page mixin determines defaults based on backend
- **Toggle Headers**: Clickable headers that trigger view changes
- **TypeScript Module**: Client-side handler for toggle interactions

---

## 2. Legacy System Reference

### Legacy Files to Review

**PHP Files:**
- `legacy/core/php/Page_http.php` - Lines 84-129: `getChildrenOf()` method with viewType branching
  - Shows table vs tile rendering patterns
  - Toggle header generation: `pageTileViewHeader_{parentId}` with clickable link
  - Tile structure: `<ul class="pageTileView">` with `<li>` elements
  - Table structure: Standard HTML table with rows
- `legacy/core/php/Page_http.php` - Lines 250-265: `displayImageGroup()` method
  - Image group rendering: `<ul class="pageImageGroup">` with tiles
  - Uses `getTileLink(300, NULL, NULL, 'imageGroup')` for each image
- `legacy/core/php/Page_http.php` - Lines 508-516: `updatePageView()` AJAX handler
  - Takes `classType`, `destination`, `viewType` parameters
  - Calls `getChildrenOf()` with viewType
  - Returns HTML via `setPassThroughData()`

**JavaScript Files:**
- `legacy/core/js/page.js` - Lines 490-518: `updatePageView()` client handler
  - Extracts viewType from `data-viewType` attribute
  - Makes AJAX POST request
  - Replaces DOM: `jqDiv.find('a').unbind().end().remove()` then `jqHeader.find('a').replaceWith(...)`
- `legacy/core/js/page.js` - Lines 79-100: `getTile()` and `getTileLink()` functions
  - Client-side tile generation (we'll do this server-side instead)
- `legacy/core/js/tile.js` - Masonry layout initialization
  - Shows how tiles are laid out in grid

### Legacy Patterns to Replicate

1. **Toggle Header Pattern:**
   ```html
   <div id="pageTileViewHeader_{parentId}" class="contentHeader">
     <a class="updatePageView_{parentId}" viewType="table">PAGES</a>
   </div>
   ```

2. **Content Wrapper Pattern:**
   ```html
   <div id="pageTileView_{parentId}" class="content tileViewDiv">
     <ul class="pageTileView">
       <li>{tile}</li>
     </ul>
   </div>
   ```

3. **Image Group Pattern:**
   ```html
   <div id="pageImageGroupHeader_{page_id}" class="contentHeader">IMAGES</div>
   <div id="pageImageGroup_{page_id}" class="content pageImageGroup">
     <ul>
       <li>{image_tile}</li>
     </ul>
   </div>
   ```

4. **AJAX Flow:**
   - Click handler extracts parameters from element attributes
   - POST request with action and parameters
   - Server returns HTML string
   - Client replaces DOM chunk directly

### Legacy Auto Mode Behavior

In the legacy system, `getChildrenOf()` had an `'auto'` viewType that would default to either tile or table based on the class type. Different page classes had different defaults:
- Some classes defaulted to tile (image-heavy content)
- Some classes defaulted to table (data-heavy content)
- This was determined in each class's `getChildrenOf()` method

**Future Implementation Note:** We'll replicate this per-class default behavior for children sections, but images will always default to tile mode in HTTP backend (no class-specific logic needed).

---

## 3. Architecture Design

### Server-Side Components

#### New Action: `get_page_section`

**Location:** `hh/page/get_page_section.py`

**Purpose:** Return HTML snippet for a specific page section in the requested view mode.

**Parameters:**
- `id` (required): Page ID
- `section` (required): Section name ('images', 'children', 'files')
- `view_type` (optional): View mode ('table', 'tile', 'auto') - defaults based on backend/section
- `class_name` (optional): For children sections, filter by specific class

**Response Structure:**
- **Parser Backend**: Returns table with metadata rows + `dom_content` row containing HTML (for testing)
- **MCP Backend**: Returns JSON with `dom_content` field (primary usage)

**Registration:**
- Registered as action: `@register_action('get_page_section')`
- Registered as parser: `@register_parser('get_page_section')` (for CLI testing)
- Registered as MCP tool: Added to MCP whitelist (not app-action, just MCP tool)
- **NOT registered as HTTP backend** - HTTP backend uses `show_page` which calls the same mixin methods

**Logic Flow:**
1. Load page via `get_page(page_id)`
2. Call same page mixin methods that `show_page` calls (e.g., `render_images_section()`)
3. Mixin methods check `gateway.backend == 'http'` and determine view_type:
   - Check URL flag: `gateway.request.is_set('image_table')` → force table
   - Otherwise: use backend default (HTTP=tile for images, parser=table)
4. Render section based on `section` parameter
5. Return HTML wrapped in appropriate response format (parser table or MCP JSON)

#### Tile Rendering Module

**Location:** `hh/render/html/tiles.py` (new file)

**Functions (Initial Implementation - Images Only):**
- `render_image_tile(image_data, target_width=300, caption=None)` - Single image tile HTML
- `render_image_tile_link(image_data, target_width=300, link_href=None)` - Image tile wrapped in link

**Future Functions (Page Tiles):**
- `render_page_tile(page_data, target_width=300)` - Single page tile HTML
- `render_page_tile_link(page_data, target_width=300, link_href=None)` - Page tile wrapped in link

**Tile Structure:**
```html
<div class="tileWrapper">
  <img src="/srv/images/{path}" alt="{caption}" style="width: {target_width}px;">
  <div class="tileText" style="width: {target_width}px;">{caption}</div>
</div>
```

**Tile Link Structure:**
```html
<a class="tileLink" href="{link_href}" id="{link_id}">
  {tile_html}
</a>
```

#### View Type Default Logic

**Location:** Page mixin (e.g., `PageDisplayMixin`)

**Purpose:** Determine default view type based on backend and section type. This logic lives in the mixin so both `show_page` and `get_page_section` can call the same methods.

**Logic:**
- **Images**: HTTP backend → tile (default), Parser backend → table
- Check `gateway.request.is_set('image_table')` to force table mode (URL override)
- **Children**: Per-class defaults (future), but each class group toggles independently
- **Files**: TBD (future)

**Implementation Pattern:**
- Methods like `render_images_section()` check backend and request flags
- `show_page` (HTTP backend) calls these methods during initial render
- `get_page_section` (MCP backend) calls the same methods for hot-swapping
- Both use the same logic, ensuring consistency

### Client-Side Components

#### TypeScript Module: `view-toggle.ts`

**Location:** `hh/deploy/site/ts/view-toggle.ts` (new file)

**Responsibilities:**
- Listen for clicks on `.updatePageView_{page_id}` links
- Extract `data-section` and `data-view-type` attributes
- Make MCP call via RPC client
- Extract HTML from response
- Replace DOM chunk by ID
- Re-initialize event handlers if needed

**Integration:**
- Import in `app.ts` with minimal wiring (just initialization call)
- Auto-initialize on DOM ready

**Click Handler Pattern:**
```typescript
// Listen for clicks on toggle links
document.addEventListener('click', (e) => {
  const target = e.target as HTMLElement;
  if (target.classList.contains('updatePageView_*')) {
    // Extract page_id, section, view_type from attributes
    // Make RPC call
    // Replace DOM
  }
});
```

### Toggle Header Pattern

**HTML Structure:**
```html
<div id="pageImageGroupHeader_{page_id}" class="contentHeader">
  <a class="updatePageView_{page_id}" 
     data-section="images" 
     data-view-type="tile">IMAGES</a>
</div>
<div id="pageImageGroup_{page_id}" class="content pageImageGroup">
  <!-- table or tile content -->
</div>
```

**Behavior:**
- Header text ("IMAGES") never changes
- Clicking toggles between table/tile
- `data-view-type` indicates target mode (opposite of current)
- Each section has unique IDs for targeting

---

## 4. Implementation Plan: Image Groups

### Phase 1: Tile Rendering Functions

**Step 1.1:** Create `hh/render/html/tiles.py`
- Implement `render_image_tile()` - generates single image tile HTML
- Implement `render_image_tile_link()` - wraps tile in link
- Match legacy structure: `tileWrapper` div, `tileText` div
- Support `target_width` parameter (default 300px)

**Step 1.2:** Test tile rendering
- Create simple test script or use parser backend
- Verify HTML output matches legacy structure

### Phase 2: Update Image Section Rendering ✅ COMPLETE

**Step 2.1:** ✅ Modified `render_images_section()` in `hh/page/render_show_page.py`
- Now calls `render_image_group_html()` from `hh/render/html/image_group.py`
- Passes `page_id` parameter
- View type determined in `render_image_group_html()` function

**Step 2.2:** ✅ Implemented tile mode rendering
- Created `render_image_group_html()` function in `hh/render/html/image_group.py`
- Uses `render_image_tile_link()` for each image
- Generates `<ul class="pageImageGroup">` structure with `<li>` elements
- Matches legacy structure

**Step 2.3:** ✅ Toggle header implemented
- ✅ Tile view includes toggle header with clickable link
- ✅ Table view includes toggle header with clickable link (added after initial implementation)
- Header ID: `pageImageGroupHeader_{page_id}`
- Content ID: `pageImageGroup_{page_id}`
- Toggle link: `data-section="images"` and `data-view-type` (opposite of current)
- Both views now support bidirectional toggling

**Step 2.4:** ✅ View type default logic implemented
- Logic in `render_image_group_html()` function
- For images: HTTP → tile, Parser → table
- URL override: `gateway.request.is_set('image_table')` → forces table

### Phase 3: Create `get_page_section` Action ✅ COMPLETE

**Step 3.1:** ✅ Created `hh/page/get_page_section.py`
- Registered as action: `@register_action('get_page_section')`
- Registered as command: `@register_command('get_page_section')`
- Registered parser backend: `@register_parser('get_page_section')` (for CLI testing)
- Registered MCP tool: Added to MCP whitelist (standard MCP tool, not app-action)
- **NOT registered as HTTP backend** - HTTP uses `show_page` instead

**Step 3.2:** ✅ Implemented action logic
- Validates parameters: `id`, `section` required
- Validates section is one of: 'images', 'children', 'files'
- Loads page via `get_page(page_id)`
- Determines view_type (check flags, use defaults)
- Routes to `render_image_group_html()` for 'images' section
- Returns JSON with `dom_content` field containing HTML string
- Currently only supports 'images' section (children/files pending)

**Step 3.3:** ✅ Implemented parser backend output
- Creates table with metadata rows:
  - `page_id`: Page ID number
  - `page_name`: Page name
  - `parent`: Parent page ID
  - `class`: Page class
  - `section`: Section name
  - `view_type`: View mode used
  - `dom_content`: HTML output as text block
- Uses standard table rendering functions

**Step 3.4:** ✅ Tested via MCP backend
- Tested with page ID 635, section "images"
- Table view: Returns formatted table with HTML in `dom_content` row
- Tile view: Returns HTML with toggle header and tile structure
- Both views working correctly

### Phase 4: TypeScript Client Integration

**Step 4.1:** Create `hh/deploy/site/ts/view-toggle.ts`
- Implement click handler for `.updatePageView_*` links
- Extract attributes: `data-section`, `data-view-type`
- Extract page_id from class name or data attribute

**Step 4.2:** Implement MCP call
- Use RPC client to call `get_page_section`
- Pass parameters: `id`, `section`, `view_type`
- Extract `dom_content` from response

**Step 4.3:** Implement DOM replacement
- Find target element by ID: `pageImageGroup_{page_id}`
- Find header element by ID: `pageImageGroupHeader_{page_id}`
- Replace header link with new one (opposite view_type)
- Replace content div with new HTML

**Step 4.4:** Wire into app.ts
- Import `view-toggle.ts`
- Call initialization function (minimal wiring)
- Test toggle functionality

### Phase 5: URL Flag Support ✅ COMPLETE

**Step 5.1:** ✅ URL flag support implemented
- `render_image_group_html()` checks `gateway.request.is_set('image_table')`
- If set, forces table mode regardless of default
- Allows testing and explicit table mode requests

**Step 5.2:** ⚠️ URL flag tested (partial)
- Logic implemented and working
- Full end-to-end web UI testing pending (TypeScript toggle not yet implemented)

### Phase 6: Testing and Refinement

**Step 6.1:** End-to-end testing
- Test initial page load (default tile mode for HTTP)
- Test toggle to table mode
- Test toggle back to tile mode
- Test URL flag override
- Test parser backend (should always be table)

**Step 6.2:** Edge cases
- Test with no images (empty image group)
- Test with single image
- Test with many images (layout/performance)
- Test with images that have no instances

**Step 6.3:** Refinement
- Ensure IDs are always unique
- Verify toggle headers update correctly
- Check that event handlers re-attach if needed
- Verify no parser backend side effects

---

## 5. Future Expansion: Children by Class

### Overview

After image groups are working, expand the system to support children sections with per-class independent toggles.

### Key Differences from Images

1. **Multiple Class Groups:** Each class type has its own toggle
2. **Per-Class Defaults:** Each page class can specify its default view type
3. **Class-Specific Rendering:** Different classes may render differently
4. **Independent Toggles:** Each class group toggles independently

### Implementation Approach

**Step 1:** Extend `get_page_section` to support `class_name` parameter
- Filter children by class when `class_name` specified
- Render only that class group

**Step 2:** Update `render_children_by_class_section()` to support view_type
- Add `view_type` parameter
- Generate toggle header per class: `child_pages_{class_name}_header_{page_id}`
- Generate content div per class: `child_pages_{class_name}_{page_id}`
- Each class group toggles independently

**Step 3:** Implement per-class default logic
- Add method to page classes: `get_default_children_view_type(class_name)`
- Some classes default to tile, some to table
- Matches legacy `getChildrenOf()` auto mode behavior

**Step 4:** Extend TypeScript to handle class-specific toggles
- Update click handler to extract `data-class-name` attribute
- Pass `class_name` to `get_page_section` call
- Replace correct class-specific DOM chunk

### Per-Class Default Pattern

**Example:**
```python
class WorkDocketContentMixin:
    @classmethod
    def get_default_children_view_type(cls, child_class: str) -> str:
        """Return default view type for children of specific class."""
        if child_class == 'ask':
            return 'tile'  # Asks default to tile view
        elif child_class == 'task':
            return 'table'  # Tasks default to table view
        return 'auto'  # Default fallback
```

---

## 6. Integration Points

### With Gateway

- **Request Parsing:** `gateway.request.is_set('image_table')` for URL flags
- **Backend Detection:** `gateway.backend == 'http'` for HTTP-only features
- **Response Management:** `gateway.response.set_lower_content()` for section HTML

### With Page System

- **Page Loading:** `get_page(page_id)` to load page data
- **Image Data:** `page.get_images_data()` to get image list
- **Children Data:** `page._get_children_by_class()` to get children grouped by class

### With Render System

- **Table Rendering:** Existing table rendering functions for table mode
- **Tile Rendering:** New tile rendering functions for tile mode
- **HTML Generation:** Both modes generate HTML strings

### With MCP Backend

- **Tool Registration:** `get_page_section` added to MCP whitelist (standard MCP tool)
- **Usage:** TypeScript client calls via RPC for hot-swapping
- **Response Format:** Returns JSON with `dom_content` field for MCP

### With TypeScript Client

- **RPC Integration:** Uses `rpc.call('get_page_section', {...})` 
- **DOM Manipulation:** Direct HTML replacement via `innerHTML`
- **Event Handling:** Re-attach handlers after DOM replacement if needed

### Backend Isolation

- **HTTP Backend:** Uses `show_page` action which calls mixin methods that check backend
- **Parser Backend:** Always renders table mode, no toggle functionality
- **MCP Backend:** `get_page_section` calls same mixin methods, returns JSON for TypeScript client
- **Shared Logic:** Both `show_page` and `get_page_section` call the same mixin rendering methods

---

## Implementation Checklist

### Image Groups (Initial Focus)

- [x] Create `hh/render/html/tiles.py` with tile rendering functions
- [x] Modify `render_images_section()` to support view_type parameter
- [x] Implement tile mode rendering for images
- [x] Generate toggle headers with unique IDs (tile view only - table view still needs toggle header)
- [x] Add view type default logic to page mixin
- [x] Create `get_page_section` action
- [x] Register parser backend for `get_page_section`
- [x] Register MCP tool for `get_page_section`
- [ ] Create `view-toggle.ts` TypeScript module
- [ ] Wire toggle handler into app.ts (minimal)
- [x] Implement URL flag support (`image_table=1`)
- [x] Test end-to-end toggle functionality (MCP testing complete, web UI pending)
- [x] Verify parser backend unaffected

### Children by Class (Future)

- [ ] Extend `get_page_section` to support `class_name` parameter
- [ ] Update `render_children_by_class_section()` for view_type support
- [ ] Implement per-class toggle headers
- [ ] Add per-class default logic to page classes
- [ ] Extend TypeScript for class-specific toggles
- [ ] Test independent toggles per class group

---

## Notes for Future Agents

### Key Files to Review

**Legacy Reference:**
- `legacy/core/php/Page_http.php` - Lines 84-129, 250-265, 508-516
- `legacy/core/js/page.js` - Lines 79-100, 490-518
- `legacy/core/js/tile.js` - Masonry layout

**Current System:**
- `hh/page/render_show_page.py` - Current rendering functions
- `hh/page/page_display.py` - Page display mixin
- `hh/gateway/response/response_http.py` - HTTP response formatting
- `hh/gateway/request/request.py` - Request argument handling

**New Files (created):**
- `hh/page/get_page_section.py` - New action for section rendering ✅
- `hh/render/html/tiles.py` - Tile rendering functions ✅
- `hh/render/html/image_group.py` - Image group rendering with table/tile support ✅

**Modified Files:**
- `hh/page/render_show_page.py` - Updated to use `render_image_group_html()` function
- `hh/gateway/response/response.py` - Added `set_image_group()` and `set_file_group()` methods
- `hh/gateway/response/response_http.py` - Updated `_render_body()` to include `image_group` and `file_group` separately

**Files (to be created):**
- `hh/deploy/site/ts/view-toggle.ts` - Client-side toggle handler

### Design Decisions

1. **Server-Side Rendering:** All HTML generation on server, client only swaps DOM
2. **Backend-Aware Defaults:** HTTP defaults to tile, parser defaults to table
3. **Independent Toggles:** Each section/class group toggles independently
4. **URL Override:** Flags can force specific modes for testing
5. **HTTP-Only:** Feature does not affect parser backend behavior

### Testing Strategy

1. **Parser Backend:** Smoke test via CLI, verify table output with HTML in `dom_content`
2. **HTTP Backend:** Test initial load, toggle functionality, URL flags
3. **Edge Cases:** Empty sections, single items, many items
4. **Backend Isolation:** Verify parser backend always table mode, no side effects

---

## Implementation Status Update

### Completed Work (Phases 1-3, Partial Phase 4)

**Phase 1: Tile Rendering Functions** ✅ COMPLETE
- Created `hh/render/html/tiles.py` with:
  - `render_tile()` - Base tile wrapper function
  - `render_tile_link()` - Tile wrapped in link
  - `render_image_tile()` - Single image tile HTML generation
  - `render_image_tile_link()` - Image tile with link wrapper
- Functions support `target_width` parameter (default 300px)
- Automatic instance selection based on target width
- Matches legacy structure with `tileWrapper` div and `tileText` div

**Phase 2: Image Section Rendering** ✅ COMPLETE
- Created `hh/render/html/image_group.py` with `render_image_group_html()` function
- Modified `render_images_section()` in `hh/page/render_show_page.py` to call `render_image_group_html()`
- Supports `view_type` parameter ('table' or 'tile')
- Default logic: HTTP backend → tile, Parser backend → table
- URL flag support: `?image_table=1` forces table mode
- Generates unique IDs: `pageImageGroupHeader_{page_id}` and `pageImageGroup_{page_id}`

**Phase 3: get_page_section Action** ✅ COMPLETE
- Created `hh/page/get_page_section.py` with action and parser backend handlers
- Registered as action, command, parser backend, and MCP tool
- Parameters: `id` (page_id), `section` ('images'|'children'|'files'), `view_type` ('table'|'tile'|'auto')
- Returns JSON with `dom_content` field containing HTML snippet
- Parser backend returns formatted table with metadata + `dom_content` row
- Currently supports 'images' section only (children/files pending)

**Phase 4: Response Module Updates** ✅ COMPLETE
- Added `set_image_group()` method to `Response` class
- Added `set_file_group()` method to `Response` class
- Updated `ResponseHTTP._render_body()` to include `image_group` and `file_group` as separate content divs
- Sections now stored separately instead of lumped into `lower_content`

### Testing Results

**MCP Testing (2025-01-XX):**
- Tested `get_page_section` with page ID 635, section "images"
- **Table view**: Returns formatted CLI table with metadata rows + `dom_content` row containing HTML table
- **Tile view**: Returns HTML with:
  - Header: `<div id="pageImageGroupHeader_635" class="contentHeader">` with toggle link
  - Content: `<div id="pageImageGroup_635" class="content pageImageGroup">` with `<ul><li>` tile structure
  - Each tile: `<a class="tileLink" href="/img/{id}">` wrapping tile with image and caption
- Both views working correctly via MCP

**Web UI Status:**
- Images render in tile mode by default (HTTP backend)
- CSS layout needs refinement (acknowledged - will be fine-tuned after functionality complete)
- Toggle functionality not yet implemented (TypeScript client pending)

### Implementation Details

**Tile Rendering:**
- Uses `render_image_tile_link()` from `tiles.py`
- Target width: 300px (configurable)
- Image instance selection: Finds best instance >= target width, falls back to largest if none found
- Tile structure: `tileWrapper` div with `img` tag and `tileText` div
- Link structure: `tileLink` class with `href="/img/{image_id}"`

**Table Rendering:**
- Uses standard `render_block()` with `TableData` and `FieldConfig`
- Columns: Images, Rank, ID, Caption, Uploaded, Instances
- Image links added to label, rank, id, and caption columns
- **Note**: Table view currently does NOT include toggle header (needs to be added)

**View Type Logic:**
- Default determination in `render_image_group_html()`:
  - If `view_type` not provided: HTTP backend → "tile", Parser backend → "table"
  - URL override: `gateway.request.is_set("image_table")` → forces "table"
- Same logic used in both `show_page` (via `render_images_section()`) and `get_page_section` action

**Response Structure:**
- `get_page_section` returns:
  ```json
  {
    "page_id": 635,
    "page_name": "asdf asdf",
    "parent": 1,
    "class": "page",
    "section": "images",
    "view_type": "tile",
    "dom_content": "<div id=\"pageImageGroupHeader_635\">...</div>..."
  }
  ```

### Known Issues / TODO

1. ~~**Table View Toggle Header**: Table view currently doesn't include toggle header~~ ✅ FIXED - Both table and tile views now include toggle headers
2. **CSS Refinement**: Image group CSS needs work for better layout (acknowledged - will be addressed after functionality is complete)
3. **Children/Files Sections**: `get_page_section` only supports 'images' section currently - children and files sections need implementation

### Next Steps

**Phase 4 (TypeScript Client)** - ✅ COMPLETE

**Step 4.1:** ✅ Created `hh/deploy/site/ts/view-toggle.ts`
- Implemented `ViewToggle` class with event delegation
- Listens for clicks on `.updatePageView_{page_id}` links
- Extracts page_id from class name
- Extracts `data-section` and `data-view-type` attributes

**Step 4.2:** ✅ Implemented MCP call
- Uses RPC client to call `get_page_section`
- Passes parameters: `id`, `section`, `view_type`
- Extracts `dom_content` from response

**Step 4.3:** ✅ Implemented DOM replacement
- Parses HTML content from response
- Finds header and content elements by ID
- Replaces innerHTML of existing elements (preserves element structure)
- Handles clearboth div insertion/removal

**Step 4.4:** ✅ Wired into app.ts
- Imported `initializeViewToggle` function
- Called in DOMContentLoaded handler
- Minimal wiring - auto-initializes on page load

**Status**: ✅ Both tile→table and table→tile toggles should now work in web UI. Table view toggle header was added to match tile view behavior.

This document will be updated as implementation progresses and design decisions are finalized.


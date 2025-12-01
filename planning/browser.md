# Browser System Architecture

This document covers the planned implementation of the browser overlay system for selecting pages and images within modal dialogs. The browser enables hierarchical navigation through the page structure to select target pages for operations like move/copy, or to select images from pages. This system reuses existing `show_page` and `get_page_section` infrastructure with overlay-specific modifications.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Legacy System Reference](#2-legacy-system-reference)
3. [Architecture Design](#3-architecture-design)
4. [Implementation Plan: Overlay Flag System](#4-implementation-plan-overlay-flag-system)
5. [Implementation Plan: TypeScript Browser Component](#5-implementation-plan-typescript-browser-component)
6. [Implementation Plan: Use Cases](#6-implementation-plan-use-cases)
7. [Integration Points](#7-integration-points)

## Agent Quick Reference

- **Core Concept**: Browser is a z-stacked overlay that shows full page HTML content with link interception
- **MCP Tools Used**: `get_browser` (for HTML rendering), `get_page_section` (for view toggling with overlay flag)
- **get_browser Action**: New action that always returns HTML (like `get_page_section`), always uses overlay mode
- **Shared Helpers**: Rendering functions extracted to `render_helpers.py` for reuse by `show_page` HTTP backend and `get_browser`
- **Selection Modes**: `page` (single page ID) or `image` (multiple image IDs as array)
- **Link Interception**: Client-side JavaScript modifies all links after rendering to intercept navigation
- **Image Buffer**: Top section of browser shows selected images when in image selection mode
- **Navigation**: All page links retarget browser to new page; image links add/remove from selection buffer

## Agent Training Notes

### Current State
- Overlay system fully functional with z-stacking support
- `show_page` action returns lightweight JSON when backend is MCP (for agent responses)
- `get_page_section` action returns HTML and supports view toggling (table/tile)
- Tile rendering system complete (images and pages)
- View toggle system working for hot-swapping views
- `render_show_page.py` is monolithic (all rendering functions in one file)
- No browser component exists yet

### Goal
- Enable page selection for move/copy operations
- Enable image selection from pages (future: file selection)
- Create dedicated `get_browser` action that always returns HTML
- Refactor `render_show_page.py` by extracting shared helpers
- Support view toggling within browser overlay
- Maintain z-stack compatibility with existing overlays

### Design Principles
- **Dedicated get_browser Action**: New action always returns HTML (like `get_page_section`)
- **Shared Helper Module**: Extract rendering functions to `render_helpers.py` for reuse
- **Overlay Mode**: `get_browser` always uses overlay classes/ID prefixes automatically
- **Client-Side Link Interception**: Modify links after rendering to intercept navigation
- **Consistent UI**: Browser shows same content as regular page view, just in overlay
- **View Toggle Support**: Header links work to switch between table/tile views
- **Image Selection Buffer**: Visual queue at top of browser for selected images

---

## 1. System Overview

The browser system provides a hierarchical navigation interface within modal overlays, allowing users to select pages or images for operations like move, copy, or image selection. The browser displays the full page content (path, badges, text, children, images) using the same rendering system as the main page view, but with overlay-specific modifications.

### Architecture Flow

1. **Browser Initialization**: User triggers browser from form (e.g., "Pick Target Location" button)
2. **HTML Rendering**: Browser calls `get_browser` MCP tool with page ID to get HTML
3. **Content Injection**: Browser injects HTML into overlay content area (HTML already has overlay classes/IDs)
4. **Link Interception**: Browser scans DOM and replaces all links with JavaScript handlers
5. **User Navigation**: User clicks page links → browser retargets; clicks image links → adds to buffer
6. **View Toggling**: User clicks header toggle links → browser calls `get_page_section` with `overlay=1` flag
7. **Selection**: User clicks Submit → browser returns selected page ID or image IDs array

### Key Components

- **get_browser Action**: New action that always returns HTML with overlay classes/IDs
- **Shared Rendering Helpers**: Extracted from `render_show_page.py` for reuse
- **Browser Component**: TypeScript class managing browser state and navigation
- **Link Interception**: Client-side JavaScript that modifies links after rendering
- **Image Selection Buffer**: Visual queue showing selected images (image mode only)
- **View Toggle Integration**: Existing `view-toggle.ts` system with overlay flag support

---

## 2. Legacy System Reference

### Legacy Files to Review

**PHP Files:**
- `legacy/core/php/Page_http.php` - Lines 441-474: `getBrowserXML()` method
  - Shows XML structure: target, path, contents, images
  - Uses `getPathArray()` for breadcrumb navigation
  - Groups children by class using `getBrowserSortString()`
  - Returns images ordered by `imageRank`
- `legacy/core/php/Page_http.php` - Lines 75-83: `getBrowserSortString()` static method
  - SQL query for getting children of a page
  - Filters by visibility and class
  - Orders by name
- `legacy/core/php/Page_http.php` - Lines 430-439: `getBrowserPutInsideCheck()` method
  - Validation for move/copy operations
  - Checks if page class is allowed inside target page
- `legacy/core/php/Image.php` - Lines 162-176: `getBrowserXML()` method for images
  - Simpler structure (no contents/images sections)
  - Shows parent page path
  - Target is the image itself

**JavaScript Files:**
- `legacy/core/js/overlay.js` - Lines 29-69: `showOverlayWindow()` method
  - Browser initialization with `browserId` parameter
  - Calls `getBrowserXML` action via AJAX
  - Shows loading animation during fetch
- `legacy/core/js/overlay.js` - Lines 89-176: `refreshOverlayWindow()` method
  - Parses XML response and renders browser sections
  - Target section: shows current page/image with tile
  - Path section: breadcrumb navigation with clickable links
  - Contents section: child pages as tiles
  - Images section: images as tiles
  - Handles both page and image targets
- `legacy/core/js/overlay.js` - Lines 177-185: `retargetOverlayWindow()` method
  - Handles clicks on browser links (path, contents, images)
  - Extracts ID from link and calls `getBrowserXML` again
  - Updates browser display with new page
- `legacy/core/js/page.js` - Lines 180-189: `copyPage()` method
  - Shows browser with `showOverlayWindow('Put Copy Where?', content, parentId)`
  - Hides images section via `browserRefreshCallback`
  - Submit callback returns `{'id': pageId, 'action': 'copyPage', 'value': browserId}`
- `legacy/core/js/page.js` - Lines 191-203: `movePage()` method
  - Similar to copyPage but different action
  - Updates page parent after success
- `legacy/core/js/page.js` - Lines 230-264: `copyImages()` method
  - Shows browser with image selection mode
  - Hides target section via `browserRefreshCallback`
  - Image click callback adds/removes images from buffer
  - Buffer displayed at top of browser
  - Submit button text updates with image count

### Legacy Patterns to Replicate

1. **Browser Layout Pattern:**
   - Header with Cancel/Submit buttons
   - Image selection buffer (if image mode)
   - Target section (current page/image)
   - Path section (breadcrumb)
   - Contents section (child pages)
   - Images section (page images)

2. **Navigation Pattern:**
   - Clicking page links → retargets browser to that page
   - Clicking image links → adds/removes from selection buffer
   - Path links navigate up the hierarchy

3. **Image Selection Pattern:**
   - Images shown as tiles with click handlers
   - Selected images appear in buffer at top
   - Buffer shows count: "Submit X images"
   - Clicking buffer image removes it from selection

4. **Submit Pattern:**
   - Page mode: Submit sends current `browserId` (page ID)
   - Image mode: Submit sends comma-separated list of image IDs

### Legacy Differences to Note

- **XML vs JSON**: Legacy used XML transport, new system uses JSON via MCP
- **jQuery vs Fetch**: Legacy used jQuery AJAX, new system uses fetch API
- **Separate Action**: Legacy had `getBrowserXML` action, new system reuses `show_page`
- **No View Toggling**: Legacy browser only showed tiles, new system supports table/tile toggle

---

## 3. Architecture Design

### Server-Side Components

#### New Action: get_browser

**Location**: `hh/page/get_browser.py` (new file)

**Purpose**: Return HTML content for browser overlay, always outputting HTML even when called via MCP (similar to `get_page_section`)

**Design Decision**: Create dedicated `get_browser` action instead of modifying `show_page` because:
- `show_page` returns lightweight JSON when backend is MCP (for agent responses)
- Browser needs full HTML rendering
- Opportunity to refactor monolithic `render_show_page.py` into shared helper modules
- `get_browser` can share helper functions with `show_page` rendering logic

**Parameters**:
- `id` (required): Page ID to display in browser
- `overlay` (optional): Flag to add overlay-specific classes/ID prefixes (default: true for browser)

**Response Structure**:
```json
{
  "page_id": 635,
  "page_name": "Page Name",
  "dom_content": "<div class='overlay'>...full page HTML...</div>"
}
```

**Implementation Approach**:
1. Extract shared rendering functions from `render_show_page.py` into helper module
2. `get_browser` calls same rendering functions as `show_page` HTTP backend
3. Always forces `backend='http'` in `render_block()` calls (like `get_page_section` does)
4. Collects all HTML sections into single `dom_content` string
5. Adds overlay flag automatically (always true for browser)

**Shared Helper Module**:
- Create `hh/page/render_helpers.py` (new file)
- Move rendering functions from `render_show_page.py`:
  - `render_path_section()`
  - `render_badge_headers_section()`
  - `render_text_section()`
  - `render_children_by_class_section()`
  - `render_images_section()`
  - `render_files_section()`
- Both `show_page` HTTP backend and `get_browser` import from helpers
- Reduces duplication and makes `render_show_page.py` less monolithic

#### Overlay Flag System

**Location**: `hh/page/get_browser.py`, `hh/page/get_page_section.py`, `hh/render/render.py`

**Purpose**: Automatically add overlay-specific classes and ID prefixes when rendering for browser overlay

**Implementation**:
- `get_browser` always uses overlay mode (adds `overlay` class and `overlay_` ID prefix)
- `get_page_section` checks `gateway.request.is_set('overlay')` flag
- If true:
  - Add `'overlay'` to `additional_classes` parameter in all `render_block()` calls
  - Prepend `'overlay_'` to all `wrapper_id` values
  - This ensures unique IDs and allows CSS targeting

**Code Pattern**:
```python
# In get_browser.py (always overlay mode)
additional_classes = ['overlay']
wrapper_id_prefix = 'overlay_'

# In get_page_section.py (check flag)
overlay_mode = gateway.request.is_set('overlay')
additional_classes = ['overlay'] if overlay_mode else []
wrapper_id_prefix = 'overlay_' if overlay_mode else ''

# When calling render_block()
dom_content = render_block(
    table_data,
    field_config,
    additional_classes=additional_classes,
    wrapper_id=f"{wrapper_id_prefix}{original_id}",
    backend='http'  # Force HTTP rendering for HTML output
)
```

**Files to Create/Modify**:
- `hh/page/get_browser.py` - New action that returns HTML (always overlay mode)
- `hh/page/render_helpers.py` - New helper module with shared rendering functions
- `hh/page/render_show_page.py` - Refactor to use helper module
- `hh/page/get_page_section.py` - Add overlay flag checks in `render_block()` calls
- `hh/render/render.py` - Ensure `render_block()` accepts and uses `additional_classes` parameter
- `hh/render/html/html_table.py` - Ensure wrapper IDs use the provided prefix

#### get_page_section Action Integration

**Location**: `hh/page/get_page_section.py`

**Current Behavior**: Returns HTML snippet for a specific section (images, children) with view type support

**Modification**: Add overlay flag detection and pass to rendering functions

**Key Functions to Modify**:
- Section rendering logic - Add overlay class/ID prefix
- `render_block()` calls - Pass overlay flag and `backend='http'` (already does this)
- Check `gateway.request.is_set('overlay')` to determine if overlay mode

### Client-Side Components

#### Browser Component

**Location**: `hh/deploy/site/ts/browser.ts` (new file)

**Class**: `Browser`

**State Management**:
- `currentPageId: number` - Currently displayed page ID
- `selectedImageIds: number[]` - Selected image IDs (image mode only)
- `mode: 'page' | 'image'` - Selection mode
- `overlay: Overlay | null` - Reference to overlay instance

**Key Methods**:

**`show(options: BrowserOptions): Promise<BrowserResult>`**
- Creates overlay window with browser content
- Calls `get_browser` MCP tool with page ID to get HTML
- Injects HTML into overlay content area
- Sets up link interception
- Returns promise that resolves when user submits

**`retargetBrowser(pageId: number): Promise<void>`**
- Updates `currentPageId`
- Calls `get_browser` MCP tool with new page ID
- Re-renders browser content
- Re-applies link interception

**`handleLinkClick(event: Event): void`**
- Intercepts clicks on page links
- Extracts page ID from href (e.g., `/123` → `123`)
- Calls `retargetBrowser(pageId)`
- Prevents default navigation

**`handleImageClick(event: Event, imageId: number): void`**
- Intercepts clicks on image links (image mode only)
- Toggles image in `selectedImageIds` array
- Updates image buffer display
- Updates submit button text

**`renderImageBuffer(): string`**
- Generates HTML for selected images buffer
- Shows images as tiles with remove buttons
- Only rendered in image mode

**`interceptLinks(container: HTMLElement): void`**
- Scans container for all `<a>` tags
- Identifies page links vs image links
- Replaces hrefs with onclick handlers
- Handles view toggle links (already work via `get_page_section`)

#### View Toggle Integration

**Location**: `hh/deploy/site/ts/view-toggle.ts`

**Modification**: Pass `overlay=1` flag to `get_page_section` calls when in browser overlay

**Implementation**:
- Check if click originated from browser overlay (check for `overlay_` ID prefix)
- If yes, add `overlay: 1` to MCP call parameters
- Existing toggle logic works unchanged

### Browser Layout Structure

```
┌─────────────────────────────────────────┐
│ [Cancel] [Submit]                       │ ← OverlayHeader
├─────────────────────────────────────────┤
│ [Image Buffer Section]                  │ ← Only if mode === 'image'
│   - Selected images as tiles            │
│   - Click to remove                     │
│   - Shows count: "Submit X images"      │
├─────────────────────────────────────────┤
│ [Path Section]                          │ ← From show_page
│   - Breadcrumb navigation               │
│   - Clickable links (intercepted)       │
├─────────────────────────────────────────┤
│ [Badge Headers]                         │ ← From show_page
├─────────────────────────────────────────┤
│ [Text Content]                          │ ← From show_page
│   - Links intercepted for navigation    │
├─────────────────────────────────────────┤
│ [Children by Class Sections]            │ ← From show_page
│   - Toggle headers work                 │
│   - Table/tile views                    │
│   - Page links intercepted              │
├─────────────────────────────────────────┤
│ [Images Section]                        │ ← From show_page
│   - Toggle header works                 │
│   - Table/tile views                    │
│   - Image links intercepted (if image mode) │
└─────────────────────────────────────────┘
```

---

## 4. Implementation Plan: Overlay Flag System

### Phase 1: Extract Shared Rendering Helpers

**Step 1.1:** Create `hh/page/render_helpers.py`
- New file for shared rendering functions
- Will be imported by both `render_show_page.py` and `get_browser.py`

**Step 1.2:** Move rendering functions from `render_show_page.py` to `render_helpers.py`
- `render_path_section()`
- `render_badge_headers_section()`
- `render_text_section()`
- `render_children_by_class_section()`
- `render_images_section()`
- `render_files_section()`
- `render_upper_content_section()`
- `render_lower_content_section()`
- `render_extra_data_section()`

**Step 1.3:** Update function signatures to accept overlay parameters
- Add `overlay_mode: bool = False` parameter to all functions
- Add `wrapper_id_prefix: str = ''` parameter
- Add `additional_classes: List[str] = []` parameter
- Functions use these to modify rendering behavior

**Step 1.4:** Update `render_show_page.py` to use helpers
- Import functions from `render_helpers.py`
- Pass overlay parameters (default to False for HTTP backend)
- Maintain existing behavior

**Step 1.5:** Test HTTP backend still works
- Verify `show_page` HTTP rendering unchanged
- All sections render correctly

### Phase 2: Modify render_block() to Support Additional Classes

**Step 2.1:** Review `hh/render/render.py` - `render_block()` function
- Check current signature for `additional_classes` parameter
- Ensure it's passed through to `render_html_table()` and `render_tile_group()`

**Step 2.2:** Modify `render_block()` if needed
- Add `additional_classes: List[str] = []` parameter
- Pass to `render_html_table()` and `render_tile_group()`

**Step 2.3:** Review `hh/render/render_http.py` - `render_html_table()` function
- Ensure it accepts and uses `additional_classes` parameter
- Add to wrapper div classes

**Step 2.4:** Review `hh/render/html/tile_group.py` - `TileGroup.render()` method
- Ensure it accepts and uses `additional_classes` parameter
- Add to wrapper div classes

### Phase 3: Create get_browser Action

**Step 3.1:** Create `hh/page/get_browser.py`
- New action file following pattern of `get_page_section.py`
- Register as action, command, parser backend, MCP tool

**Step 3.2:** Implement `get_browser` action logic
- Load page via `get_page(page_id)`
- Call `page.show_page()` to get JSON data (full payload, not lightweight)
- Import rendering functions from `render_helpers.py`
- Call all rendering functions with `overlay_mode=True`, `wrapper_id_prefix='overlay_'`, `additional_classes=['overlay']`
- Force `backend='http'` in all `render_block()` calls (like `get_page_section` does)
- Collect all HTML sections from `gateway.response`:
  - Path HTML from `gateway.response.path`
  - Badge headers HTML
  - Page text HTML from `gateway.response.page_text`
  - Upper content HTML
  - Lower content HTML
  - Child pages HTML from `gateway.response.child_pages`
  - Image group HTML from `gateway.response.image_group`
  - File group HTML from `gateway.response.file_group`
- Combine into single `dom_content` string
- Return JSON with `dom_content` field

**Step 3.3:** Implement parser backend handler
- Similar to `get_page_section` parser backend
- Returns formatted table with metadata + `dom_content` row

**Step 3.4:** Test via parser backend
- Call `get_browser` with page ID
- Verify HTML is returned in `dom_content` field
- Verify IDs are prefixed with `overlay_`
- Verify `overlay` class is added to wrapper divs

### Phase 4: Add Overlay Flag Detection to get_page_section

**Step 3.1:** Modify `hh/page/get_page_section.py`
- Add overlay flag detection at top of `get_page_section_action()`:
  ```python
  overlay_mode = gateway.request.is_set('overlay')
  wrapper_id_prefix = 'overlay_' if overlay_mode else ''
  additional_classes = ['overlay'] if overlay_mode else []
  ```

**Step 3.2:** Modify section rendering logic
- Pass `wrapper_id_prefix` and `additional_classes` to `render_block()` calls
- Update wrapper IDs with prefix

**Step 3.3:** Test via parser backend
- Call `get_page_section` with `overlay=1` flag
- Verify IDs are prefixed with `overlay_`
- Verify `overlay` class is added

### Phase 5: Update View Toggle System

**Step 4.1:** Modify `hh/deploy/site/ts/view-toggle.ts`
- In `handleToggleClick()`, check if toggle link is in browser overlay
- Detection: Check if link's parent container has ID starting with `overlay_`
- If yes, add `overlay: 1` to MCP call parameters

**Step 4.2:** Test view toggling in browser
- Create test browser overlay
- Click toggle links
- Verify table/tile switching works
- Verify IDs remain prefixed with `overlay_`

---

## 5. Implementation Plan: TypeScript Browser Component

### Phase 6: Create Browser Class Structure

**Step 1.1:** Create `hh/deploy/site/ts/browser.ts`
- Define `BrowserOptions` interface
- Define `BrowserResult` interface
- Create `Browser` class with state properties

**Step 1.2:** Implement basic `show()` method
- Accept `BrowserOptions` parameter
- Create overlay using `OverlayManager.getInstance().show()`
- Set up basic structure (header, content area)
- Return promise that resolves on submit

**Step 1.3:** Implement `loadPage()` helper method
- Calls `rpc.call('get_browser', { id: pageId })`
- Returns HTML content from `dom_content` field

**Step 1.4:** Test basic browser display
- Create test button that shows browser
- Call `get_browser` MCP tool
- Verify HTML content displays in overlay
- Verify overlay z-stacks correctly

### Phase 7: Implement Link Interception

**Step 2.1:** Implement `interceptLinks()` method
- Scans container for all `<a>` tags
- Identifies link types:
  - Page links: href like `/123` or `/page/123`
  - Image links: href like `/img/123` or class contains `tileLink` with image ID
  - View toggle links: class contains `updatePageView_`
  - Text links: links in page text content

**Step 2.2:** Implement page link interception
- Extract page ID from href
- Replace href with `#` or `javascript:void(0)`
- Add `onclick` handler that calls `retargetBrowser(pageId)`
- Prevent default navigation

**Step 2.3:** Implement image link interception (image mode only)
- Extract image ID from href or data attribute
- Replace href with `#` or `javascript:void(0)`
- Add `onclick` handler that calls `handleImageClick(imageId)`
- Toggle visual state (selected/unselected)

**Step 2.4:** Handle view toggle links
- View toggle links already work via `view-toggle.ts`
- Just need to ensure `overlay=1` flag is passed (handled in Phase 4 of previous section)

**Step 2.5:** Handle text content links
- Scan page text content for links
- Extract page IDs from links
- Replace with onclick handlers
- Same pattern as tile/table links

**Step 2.6:** Test link interception
- Click page links → verify browser retargets
- Click image links (image mode) → verify images add to buffer
- Click view toggle links → verify view switches

### Phase 8: Implement retargetBrowser() Method

**Step 3.1:** Implement `retargetBrowser()` method
- Update `currentPageId` state
- Show loading state in overlay
- Call `rpc.call('get_browser', { id: pageId })` to get new HTML
- Extract `dom_content` from response
- Replace browser content area HTML
- Re-apply link interception
- Hide loading state

**Step 3.2:** Handle navigation errors
- If page not found, show error message
- Keep current page displayed
- Allow user to navigate elsewhere

**Step 3.3:** Test navigation
- Click various page links
- Verify browser updates correctly
- Verify path breadcrumb updates
- Verify all sections update

### Phase 9: Implement Image Selection Buffer

**Step 4.1:** Implement `renderImageBuffer()` method
- Generates HTML for selected images
- Shows images as tiles (100px width for buffer)
- Each tile has remove button/click handler
- Shows count: "X images selected"

**Step 4.2:** Implement `handleImageClick()` method
- Toggles image ID in `selectedImageIds` array
- Updates image buffer HTML
- Updates submit button text
- Toggles visual state of image in main content

**Step 4.3:** Add buffer to overlay layout
- Insert buffer HTML after header, before main content
- Only show if `mode === 'image'`
- Update on image selection/deselection

**Step 4.4:** Update submit button text
- Page mode: "Submit" or "Select Page"
- Image mode: "Submit X images" (updates dynamically)

**Step 4.5:** Test image selection
- Click images in image mode → verify they add to buffer
- Click buffer images → verify they remove
- Verify submit button text updates
- Verify visual state toggles

### Phase 10: Implement Submit Handling

**Step 5.1:** Implement submit callback
- Page mode: Return `{ pageId: currentPageId }`
- Image mode: Return `{ imageIds: selectedImageIds }`
- Close overlay
- Resolve promise with result

**Step 5.2:** Handle validation
- Page mode: Always valid (current page is selection)
- Image mode: Require at least one image selected
- Show error if validation fails

**Step 5.3:** Test submit
- Submit in page mode → verify callback receives page ID
- Submit in image mode → verify callback receives image IDs array
- Test validation errors

---

## 6. Implementation Plan: Use Cases

### Phase 11: Move Page Handler

**Step 1.1:** Modify `hh/deploy/site/ts/page-data.ts`
- Add `move_page()` handler method
- Follow pattern of existing handlers (e.g., `delete_page()`)

**Step 1.2:** Implement move page flow
- Show browser overlay with page mode
- Initial page ID: current page's parent (or current page if no parent)
- Hide images section (not needed for page selection)
- On submit: Call `move_page` MCP tool with `source_page` and `target_page`
- On success: Redirect to moved page (or refresh current page)

**Step 1.3:** Test move page
- Click "Move Page" action
- Navigate to target page in browser
- Submit → verify page moves
- Verify redirect works

### Phase 12: Copy Page Handler

**Step 2.1:** Modify `hh/deploy/site/ts/page-data.ts`
- Add `copy_page()` handler method

**Step 2.2:** Implement copy page flow
- Show browser overlay with page mode
- Initial page ID: current page's parent (or current page if no parent)
- Hide images section
- On submit: Call `copy_page` MCP tool with `source_page` and `target_page`
- On success: Redirect to new copied page

**Step 2.3:** Test copy page
- Click "Copy Page" action
- Navigate to destination parent in browser
- Submit → verify page copies
- Verify redirect to new page works

### Phase 13: Copy Page Here Handler (Optional)

**Step 3.1:** Determine if needed
- Check if `copy_page_here` action exists or should be separate
- Alternative: `copy_page` could detect missing target and use current page

**Step 3.2:** If implementing separately
- Add `copy_page_here()` handler method
- Show browser overlay with page mode
- Initial page ID: current page (destination is current page)
- On submit: Call `copy_page` with `source_page` (from browser) and `target_page` (current page)
- On success: Redirect to new copied page

**Step 3.3:** Test copy page here
- Click "Copy Page Here" action
- Navigate to source page in browser
- Submit → verify page copies into current page
- Verify redirect works

---

## 7. Integration Points

### With Overlay System

- **Z-Stacking**: Browser uses `OverlayManager.getInstance().show()` which automatically handles z-index
- **Focus Management**: Overlay system handles focus trapping
- **Keyboard Shortcuts**: ESC closes browser, Enter submits (handled by overlay system)
- **Loading States**: Browser shows loading spinner during page loads

### With get_browser Action

- **HTML Rendering**: Browser calls `get_browser` MCP tool to get HTML
- **Always Overlay Mode**: `get_browser` always uses overlay-specific IDs/classes
- **Content Structure**: Receives same HTML structure as regular page view
- **Sections**: All sections (path, badges, text, children, images) are included
- **Shared Helpers**: Uses same rendering functions as `show_page` HTTP backend

### With get_page_section Action

- **View Toggling**: Browser uses `get_page_section` for table/tile switching
- **Overlay Flag**: Passes `overlay=1` to maintain ID prefixes
- **Section Updates**: Replaces section HTML when view toggles

### With View Toggle System

- **Automatic Detection**: `view-toggle.ts` detects browser overlay context
- **Flag Passing**: Automatically adds `overlay=1` to MCP calls
- **DOM Replacement**: Works seamlessly within browser overlay

### With MCP Backend

- **Tool Calls**: Browser makes MCP calls via `RPCClient`
- **Debug Options**: Browser respects debug options from overlay
- **Error Handling**: Uses standard RPC error handling

### With Page System

- **Page Navigation**: Uses `get_page()` from page registry (via MCP)
- **Page Data**: Receives full page data structure
- **Children/Images**: Uses existing children_by_class and images data

### With Tile System

- **Tile Rendering**: Reuses existing tile rendering functions
- **Image Tiles**: Uses `render_image_tile_link()` for images
- **Page Tiles**: Uses `render_page_tile_link()` for pages
- **Tile Sizing**: Uses standard 300px width (or configured default)

---

## Implementation Checklist

### Shared Rendering Helpers

- [ ] Create `hh/page/render_helpers.py` file
- [ ] Move rendering functions from `render_show_page.py` to helpers
- [ ] Update function signatures to accept overlay parameters
- [ ] Update `render_show_page.py` to import from helpers
- [ ] Test HTTP backend still works correctly

### render_block() Additional Classes Support

- [ ] Review and modify `render_block()` to support `additional_classes` parameter
- [ ] Modify `render_html_table()` to use `additional_classes`
- [ ] Modify `TileGroup.render()` to use `additional_classes`
- [ ] Test additional classes are applied correctly

### get_browser Action

- [ ] Create `hh/page/get_browser.py` action file
- [ ] Register as action, command, parser backend, MCP tool
- [ ] Implement action logic using shared helpers
- [ ] Always use overlay mode (overlay classes/ID prefixes)
- [ ] Force `backend='http'` in all `render_block()` calls
- [ ] Collect all HTML sections into `dom_content` string
- [ ] Implement parser backend handler
- [ ] Test via parser backend (verify HTML output)

### get_page_section Overlay Flag

- [ ] Add overlay flag detection to `get_page_section` action
- [ ] Modify `get_page_section` rendering to use overlay prefix/classes when flag set
- [ ] Update `view-toggle.ts` to pass `overlay=1` flag
- [ ] Test overlay flag system via parser backend

### TypeScript Browser Component

- [ ] Create `browser.ts` file with `Browser` class
- [ ] Implement `BrowserOptions` and `BrowserResult` interfaces
- [ ] Implement basic `show()` method
- [ ] Implement `loadPage()` helper method
- [ ] Implement `interceptLinks()` method
- [ ] Implement page link interception
- [ ] Implement image link interception
- [ ] Implement text content link interception
- [ ] Implement `retargetBrowser()` method
- [ ] Implement `renderImageBuffer()` method
- [ ] Implement `handleImageClick()` method
- [ ] Implement submit handling
- [ ] Test browser display and navigation
- [ ] Test link interception
- [ ] Test image selection buffer
- [ ] Test view toggling within browser

### Use Cases

- [ ] Implement `move_page()` handler in `page-data.ts`
- [ ] Test move page end-to-end
- [ ] Implement `copy_page()` handler in `page-data.ts`
- [ ] Test copy page end-to-end
- [ ] Implement `copy_page_here()` handler (if needed)
- [ ] Test copy page here end-to-end

---

## Notes for Future Agents

### Key Files to Review

**Legacy Reference:**
- `legacy/core/php/Page_http.php` - Lines 441-474, 75-83, 430-439
- `legacy/core/php/Image.php` - Lines 162-176
- `legacy/core/js/overlay.js` - Lines 29-69, 89-176, 177-185
- `legacy/core/js/page.js` - Lines 180-189, 191-203, 230-264

**Current System:**
- `hh/page/render_show_page.py` - Current page rendering functions
- `hh/page/get_page_section.py` - Section rendering for view toggling
- `hh/render/render.py` - `render_block()` function
- `hh/render/render_http.py` - HTML table rendering
- `hh/render/html/tile_group.py` - Tile group rendering
- `hh/deploy/site/ts/overlay-manager.ts` - Overlay system
- `hh/deploy/site/ts/overlay.ts` - Overlay component
- `hh/deploy/site/ts/view-toggle.ts` - View toggle system
- `hh/deploy/site/ts/page-data.ts` - Page data handlers

**New Files (to be created):**
- `hh/page/get_browser.py` - New action that returns HTML for browser
- `hh/page/render_helpers.py` - Shared rendering helper functions
- `hh/deploy/site/ts/browser.ts` - Browser component

**Modified Files:**
- `hh/page/render_show_page.py` - Refactor to use `render_helpers.py`
- `hh/page/get_page_section.py` - Add overlay flag support
- `hh/render/render.py` - Add `additional_classes` parameter support
- `hh/render/render_http.py` - Use `additional_classes` parameter
- `hh/render/html/tile_group.py` - Use `additional_classes` parameter
- `hh/deploy/site/ts/view-toggle.ts` - Pass overlay flag to MCP calls
- `hh/deploy/site/ts/page-data.ts` - Add move/copy page handlers

### Design Decisions

1. **Dedicated get_browser Action**: Create new action instead of modifying `show_page` because:
   - `show_page` returns lightweight JSON for MCP backend (for agent responses)
   - Browser needs full HTML rendering
   - Opportunity to refactor monolithic `render_show_page.py`
   - `get_browser` always returns HTML (like `get_page_section`)
2. **Shared Helper Module**: Extract rendering functions to `render_helpers.py`:
   - Both `show_page` HTTP backend and `get_browser` use same helpers
   - Reduces code duplication
   - Makes `render_show_page.py` less monolithic
3. **Overlay Flag System**: `get_browser` always uses overlay mode (adds classes/ID prefixes)
4. **Client-Side Link Interception**: Modify links after rendering to intercept navigation
5. **View Toggle Support**: Browser supports table/tile switching via existing system
6. **Image Selection Buffer**: Visual queue at top of browser for selected images
7. **Page-Only Navigation**: Browser only navigates to pages, images selected from page's image group
8. **Force HTTP Rendering**: `get_browser` always forces `backend='http'` in `render_block()` calls (like `get_page_section` does)

### Testing Strategy

1. **Parser Backend**: Test overlay flag system via CLI with `overlay=1` flag
2. **MCP Backend**: Test browser component via MCP calls
3. **Web UI**: Test full browser functionality in browser overlay
4. **Edge Cases**: Test with no children, no images, single page, many pages
5. **View Toggling**: Test table/tile switching within browser
6. **Link Interception**: Test all link types (page, image, text, toggle)

---

## Implementation Status

### Completed ✅

- [x] Extract rendering helper functions from `render_show_page.py` to `render_helpers.py`
- [x] Update `render_show_page.py` to use extracted helpers (removed duplicate functions)
- [x] Add overlay flag support to `get_page_section` action
- [x] Modify `render_block()` and HTML rendering to support `additional_classes` parameter
- [x] Create `get_browser` action with structured response (metadata + HTML sections)
- [x] Add MCP tool registration for `get_browser` (tiers 1-4)
- [x] Test `get_browser` via parser backend (CLI smoke tests)
- [x] Standardize HTML output formatting (id before class, proper line breaks)
- [x] Add overlay class to all wrapper divs (ImageGroup, PageGroup, HtmlTableBuilder)

### Pending ⏳

- [ ] Create Browser TypeScript class with mode support (page/image/file)
- [ ] Implement page mode in Browser (hide image groups, no buffer)
- [ ] Implement image mode in Browser (show buffer, handle image selection)
- [ ] Implement file mode in Browser (show buffer, handle file selection)
- [ ] Add link interception for browser navigation
- [ ] Integrate browser with move/copy page operations
- [ ] Test browser in web UI with overlay system

This document will be updated as implementation progresses and design decisions are finalized.


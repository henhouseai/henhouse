# Henhouse TypeScript System Architecture

This document covers the TypeScript/ES modules system that provides client-side interactivity for the Henhouse HTTP interface, including overlay management, page data handling, RPC integration, and form processing.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [TypeScript Compilation](#2-typescript-compilation)
3. [Core Overlay System](#3-core-overlay-system)
4. [PageData System](#4-pagedata-system)
5. [RPC Integration](#5-rpc-integration)
6. [Action Handlers](#6-action-handlers)
7. [Form Patterns](#7-form-patterns)
8. [Debug Integration](#8-debug-integration)
9. [Derived PageData Classes](#9-derived-pagedata-classes)
10. [File Upload](#10-file-upload)
11. [Best Practices](#11-best-practices)

## Agent Quick Reference

- **Overlay System**: `OverlayManager.getInstance().show()` - Singleton pattern for modal management (see `overlay-manager.ts`)
- **PageData Pattern**: Handlers live in PageData classes (one file per derived class)
- **Field Registration**: Use `getField('fieldName', 'form')` to auto-register editable fields (see `page-data.ts` - `getField()` method)
- **Field IDs**: Standardized as `#page-field-{fieldName}` (e.g., `#page-field-name`)
- **Content Structure**: Use array-based system: `content: Array<string | HTMLElement>`, `contentHeaders: Array<string>` (see `overlay.ts` - `OverlayOptions` interface)
- **Operation Processing**: UPDATE uses `processOperationsIncrementally()`, CREATE/DELETE use direct `rpc.call()` (see `page-data.ts` - `processOperationsIncrementally()` method)
- **Error Handling**: Return objects with `_showMessage`, errors stack as individual overlay content divs (see `overlay.ts` - `handleSubmit()` method)
- **Debug Options**: Always present but collapsed by default (see `overlay-debug-options.ts`)
- **Redirect Handling**: Use `_redirectAfterFade: 'parent' | 'self' | '/url' | null` (see `overlay.ts` - `handleRedirect()` method)

## Agent Training Notes

### Overlay System Usage
- Always use `OverlayManager.getInstance().show()` - never instantiate directly (see `overlay-manager.ts`)
- Set the overlay `mode`: `fixed` (default, 90% clamp + inner scroll), `pannable` (full-height flow, wheel/touch pans the window), `zoomable` (width-driven, height auto, pan/zoom gestures). Modes add classes `overlay-window-{mode}` and `{mode}`.
- Content should use array-based structure with headers for multiple sections (see `overlay-content.ts` - `render()` method)
- Debug options automatically available when submit button is shown (see `overlay.ts` - `mount()` method)
- Errors automatically stack as separate content sections (see `overlay.ts` - `handleSubmit()` method)

### PageData Handler Pattern
- All CRUD handlers live in PageData classes (base or derived) - see `page-data.ts` for base handlers
- Use `getField('fieldName', 'form')` to register fields for editing (see `page-data.ts` - `getField()` method)
- Use `getField('fieldName')` or `getField('fieldName', 'display')` for read-only display
- Handlers accept `rpc` as first parameter

### Form Field Management
- Fields auto-register when accessed with `context: 'form'` (see `page-data.ts` - `getField()` method)
- Field IDs must follow `#page-field-{fieldName}` pattern (see `page-manager.ts` - `registerField()` method)
- PageManager handles change detection and optimal MCP tool selection (see `page-manager.ts` - `selectOptimalMappings()` method)
- Use `processOperationsIncrementally()` for UPDATE operations with multiple fields (see `page-data.ts` - `processOperationsIncrementally()` method)

### RPC Integration
- Use `rpc.call(method, params, debugOptions?)` for MCP calls (see `rpc-client.ts` - `call()` method)
- Debug options automatically captured from overlay if not provided (see `rpc-client.ts` - `call()` method)
- Errors return `RPCError` with multiple error messages (see `rpc-client.ts` - `RPCError` class)
- Debug data automatically extracted and displayed in separate overlay (see `rpc-client.ts` - `extractMCPData()` method)

### Error Handling
- Return objects with `_showMessage` for success messages (see `overlay.ts` - `handleSubmit()` method)
- Throw errors for validation failures (will be caught and displayed)
- Multiple errors automatically stack as separate red content sections (see `overlay.ts` - `handleSubmit()` method)
- Use `_autoFade: true` for successful operations that should auto-close

---

## 1. System Overview

The TypeScript system provides client-side interactivity for the Henhouse HTTP interface, using ES modules architecture. The system integrates with the Python MCP backend through JSON-RPC 2.0 calls and provides an overlay system for user interactions.

### Architecture Flow

Python HTTP Backend renders HTML with seed data and action links → TypeScript App (`app.ts`) loads page data and attaches handlers → User interaction triggers overlay → Overlay system shows modal and captures form data → RPC Client (`rpc-client.ts`) makes MCP JSON-RPC call → Python Gateway executes MCP tool and returns JSON → TypeScript components update DOM and manage state

### Key Components

- **OverlayManager** (`overlay-manager.ts`): Singleton manager for all modal overlays
- **PageData/PageManager** (`page-data.ts`, `page-manager.ts`): Field management and form processing system
- **RPCClient** (`rpc-client.ts`): MCP JSON-RPC wrapper with debug integration
- **Action Handlers**: CRUD operation handlers in PageData classes
- **Debug System**: Integrated debug options and table rendering (`overlay-debug-options.ts`, `overlay-debug-table.ts`)

### File Structure

Core files in `hh/deploy/site/ts/`:
- `app.ts` - Main entry point, action handler registration
- `overlay-manager.ts` - OverlayManager singleton
- `overlay.ts` - Base Overlay component
- `overlay-backdrop.ts`, `overlay-window.ts`, `overlay-header.ts`, `overlay-content.ts` - Overlay subcomponents
- `overlay-debug-options.ts`, `overlay-debug-table.ts` - Debug UI components
- `rpc-client.ts` - MCP RPC client
- `page-manager.ts` - Field registry and form processing
- `page-data.ts` - Base PageData class
- `page-data-factory.ts` - Factory for derived classes
- Derived classes: `source-code-file-page-data.ts`, `mcp-request-page-data.ts`, `mcp-action-page-data.ts`, `work-page-data.ts`, `work-docket-page-data.ts`
- `browser.ts` - Browser component for hierarchical navigation and selection
- `image-group-sorter.ts` - Specialized browser for image sorting
- `view-toggle.ts` - View toggle system for table/tile switching
- `upload-handler.ts` - Image upload handler
- `seed.ts` - Seed data reader
- Action handlers: `page-actions-fields.ts`, `page-actions-pages.ts`, `page-actions-images.ts`
- `image-viewer.ts` - Zoomable image viewer (uses `mode: 'zoomable'`, width-only sizing, intrinsic dimensions set on images, caption links to `/img/{id}`)
- `audio-viewer.ts` - Audio playback viewer overlay
- `video-viewer.ts` - Video playback viewer overlay

**Potential refactors / future work**
- Extract a reusable sortable helper (for image/file group sorters) instead of duplicating logic in `image-group-sorter.ts` and the planned file-group sorter; overlay remains mode-based, helper would wire Sortable setup + rank commit loop.
- Consider optional overlay flags/hooks for sortable flows rather than hard-coding per overlay; today it's handled in the sorter modules.

---

## 2. TypeScript Compilation

The TypeScript compilation process uses a top-level `tsconfig.json` that compiles TypeScript files from both `hh/deploy/site/ts/` and `ext/deploy/site/ts/` folders, weaving them together into a single output directory.

### Compilation Process

**Configuration**: `tsconfig.json` at project root

The `tsconfig.json` file is located at the top level of the project directory and configures TypeScript compilation:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ES2020",
    "lib": ["ES2020", "DOM"],
    "outDir": "hh/deploy/site/js",
    "rootDir": ".",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "node"
  },
  "include": [
    "hh/deploy/site/ts/**/*",
    "ext/deploy/site/ts/**/*"
  ],
  "exclude": ["node_modules"]
}
```

**Compilation Command**: Run `tsc` from project root

TypeScript compilation is performed by running `tsc` from the top-level project directory:

```bash
cd /path/to/henhouse
tsc
```

This compiles all TypeScript files from both `hh/deploy/site/ts/` and `ext/deploy/site/ts/` into `hh/deploy/site/js/`, preserving directory structure.

**Output Structure**: Compiled JavaScript files mirror TypeScript source structure

- `hh/deploy/site/ts/**/*.ts` → `hh/deploy/site/js/hh/deploy/site/ts/**/*.js`
- `ext/deploy/site/ts/**/*.ts` → `hh/deploy/site/js/ext/deploy/site/ts/**/*.js`

### Page Class Registry Generation

During deployment, a `page-classes-registry.js` file is automatically generated that registers all page class PageData handlers based on a whitelist/blacklist system.

**Whitelist/Blacklist Pattern**: `whitelist - blacklist + ext_whitelist`

The system uses a three-step process to determine which page classes are registered:

1. **Base Whitelist**: `hh/deploy/conf/js_page_classes_whitelist.py`
   - Contains `JS_PAGE_CLASSES_WHITELIST` list of page class filenames
   - Files are discovered from `hh/deploy/site/js/page-classes/` folder

2. **Blacklist**: `ext/deploy/conf/js_page_classes_blacklist.py` (optional)
   - Contains `JS_PAGE_CLASSES_WHITELIST` list of filenames to remove from base whitelist
   - Items are subtracted from the base whitelist

3. **Extension Whitelist**: `ext/deploy/conf/js_page_classes_whitelist.py` (optional)
   - Contains `JS_PAGE_CLASSES_WHITELIST` list of additional filenames
   - Files are discovered from `ext/deploy/site/js/page-classes/` folder
   - Items are added to the final list (warnings if duplicates exist)

**Processing Order**: See `hh/deploy/deploy_utils.py` - `load_whitelist_with_extensions()`:
1. Load base whitelist from `hh/deploy/conf/js_page_classes_whitelist.py`
2. Load blacklist from `ext/deploy/conf/js_page_classes_blacklist.py` (if exists)
3. Subtract blacklist items from base
4. Load extension whitelist from `ext/deploy/conf/js_page_classes_whitelist.py` (if exists)
5. Add extension items to result (warn if duplicates)

**Registry Generation**: See `hh/deploy/srv/deploy.py` - page class registry generation:
- During `hen deploy`, the system scans for page class files matching the whitelist
- Files are searched in both `hh/deploy/site/js/page-classes/` and `ext/deploy/site/js/page-classes/`
- Registry file is generated at: `hh/deploy/site/js/hh/deploy/site/ts/page-classes-registry.js`
- Registry exports `PAGE_CLASS_REGISTRY` object mapping page class names to PageData constructors

**Page Class File Discovery**:
- Base whitelist files are searched in `hh/deploy/site/js/page-classes/` first
- If not found in `hh/`, searched in `ext/deploy/site/js/page-classes/`
- Files must exist as compiled `.js` files (from TypeScript compilation)
- Missing files are logged but don't cause errors

**Registry Format**: Generated registry file structure:
```typescript
// Auto-generated during deployment - do not edit manually

import { ask_page_data } from './page-classes/ask-page-data.js';
import { source_code_file_page_data } from '../../../../ext/deploy/site/ts/page-classes/source-code-file-page-data.js';
// ... more imports ...

export const PAGE_CLASS_REGISTRY = {
  'ask': ask_page_data,
  'source_code_file': source_code_file_page_data,
  // ... more entries ...
};
```

**File Naming Convention**: Page class files follow pattern `{page-class-name}-page-data.ts`
- Example: `ask-page-data.ts` → compiled to `ask-page-data.js`
- Registry key: `ask` (kebab-case converted to snake_case)
- Class name: `ask_page_data` (kebab-case converted to snake_case with `_page_data` suffix)

---

## 3. Core Overlay System

The overlay system provides modal dialogs for user interactions, using a component-based architecture.

### OverlayManager

**File**: `overlay-manager.ts`

Singleton manager for all overlay instances. Handles z-index stacking, focus management, keyboard shortcuts, and event routing.

**Key Methods**:
- `getInstance()`: Get singleton instance
- `show(options)`: Show new overlay, returns Overlay instance
- `close(overlay)`: Close specific overlay with fade
- `closeAll()`: Close all overlays
- `getTopOverlay()`: Get topmost overlay (highest z-index)
- `isActive()`: Check if any overlay is active

See `overlay-manager.ts` for the `OverlayOptions` interface definition.

### Overlay Component

**File**: `overlay.ts`

Base overlay component that handles lifecycle, rendering, and state management.

**Content Structure**: Array-based system with optional headers:
- `content: Array<string | HTMLElement>` - Array of content items
- `contentHeaders: Array<string>` - Optional headers for each content section (empty string = no header)

See `overlay.ts` - `OverlayOptions` interface for complete options structure.

**Modes**:
- `mode: 'fixed' | 'pannable' | 'zoomable'`
  - **fixed** (default): 90% max width/height, inner scroll if needed.
  - **pannable**: height flows; wheel/touch pans the whole overlay vertically; pinch on mobile fits width to 90–100% (no vertical zoom); uses classes `overlay-window-pannable`/`pannable`.
  - **zoomable**: width-driven sizing (height auto), no max-height; pan/zoom gestures with state-based axis locking; uses classes `overlay-window-zoomable`/`zoomable`.
  - Mode classes are added to the window element for CSS targeting.

**Zoomable specifics (image viewer)**:
- Width-only sizing: sets window width, lets height flow; single fit pass on init to hit viewport height within ~1px tolerance; no height/max-height set.
- Axis locking from overflow: no pan if no overflow; single-axis pan when only one axis overflows; both axes when both overflow.
- Gestures: wheel zoom; pinch zoom with max-scale clamp and baseline reset to avoid rubber-band; drag-to-pan; swipe navigation when scale=1.
- Touch handling: `touch-action: none` on window/backdrop; preventDefault on pinch paths; backdrop tap closes overlay on mobile.
- Intrinsic image dimensions set on `<img>` to avoid first-load mis-measurements; caption is a link to `/img/{id}`.
- See `hh/deploy/site/ts/image-viewer.ts` for implementation.

**State Management**: See `overlay.ts` - `OverlayState` interface:
- `isVisible`: Overlay visibility state
- `isLoading`: Loading state (hides submit button, shows spinner)
- `messages`: Array of messages `[{ type: 'success' | 'error', text: string }]` (preferred over single error/success)

**Submit Result Format**: See `overlay.ts` - `handleSubmit()` method for result object structure with `_showMessage`, `_autoFade`, `_redirectAfterFade`, `debug`, etc.

**Error Handling**: See `overlay.ts` - `handleSubmit()` method:
- Thrown errors are caught and displayed
- `RPCError` with multiple errors displays all errors as separate content sections
- Each error appears as red overlay content div
- Errors prevent auto-fade (user must acknowledge)

### Overlay Components

- **OverlayBackdrop** (`overlay-backdrop.ts`): Dark backdrop behind modal window
- **OverlayWindow** (`overlay-window.ts`): Modal window container with positioning
- **OverlayHeader** (`overlay-header.ts`): Header bar with title and action buttons
- **OverlayContent** (`overlay-content.ts`): Content container supporting single or array-based content with collapsible sections

**Content Headers**: See `overlay-content.ts` - `render()` method:
- Headers with text create collapsible sections (expand/collapse button)
- Empty string headers create sections without headers
- "Response" sections default to collapsed, "Request" sections default to expanded

---

## 4. PageData System

The PageData system provides field management and form processing that handles field registration, change detection, and MCP tool selection.

### PageData Base Class

**File**: `page-data.ts`

Base class for all page data types. Provides field access, field mapping, and handler methods.

**Field Access Pattern**: See `page-data.ts` - `getField()` method:
- Read-only field: `getField('name')` or `getField('name', 'display')`
- Editable field: `getField('name', 'form')` - automatically registers field with PageManager

**Field Registration**: See `page-data.ts` - `getField()` method:
- `getField(fieldName, 'form')` automatically registers field with PageManager
- Field type auto-detected based on value type
- Read-only fields (id, class, link, etc.) never register for editing

**Field Mappings**: See `page-data.ts` - `getFieldMappings()` method:
- Each PageData class defines field-to-MCP-tool mappings
- Priority system: `priority: 0` = exact match, `priority: 1` = small group, `priority: 2+` = larger groups
- `buildParams` function constructs MCP tool parameters

**Handler Methods**: See `page-data.ts` for handler examples (`modify_name()`, `modify_text()`, `delete_page()`, `add_page()`, `combo()`, `Upload()`):
- All CRUD handlers follow pattern: `async handlerName(rpc: any): Promise<void>`
- Register fields with `getField('fieldName', 'form')`
- Create form HTML with standardized field IDs
- Use `processOperationsIncrementally()` for UPDATE operations

### PageManager

**File**: `page-manager.ts`

Singleton manager for field registry, change detection, and form submission.

**Field Registry**: See `page-manager.ts` - `registerField()` method:
- Tracks which fields are being edited
- Stores original values for change detection
- Maps fields to DOM selectors (`#page-field-{fieldName}`)

**Change Detection**: See `page-manager.ts` - `detectChangedFields()` method:
- Returns array of field names that have changed
- Compares current form values to original registered values

**Optimal MCP Tool Selection**: See `page-manager.ts` - `selectOptimalMappings()` method:
- Uses weighted set cover algorithm with exact match preference
- Returns array of `{ mapping, fields }` pairs
- Prefers exact matches (priority 0) over grouped operations

**Form Value Extraction**: See `page-manager.ts` - `extractFormValues()` method:
- Returns `{ fieldName: value }` object
- Handles checkboxes, numbers, text inputs automatically

**Field Lifecycle**: See `page-manager.ts` methods:
1. Field registered when `getField('fieldName', 'form')` called
2. Field tracked in registry with original value
3. User edits field in form
4. `detectChangedFields()` identifies changes
5. `selectOptimalMappings()` selects MCP tools
6. Operations execute
7. Fields cleared from registry after successful update

### PageDataFactory

**File**: `page-data-factory.ts`

Factory pattern for creating appropriate PageData instance based on page class.

See `page-data-factory.ts` - `create()` method:
- Returns: `PageData`, `SourceCodeFilePageData`, `MCPRequestPageData`, `MCPActionPageData`, `WorkDocketPageData`
- Maps page class names to appropriate derived class

---

## 5. RPC Integration

The RPC client provides an interface for making MCP JSON-RPC calls with automatic debug option handling and error management.

### RPCClient

**File**: `rpc-client.ts`

MCP JSON-RPC wrapper with debug integration and error handling.

**Basic Usage**: See `rpc-client.ts` - `call()` method:
- `await rpc.call('get_page', { id: 123 })`
- Returns `RPCCallResult` with `data` and optional `debug` fields

**Debug Options**: See `rpc-client.ts` - `call()` method:
- Debug options automatically captured from current overlay if not provided
- Or provide explicitly as third parameter
- Merged into RPC params (debug → params.debug = 1, log → params.log = 1, etc.)

**Error Handling**: See `rpc-client.ts` - `call()` method and `RPCError` class:
- `RPCError` extends Error with `errors` array, `code`, optional `debug`, and `requestInfo`
- Multiple errors extracted from `error.data.errors` array
- Debug data extracted from `error.data.content` array

**Response Structure**: See `rpc-client.ts` - `extractMCPData()` method:
- MCP responses have structure: `{ content: [{ type: "text", text: "<JSON_STRING>" }] }`
- Automatically parses all content items and separates main data from debug data
- Debug data identified by presence of `entries` array

**Specialized Methods**: See `rpc-client.ts`:
- `getPage(pageId)`: Get page data as PageData instance
- `showError('operationName', error)`: Display error to user

---

## 6. Action Handlers

Action handlers are CRUD operation methods that live in PageData classes (base or derived). The app.ts file handles registration and routing.

### Handler Registration

**File**: `app.ts`

Action handlers are registered in two ways:

1. **Persistent Actions**: Server-rendered action links with `data-source` attribute
   - Loaded from `get_page` response `available_actions`
   - Attached to DOM elements by ID
   - Handlers found in PageData class

2. **Hot-Cache Actions**: Dynamically discovered actions
   - Also from `available_actions` but with `source: 'hot_cache'`
   - Can be added/removed dynamically
   - Same handler lookup pattern

**Handler Lookup Order**: See `app.ts` - `attachAppActionHandlers()` method:
1. Check PageData class for method matching action ID
2. Warn if handler not found

**Handler Signature**: See `page-data.ts` for handler examples:
- `async actionId(rpc: any): Promise<void>`

### Handler Location Pattern

**Standard Pattern**: Handlers live in PageData classes
- Base handlers: `page-data.ts` (modify_name, modify_text, delete_page, add_page, combo, Upload)
- Derived handlers: `source-code-file-page-data.ts` (source_code_file_combo)
- One file per page class type

### Handler Types

**UPDATE Handlers** (modify_name, modify_text, combo): See `page-data.ts` - `modify_name()`, `modify_text()`, `combo()` methods:
- Use `processOperationsIncrementally()` for multiple field updates
- Register fields with `getField('fieldName', 'form')`
- Use PageManager for change detection and optimal tool selection

**CREATE Handlers** (add_page): See `page-data.ts` - `add_page()` method:
- Direct `rpc.call()` (no field registry needed)
- Form validation before submission
- Redirect to new page after creation

**DELETE Handlers** (delete_page): See `page-data.ts` - `delete_page()` method:
- Direct `rpc.call()` with confirmation
- Redirect to parent after deletion

---

## 7. Form Patterns

Forms follow standardized patterns for field registration, change detection, and submission.

### Field Registration Pattern

**Standard Approach**: See `page-data.ts` - `getField()` method:
- Use `getField()` with `'form'` context
- Field automatically registered with PageManager
- Field type auto-detected (text, textarea, checkbox, number)

**Field ID Standardization**: See `page-manager.ts` - `registerField()` method:
- All form fields must use standardized IDs: `#page-field-{fieldName}`
- Pattern: `#page-field-{fieldName}`

### Form HTML Structure

**Standard Form Sections**: See `page-data.ts` - `combo()` method for example:
- Editable fields section with form inputs
- Read-only fields section with display grid
- Use array-based content structure with headers

### Operation Processing Patterns

**UPDATE Operations**: See `page-data.ts` - `modify_name()`, `modify_text()`, `combo()` methods:
- Use `processOperationsIncrementally()` for multiple fields
- Pattern: detect changed fields → select optimal mappings → extract form values → process operations incrementally
- Update DOM after successful operations

**CREATE Operations**: See `page-data.ts` - `add_page()` method:
- Direct `rpc.call()` with form validation
- Redirect to new page after creation using `_redirectAfterFade`

**DELETE Operations**: See `page-data.ts` - `delete_page()` method:
- Direct `rpc.call()` with confirmation checkbox
- Redirect to parent after deletion using `_redirectAfterFade: 'parent'`

### processOperationsIncrementally

**Purpose**: See `page-data.ts` - `processOperationsIncrementally()` method:
- Process multiple MCP operations sequentially, updating overlay as each completes
- Features: processes operations one at a time, updates overlay with success/error messages incrementally, handles debug data for each operation, captures debug options once at start

**Return Value**: See `page-data.ts` - `processOperationsIncrementally()` method:
- Returns object with `success`, `noChanges`, `operations`, `successes`, `errors`, `debug` fields

---

## 8. Debug Integration

The debug system is integrated into the overlay and RPC systems. Users can enable debug output for MCP calls from overlay forms.

### Debug Options Component

**File**: `overlay-debug-options.ts`

Debug options UI component that appears in overlay footer when submit button is shown.

**Standard Behavior**: See `overlay-debug-options.ts`:
- Always present in overlay footer (when submit button shown)
- Collapsed by default (like response section)
- Expandable section with checkboxes and filter inputs
- Checkboxes: Debug, Log
- Filter inputs: Blacklist, Graylist, Whitelist, Limit

**Debug Options Interface**: See `overlay-debug-options.ts` - `DebugOptions` interface:
- `debug: boolean`, `log: boolean`, `white?: string`, `gray?: string`, `black?: string`, `debugLimit?: number`

**Accessing Debug Options**: See `overlay.ts` - `getDebugOptions()` method:
- `overlay.getDebugOptions()` returns `DebugOptions` or null

### Debug Options in RPC Calls

**Automatic Capture**: See `rpc-client.ts` - `call()` method:
- RPC calls automatically capture debug options from current overlay
- Or provide explicitly as third parameter

**Debug Options Merging**: See `rpc-client.ts` - `call()` method:
- Debug options merged into RPC params (debug → params.debug = 1, log → params.log = 1, white → params.white, etc.)

### Debug Data Display

**Automatic Extraction**: See `rpc-client.ts` - `extractMCPData()` method:
- RPC responses automatically extract debug data from MCP content items

**Debug Table Overlay**: See `overlay.ts` - `showDebugTable()` method and `debug-helper.ts`:
- When debug data is present, a separate overlay window is automatically created
- Request section (expanded by default): Tool name and arguments
- Response section (collapsed by default): Response data JSON
- Debug table section (no header): Debug entries table

**Debug Table Format**: See `overlay-debug-table.ts`:
- Columns: Time, Level, Module, File, Function, Message
- Color-coded by module, filename, function
- Timestamps as deltas from first entry

### Debug Helper

**File**: `debug-helper.ts`

Helper function for creating debug overlay windows.

See `debug-helper.ts` - `handleRPCResponseWithDebug()` function:
- Automatically creates overlay with Request/Response/Debug sections
- Handles both success and error responses
- Only creates overlay if debug data has entries

---

## 9. Derived PageData Classes

Derived PageData classes extend the base class to provide page-type-specific field mappings and handlers.

### Factory Pattern

**File**: `page-data-factory.ts`

Factory creates appropriate PageData instance based on page class.

See `page-data-factory.ts` - `create()` method:
- Returns: `PageData`, `SourceCodeFilePageData`, `MCPRequestPageData`, `MCPActionPageData`, `WorkDocketPageData`
- Maps page class names to appropriate derived class

### SourceCodeFilePageData

**File**: `source-code-file-page-data.ts`

Handles source code file pages with `file_path` and `language` fields.

**Field Mappings**: See `source-code-file-page-data.ts` - `getFieldMappings()` method:
- `file_path` → `modify_file_path` (priority 0)
- `language` → `modify_language` (priority 0)

**Handler**: See `source-code-file-page-data.ts` - `source_code_file_combo()` method:
- Edit text, file_path, and language together

### MCPRequestPageData

**File**: `mcp-request-page-data.ts`

Handles MCP request pages with transaction fields.

**Field Mappings**: See `mcp-request-page-data.ts`:
- Group mapping for all transaction fields to `modify_mcp_request`
- Priority 1 (group operation)

### MCPActionPageData

**File**: `mcp-action-page-data.ts`

Handles MCP action request pages.

**Field Mappings**: See `mcp-action-page-data.ts`:
- Group mapping for all action fields to `modify_mcp_action_request`
- Priority 1 (group operation)

### WorkPageData

**File**: `work-page-data.ts`

Base class for work pages (work docket, ask, task, step). Provides shared functionality for `status`, `meta`, and `sort_order` fields.

**Field Mappings**: See `work-page-data.ts`:
- `status` → `modify_work_status` (priority 0)
- `sort_order` → `modify_work_sort_order` (priority 0)

### WorkDocketPageData

**File**: `work-docket-page-data.ts`

Extends `WorkPageData` to handle work docket pages. Inherits `status` and `sort_order` field mappings from base class.

### Creating New Derived Classes

**Pattern**: See `source-code-file-page-data.ts` for example:
1. Create new file: `{page-class}-page-data.ts`
2. Extend `PageData` base class
3. Override `getFieldMappings()` to add class-specific mappings
4. Add handler methods for class-specific operations
5. Register in `PageDataFactory.create()`

---

## 10. View Toggle System

The view toggle system enables hot-swapping between table and tile views for page sections (images, children by class) via client-side DOM replacement.

### ViewToggle Class

**File**: `view-toggle.ts`

Handles dynamic view switching for page sections. Listens for clicks on toggle links and replaces DOM chunks via MCP calls.

**Initialization**: See `view-toggle.ts` - `initializeViewToggle()` function:
- Auto-initializes on DOM ready
- Imported and called in `app.ts`
- Minimal wiring required

**Event Handling**: See `view-toggle.ts` - `initialize()` method:
- Uses event delegation on document
- Listens for clicks on `.updatePageView_{page_id}` links
- Extracts page_id from class name pattern

**Toggle Flow**: See `view-toggle.ts` - `handleToggleClick()` method:
1. Extract page_id from class name (e.g., `updatePageView_635` → `635`)
2. Extract `data-section` attribute (`images` or `children`)
3. Extract `data-class-name` attribute (for children sections)
4. Auto-detect current view type by checking for table element in DOM
5. Request opposite view type via MCP call
6. Replace DOM content with new HTML

**MCP Integration**: See `view-toggle.ts` - `handleToggleClick()` method:
- Calls `get_page_section` MCP tool via RPC client
- Parameters: `id`, `section`, `view_type`, `class_name` (for children)
- Extracts `dom_content` from response

**DOM Replacement**: See `view-toggle.ts` - `replaceSectionContent()` method:
- Determines content element ID based on section type:
  - Images: `pageImageGroup_{page_id}`
  - Children: `child_pages_{class_name}_{page_id}` (class_name converted to safe format)
- Finds existing content element in DOM
- Replaces innerHTML (preserves element structure)
- Handles clearboth div insertion/removal for tile views

**View Type Detection**: See `view-toggle.ts` - `handleToggleClick()` method:
- Checks next sibling of header element for table element
- If table present → current view is 'table', request 'tile'
- If no table → current view is 'tile', request 'table'

### Toggle Link Structure

**HTML Pattern**: See `render_show_page.py` for header generation:
```html
<div id="pageImageGroupHeader_{page_id}" class="contentHeader">
  <a class="updatePageView_{page_id}" 
     data-section="images">IMAGES</a>
</div>
<div id="pageImageGroup_{page_id}" class="content pageImageGroup">
  <!-- table or tile content -->
</div>
```

**Children Sections**: See `render_show_page.py` for children headers:
```html
<div id="child_pages_{class_name}_header_{page_id}" class="contentHeader">
  <a class="updatePageView_{page_id}" 
     data-section="children" 
     data-class-name="{class_name}">{Human Readable Name}</a>
</div>
<div id="child_pages_{class_name}_{page_id}" class="content">
  <!-- table or tile content -->
</div>
```

**Key Points**:
- Headers are static (don't get swapped)
- Only content divs are replaced
- Each section/class has unique IDs for targeting
- TypeScript auto-detects current view type

### Integration with Render System

**Server-Side Rendering**: All HTML generation happens server-side:
- `get_page_section` action returns HTML in `dom_content` field
- Supports both table and tile rendering
- Wrapper IDs generated for DOM targeting

**Backend Override**: See `render.py` - `render_block()` function:
- `backend` parameter allows forcing HTML rendering when called via MCP
- Ensures HTML tables are rendered even when gateway.backend is 'mcp'

**Callback System**: See `view-toggle.ts` - `ViewToggleCallbacks` interface:
- `onBeforeSwap`: Called before DOM replacement (can modify HTML)
- `onAfterSwap`: Called after DOM replacement (for re-initialization)
- Used by Browser system to re-intercept links after view toggles

## 11. Browser System

The browser system provides hierarchical navigation and selection within modal overlays, enabling users to select pages or images for operations like move, copy, or image selection.

### Browser Class

**File**: `browser.ts`

Main browser component that manages hierarchical navigation and selection within overlay windows.

**Initialization**: See `browser.ts` - `Browser` constructor:
- `mode: 'page' | 'image'` - Selection mode (single page ID or multiple image IDs)
- `initialPageId: number` - Starting page for navigation
- `onSubmit: (result) => Promise<any>` - Callback when user submits selection

**Navigation Flow**: See `browser.ts` - `loadAndRender()` method:
1. Calls `get_browser` MCP tool with current page ID
2. Receives HTML with overlay classes/IDs already applied
3. Injects HTML into overlay content area
4. Intercepts all links to retarget browser navigation
5. User clicks links → browser updates to new page

**Link Interception**: See `browser.ts` - `interceptLinks()` method:
- Scans overlay window for all `<a>` tags
- Replaces default navigation with browser retargeting
- Page links → update browser to new page
- Image links (in image mode) → add/remove from selection buffer
- Preserves data attributes (`data-page-id`, `data-image-rank`, etc.)

**Image Selection Mode**: See `browser.ts` - `handleImageClick()` method:
- When `mode === 'image'`, clicking images adds them to selection buffer
- Buffer displays selected images as tiles at top of browser
- Clicking buffer items removes them from selection
- Same image can be selected multiple times
- Buffer shows both tile and table views of selected images

**Image Buffer**: See `browser.ts` - `renderImageBuffer()` method:
- Displays selected images at top of browser overlay
- Shows tiles and table views simultaneously
- Clicking any buffer item (tile or row) removes it
- Buffer updates live as images are added/removed

**View Toggle Integration**: See `browser.ts` - `setupViewToggle()` method:
- Registers callbacks with ViewToggle system
- `onAfterSwap`: Re-intercepts links after view toggle completes
- Ensures link interception works after table/tile swaps

**Z-Stack Support**: See `browser.ts` - `getBrowserWindowElement()` method:
- Uses `this.overlay.windowEl` to target specific browser overlay
- Prevents conflicts when multiple overlays are stacked
- Link interception scoped to browser's specific overlay window

**Submit Handling**: See `browser.ts` - `handleSubmit()` method:
- Page mode: Returns current page ID as number
- Image mode: Returns array of selected image IDs
- Calls `onSubmit` callback with result
- Callback can return `{ _autoFade: true }` to close browser
- Callback can return `{ _autoFade: false }` to keep browser open

### Browser Integration Patterns

**Form Integration**: See `page-actions-pages.ts` - `move_page()` and `copy_page()` methods:
- Forms can include "Browser" middle button
- Button opens browser overlay as z-stack on top of form
- Browser callback updates form input field with selected page ID
- Browser closes automatically after selection
- Form submit uses the selected page ID

**Image Selection**: See `page-actions-images.ts` - `copy_images_app()` and `move_images_app()` methods:
- Browser opened in `mode: 'image'`
- User navigates pages and selects images
- Selected images stored with `source_page_id` and `source_rank` metadata
- Submit processes all selected images with their source information

**Callback-Only Mode**: See `page-actions-pages.ts` - `move_page()` onMiddleButton:
- Browser can be used purely for selection (no MCP calls)
- Debug options in browser are ignored
- Only the callback result matters
- Used for populating form fields

### get_browser Action

**MCP Tool**: `get_browser`

Always returns HTML content with overlay classes/IDs pre-applied. Reuses rendering infrastructure from `show_page` but with overlay-specific modifications.

**Parameters**: See `hh/page/get_browser.py`:
- `id`: Page ID to display
- Returns HTML with `overlay_` prefix on all content IDs
- Uses `render_helpers.py` for consistent rendering

**Overlay Mode**: See `hh/page/render_helpers.py`:
- `overlay_mode=True` adds `overlay` class to content divs
- `wrapper_id_prefix='overlay_'` ensures unique IDs
- Headers and content sections get overlay-specific styling

### ImageGroupSorter

**File**: `image-group-sorter.ts`

Specialized browser extension for sorting images within a page's image group.

**Features**: See `image-group-sorter.ts`:
- Shows only image group for current page
- Drag-and-drop reordering using SortableJS library
- No navigation or image selection (sorting only)
- Tracks old and new ranks for each image
- Optimized sorting algorithm (moves largest distance first)
- Incremental success messages per operation
- Final verification pass to ensure correct order

**Sorting Algorithm**: See `image-group-sorter.ts` - `handleSubmit()` method:
- Iteratively moves image with largest rank distance
- Recalculates distances after each server response
- Uses `set_image_rank` MCP tool for each move
- Updates internal rank map from server responses
- Failsafe: Maximum iterations = number of images

**Integration**: See `page-actions-images.ts` - `sort_images_app()` method:
- Opens ImageGroupSorter overlay
- User drags and drops images to reorder
- Submit triggers optimized sorting algorithm
- Page refreshes after successful sort

## 12. Image Viewer

The image viewer provides a full-screen viewing experience for images in a page's image group, with pan/zoom capabilities and keyboard navigation.

### ImageViewer Class

**File**: `image-viewer.ts`

Full-screen image viewer overlay that opens when clicking images in a page's image group. Supports pan, zoom, touch gestures, and keyboard navigation.

**Initialization**: See `image-viewer.ts` - `ImageViewer` constructor:
- `pageId: number` - Page ID containing the image group
- `initialImageId?: number` - Optional image ID to start viewing (defaults to first image)

**Entry Point**: See `image-viewer.ts` - `openFromImageLink()` static method:
```typescript
static async openFromImageLink(pageId: number, imageId?: number): Promise<void>
```
- Static method for opening viewer from image links
- Creates viewer instance and calls `show()`

**Overlay Integration**: See `image-viewer.ts` - `renderOverlay()` method:
- Uses `OverlayManager.getInstance().show()` with `mode: 'zoomable'`
- Sets `imageViewerMode: true` for special overlay behavior
- Provides `footerContent` for caption display (link to `/img/{id}`)
- Header shows "Image Viewer" with Cancel button
- Middle button shows "More Info" linking to image page

**Zoom States**: See `image-viewer.ts` - `getZoomState()` method:
- **State 1 (zoomedOut)**: Image fully visible, centered, no panning allowed
- **State 2 (between)**: First axis fills viewport, single-axis panning enabled
- **State 3 (zoomedIn)**: Image fills entire viewport, both X and Y panning enabled

**Sizing Approach**: See `image-viewer.ts` - `initializeBaseSizes()` method:
- Width-only control: Only sets width on overlay window, lets height auto-calculate
- Avoids complex height calculations accounting for header, footer, padding, borders
- Reads `offsetHeight` after rendering for inflection calculations
- Images set intrinsic width/height to avoid first-load mis-measurements

**Event Handling**: See `image-viewer.ts` - `bindEvents()` method:
- **Mouse Wheel**: Zoom in/out with detent at inflection points
- **Mouse Drag**: Pan image when zoomed (state-based constraints)
- **Touch Pinch**: Zoom in/out with max-scale clamp
- **Touch Drag**: Pan image when zoomed
- **Touch Swipe**: Navigate between images when at default scale
- **Keyboard**: Arrow Left/Right navigate between images, Escape closes (handled by overlay)

**Navigation**: See `image-viewer.ts` - `navigate()` method:
- Moves to next/previous image in group
- Resets zoom and pan state when navigating
- Updates image content and caption

**Data Loading**: See `image-viewer.ts` - `loadAndRender()` method:
- Calls `get_image_group` MCP tool to fetch all images and instances
- Receives JSON with image metadata and instance data
- Finds initial image index if `initialImageId` provided
- Renders overlay with first image

**MCP Tool**: `get_image_group`
- Returns JSON data for all images in a page's image group
- Includes image metadata (id, caption, visibility, viewCount)
- Includes instance data (width, height, filesize, src) sorted by width (smallest first)
- Used by ImageViewer to load image data

**Overlay Mode Details**: See `overlay.ts` - zoomable mode:
- `mode: 'zoomable'` triggers special behavior:
  - No debug options section rendered
  - Raw content mode (no `div.content` wrapper)
  - Footer support for caption
  - Touch handling: `touch-action: none` on window/backdrop
  - Explicit pinch handlers prevent default browser behavior

**CSS Classes**: See `overlay.css`:
- `.overlay-window.zoomable` - Zoomable overlay window styling
- `.overlay-window.zoomable .contentWrapper` - Content wrapper styling
- `.overlay-window.zoomable .image-viewer-box` - Image container styling
- All overlay CSS uses `.overlay-window` class selector (not `#overlayWindow` ID) for z-stacking support

---

## 13. File Upload

### UploadHandler

**File**: `upload-handler.ts`

Handles image file uploads with multi-file support.

**Usage**: See `upload-handler.ts`:
- `new UploadHandler(rpc, seedData)` then `await handler.handle()`

**Features**: See `upload-handler.ts`:
- Multiple file selection
- Upload progress bars
- Sequential processing (upload all, then process one at a time)
- Debug options support
- Success/error messages per file

**Upload Flow**: See `upload-handler.ts`:
1. User selects files (via "Choose Files" button)
2. Files added to overlay with pending status
3. User clicks "Upload"
4. All files upload in parallel (with progress bars)
5. Files convert to "pending processing" state
6. Files process sequentially (one MCP call per file)
7. Success/error messages shown per file
8. Overlay auto-fades and refreshes page on success

**Debug Integration**: See `upload-handler.ts`:
- Debug options captured when "Upload" clicked
- Same debug options applied to all file processing calls
- Debug overlays shown for each file with debug data

---

## 14. Best Practices

### Handler Development

**Location**: Always put handlers in PageData classes (base or derived)
- One file per page class type
- Keeps related code together

**Naming**: Handler method names match action IDs exactly
- Action ID: `modify_name` → Method: `async modify_name(rpc: any)`
- Action ID: `source_code_file_combo` → Method: `async source_code_file_combo(rpc: any)`

**Error Handling**: Use standardized error pattern
- Return objects with `_showMessage` for success
- Throw errors for validation failures
- Multiple errors automatically stack as separate content sections
- Use `_autoFade: true` for successful operations

**Field Registration**: Always use `getField()` pattern
- `getField('fieldName', 'form')` for editable fields
- `getField('fieldName')` or `getField('fieldName', 'display')` for read-only
- Never manually call `PageManager.registerField()`

**Field IDs**: Always use standardized pattern
- `#page-field-{fieldName}` (e.g., `#page-field-name`, `#page-field-text`)
- Required for automatic form value extraction

### Content Structure

**Array-Based System** (required): See `overlay-content.ts` - `render()` method:
- All content must be provided as an array, even for single items
- `content: Array<string | HTMLElement>`
- `contentHeaders: Array<string>` (empty string = no header)

### Operation Processing

**UPDATE Operations**: Use `processOperationsIncrementally()`
- Multiple fields can change
- Optimal MCP tool selection
- Incremental feedback to user

**CREATE Operations**: Direct `rpc.call()`
- Single operation
- No field registry needed
- Redirect after creation

**DELETE Operations**: Direct `rpc.call()` with confirmation
- Confirmation checkbox required
- Redirect to parent after deletion

### Debug Integration

**Always Support Debug Options**:
- Debug options automatically available in overlay
- RPC calls automatically capture options
- Debug data automatically displayed in separate overlay

**Debug Options State**:
- Always present in footer but collapsed by default
- Collapses automatically when form is submitted
- User expands when needed

### Redirect Handling

**Standardized Redirect Pattern**: See `overlay.ts` - `handleRedirect()` method:
- `_redirectAfterFade: 'parent'` - Redirect to parent page
- `_redirectAfterFade: 'self'` - Refresh current page
- `_redirectAfterFade: '/url'` - Redirect to specific URL
- Omit or null = no redirect, just fade

**When to Redirect**:
- DELETE: Always redirect to parent
- CREATE: Redirect to new page
- UPDATE: Usually no redirect (DOM updated dynamically)
- Exception: Text updates may refresh page due to processing complexity

### Form Patterns

**Standard Form Structure**: See `page-data.ts` - `combo()` method for example:
- Editable fields section with form inputs
- Read-only fields section with display grid
- Use array-based content structure with headers

**Field Cleanup**: Always clear field registry on cancel/unmount:
- `onCancel: () => { pageManager.clearFieldRegistry(); }`
- `onUnmount: () => { pageManager.clearFieldRegistry(); }`

### RPC Call Patterns

**Standard RPC Call**: See `rpc-client.ts` - `call()` method:
- `const result = await rpc.call('tool_name', { param1: value1, param2: value2 })`
- `result.data` contains response
- `result.debug` contains debug data if present

**Error Handling**: See `rpc-client.ts` - `call()` method:
- `try/catch` with `RPCError` handling
- Errors automatically displayed in overlay
- No need to manually handle display

---

## Summary

The TypeScript system provides client-side functionality for the Henhouse HTTP interface:

- **Overlay System**: Component-based modal dialogs with array-based content structure
- **PageData Architecture**: Field management and form processing with automatic MCP tool selection
- **RPC Integration**: MCP JSON-RPC wrapper with automatic debug handling
- **Browser System**: Hierarchical navigation and selection within overlays for pages, images, files, audio, and video
- **View Toggle System**: Hot-swapping between table and tile views for page sections
- **ImageViewer**: Full-screen image viewer with pan/zoom capabilities, touch gestures, and keyboard navigation
- **Audio/Video Viewers**: Playback viewers with streaming support
- **Standardized Patterns**: Consistent handler patterns, field registration, and error handling
- **Debug Integration**: Debug system integrated with overlay UI

The system can be extended with new page types and handlers following the patterns documented above.

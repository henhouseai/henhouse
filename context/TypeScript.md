# Henhouse TypeScript System Architecture

This document covers the TypeScript/ES modules system that provides client-side interactivity for the Henhouse HTTP interface, including overlay management, page data handling, RPC integration, and form processing.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Core Overlay System](#2-core-overlay-system)
3. [PageData System](#3-pagedata-system)
4. [RPC Integration](#4-rpc-integration)
5. [Action Handlers](#5-action-handlers)
6. [Form Patterns](#6-form-patterns)
7. [Debug Integration](#7-debug-integration)
8. [Derived PageData Classes](#8-derived-pagedata-classes)
9. [File Upload](#9-file-upload)
10. [Best Practices](#10-best-practices)

## Agent Quick Reference

- **Overlay System**: `OverlayManager.getInstance().show(options)` - Singleton pattern for modal management
- **PageData Pattern**: Handlers live in PageData classes (one file per derived class)
- **Field Registration**: Use `getField('fieldName', 'form')` to auto-register editable fields
- **Field IDs**: Standardized as `#page-field-{fieldName}` (e.g., `#page-field-name`)
- **Content Structure**: Use array-based system: `content: Array<string | HTMLElement>`, `contentHeaders: Array<string>`
- **Operation Processing**: UPDATE uses `processOperationsIncrementally()`, CREATE/DELETE use direct `rpc.call()`
- **Error Handling**: Return objects with `_showMessage`, errors stack as individual overlay content divs
- **Debug Options**: Always present but collapsed by default (like response section)
- **Redirect Handling**: Use `_redirectAfterFade: 'parent' | 'self' | '/url' | null`

## Agent Training Notes

### Overlay System Usage
- Always use `OverlayManager.getInstance().show()` - never instantiate directly
- Content should use array-based structure with headers for multiple sections
- Debug options automatically available when submit button is shown
- Errors automatically stack as separate content sections

### PageData Handler Pattern
- All CRUD handlers live in PageData classes (base or derived)
- Use `getField('fieldName', 'form')` to register fields for editing
- Use `getField('fieldName')` or `getField('fieldName', 'display')` for read-only display
- Handlers accept `rpc` as first parameter

### Form Field Management
- Fields auto-register when accessed with `context: 'form'`
- Field IDs must follow `#page-field-{fieldName}` pattern
- PageManager handles change detection and optimal MCP tool selection
- Use `processOperationsIncrementally()` for UPDATE operations with multiple fields

### RPC Integration
- Use `rpc.call(method, params, debugOptions?)` for MCP calls
- Debug options automatically captured from overlay if not provided
- Errors return `RPCError` with multiple error messages
- Debug data automatically extracted and displayed in separate overlay

### Error Handling
- Return objects with `_showMessage` for success messages
- Throw errors for validation failures (will be caught and displayed)
- Multiple errors automatically stack as separate red content sections
- Use `_autoFade: true` for successful operations that should auto-close

---

## 1. System Overview

The TypeScript system provides client-side interactivity for the Henhouse HTTP interface, using ES modules architecture. The system integrates with the Python MCP backend through JSON-RPC 2.0 calls and provides an overlay system for user interactions.

### Architecture Flow

```
Python HTTP Backend (renders HTML)
    ↓ (includes seed data, action links)
TypeScript App (app.ts)
    ↓ (loads page data, attaches handlers)
User Interaction
    ↓ (clicks action link)
Overlay System
    ↓ (shows modal, captures form data)
RPC Client
    ↓ (MCP JSON-RPC call)
Python Gateway
    ↓ (executes MCP tool, returns JSON)
TypeScript Components
    ↓ (updates DOM, manages state)
User Sees Updated UI
```

### Key Components

- **OverlayManager**: Singleton manager for all modal overlays
- **PageData/PageManager**: Field management and form processing system
- **RPCClient**: MCP JSON-RPC wrapper with debug integration
- **Action Handlers**: CRUD operation handlers in PageData classes
- **Debug System**: Integrated debug options and table rendering

### File Structure

```
hh/deploy/site/ts/
  ├─ app.ts                      # Main entry point, action handler registration
  ├─ overlay-manager.ts          # OverlayManager singleton
  ├─ overlay.ts                  # Base Overlay component
  ├─ overlay-backdrop.ts         # Backdrop component
  ├─ overlay-window.ts            # Window container component
  ├─ overlay-header.ts            # Header with buttons
  ├─ overlay-content.ts           # Content container (supports arrays)
  ├─ overlay-debug-options.ts     # Debug options UI
  ├─ overlay-debug-table.ts       # Debug table rendering
  ├─ debug-helper.ts             # Debug overlay helper
  ├─ rpc-client.ts                # MCP RPC client
  ├─ page-manager.ts              # Field registry and form processing
  ├─ page-data.ts                 # Base PageData class
  ├─ page-data-factory.ts         # Factory for derived classes
  ├─ source-code-file-page-data.ts
  ├─ mcp-request-page-data.ts
  ├─ mcp-action-page-data.ts
  ├─ work-docket-page-data.ts
  ├─ upload-handler.ts            # Image upload handler
  ├─ seed.ts                      # Seed data reader
  └─ test.ts                      # Temporary test handlers
```

---

## 2. Core Overlay System

The overlay system provides modal dialogs for user interactions, using a component-based architecture.

### OverlayManager

**File**: `overlay-manager.ts`

Singleton manager for all overlay instances. Handles z-index stacking, focus management, keyboard shortcuts, and event routing.

**Usage**:
```typescript
import { OverlayManager } from './overlay-manager.js';

const manager = OverlayManager.getInstance();
const overlay = manager.show({
  header: 'My Overlay',
  content: ['Section 1 content', 'Section 2 content'],
  contentHeaders: ['Section 1', 'Section 2'],
  closable: true,
  submitLabel: 'Submit',
  onSubmit: async () => {
    // Handle submission
    return { _showMessage: 'Success!', _autoFade: true };
  }
});
```

**Key Methods**:
- `getInstance()`: Get singleton instance
- `show(options)`: Show new overlay, returns Overlay instance
- `close(overlay)`: Close specific overlay with fade
- `closeAll()`: Close all overlays
- `getTopOverlay()`: Get topmost overlay (highest z-index)
- `isActive()`: Check if any overlay is active

### Overlay Component

**File**: `overlay.ts`

Base overlay component that handles lifecycle, rendering, and state management.

**OverlayOptions Interface**:
```typescript
interface OverlayOptions {
  header?: string | HTMLElement;
  content?: Array<string | HTMLElement>;  // Array-based content structure (required)
  contentHeaders?: Array<string>;  // Optional headers for each content section
  footer?: string | HTMLElement;
  closable?: boolean;
  showSubmit?: boolean;
  submitLabel?: string;
  cancelLabel?: string;
  middleButtonLabel?: string;
  onMiddleButton?: () => void;
  onMount?: () => void;
  onUnmount?: () => void;
  onSubmit?: () => Promise<any> | any;
  onCancel?: () => void;
  onError?: (error: Error) => void;
  className?: string;
  style?: Partial<CSSStyleDeclaration>;
}
```

**Content Structure**:
The overlay system uses an array-based content structure:

- `content: Array<string | HTMLElement>` - Array of content items
- `contentHeaders: Array<string>` - Optional headers for each content section (empty string = no header)

**Array-Based Structure**:
```typescript
manager.show({
  header: 'Debug Information',
  content: [
    '<div>Request info HTML</div>',
    '<div>Response data HTML</div>',
    debugTableElement
  ],
  contentHeaders: ['Request', 'Response', ''],  // Empty string = no header
  // ...
});
```

**State Management**:
- `isVisible`: Overlay visibility state
- `isLoading`: Loading state (hides submit button, shows spinner)
- `error`: Single error message (legacy)
- `success`: Single success message (legacy)
- `messages`: Array of messages `[{ type: 'success' | 'error', text: string }]` (preferred)

**Submit Result Format**:
```typescript
{
  _showMessage?: string;           // Custom success message
  _autoFade?: boolean;              // Auto-close after success
  _redirectAfterFade?: 'parent' | 'self' | '/url' | null;
  debug?: DebugData;                // Debug data (prevents auto-fade)
  success?: boolean;                // Operation success
  errors?: Array<any>;               // Operation errors
}
```

**Error Handling**:
- Thrown errors are caught and displayed
- `RPCError` with multiple errors displays all errors as separate content sections
- Each error appears as red overlay content div
- Errors prevent auto-fade (user must acknowledge)

### Overlay Components

**OverlayBackdrop** (`overlay-backdrop.ts`): Dark backdrop behind modal window
**OverlayWindow** (`overlay-window.ts`): Modal window container with positioning
**OverlayHeader** (`overlay-header.ts`): Header bar with title and action buttons
**OverlayContent** (`overlay-content.ts`): Content container supporting single or array-based content with collapsible sections

**Content Headers**:
- Headers with text create collapsible sections (expand/collapse button)
- Empty string headers create sections without headers
- "Response" sections default to collapsed, "Request" sections default to expanded

---

## 3. PageData System

The PageData system provides field management and form processing that handles field registration, change detection, and MCP tool selection.

### PageData Base Class

**File**: `page-data.ts`

Base class for all page data types. Provides field access, field mapping, and handler methods.

**Field Access Pattern**:
```typescript
// Read-only field (for display)
const pageName = this.getField('name');  // or getField('name', 'display')

// Editable field (registers for form processing)
const currentName = this.getField('name', 'form');
```

**Field Registration**:
- `getField(fieldName, 'form')` automatically registers field with PageManager
- Field type auto-detected based on value type
- Read-only fields (id, class, link, etc.) never register for editing

**Field Mappings**:
Each PageData class defines field-to-MCP-tool mappings:

```typescript
protected getFieldMappings(): FieldMapping[] {
  return [
    {
      fields: ['name'],
      mcpTool: 'modify_name',
      priority: 0,  // Lower = higher priority (exact match)
      buildParams: (fields, values, pageId) => ({
        page_id: pageId,
        name: values['name']
      })
    },
    {
      fields: ['text'],
      mcpTool: 'modify_text',
      priority: 0,
      buildParams: (fields, values, pageId) => ({
        page_id: pageId,
        text: values['text']
      })
    }
  ];
}
```

**Priority System**:
- `priority: 0`: Exact match (single field → single tool)
- `priority: 1`: Small group (few fields → one tool)
- `priority: 2+`: Larger groups

**Handler Methods**:
All CRUD handlers follow this pattern:
```typescript
async handlerName(rpc: any): Promise<void> {
  const pageId = this.id;
  if (!pageId) {
    alert('No page ID found');
    return;
  }

  try {
    const pageManager = PageManager.getInstance();
    
    // Register fields for editing
    const currentValue = this.getField('fieldName', 'form') || '';
    
    // Create form HTML with standardized field IDs
    const formHtml = `
      <div class="overlay-form-group">
        <label>Field Label:</label>
        <input type="text" id="page-field-fieldName" value="${this.escapeHtml(currentValue)}" class="overlay-form-input">
      </div>
    `;

    OverlayManager.getInstance().show({
      header: 'Form Title',
      content: formHtml,
      closable: true,
      submitLabel: 'Submit',
      cancelLabel: 'Cancel',
      onCancel: () => {
        pageManager.clearFieldRegistry();
      },
      onUnmount: () => {
        pageManager.clearFieldRegistry();
      },
      onSubmit: async () => {
        // Process operations (see Form Patterns section)
        // ...
      }
    });
  } catch (error) {
    rpc.showError('handlerName', error);
  }
}
```

### PageManager

**File**: `page-manager.ts`

Singleton manager for field registry, change detection, and form submission.

**Field Registry**:
- Tracks which fields are being edited
- Stores original values for change detection
- Maps fields to DOM selectors (`#page-field-{fieldName}`)

**Change Detection**:
```typescript
const changedFields = pageManager.detectChangedFields();
// Returns array of field names that have changed
```

**Optimal MCP Tool Selection**:
```typescript
const optimalMappings = pageManager.selectOptimalMappings(changedFields);
// Returns array of { mapping, fields } pairs
// Uses weighted set cover algorithm with exact match preference
```

**Form Value Extraction**:
```typescript
const currentValues = pageManager.extractFormValues();
// Returns { fieldName: value } object
// Handles checkboxes, numbers, text inputs automatically
```

**Field Lifecycle**:
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

```typescript
const pageData = PageDataFactory.create(getPageResponse);
// Returns: PageData, SourceCodeFilePageData, MCPRequestPageData, etc.
```

---

## 4. RPC Integration

The RPC client provides an interface for making MCP JSON-RPC calls with automatic debug option handling and error management.

### RPCClient

**File**: `rpc-client.ts`

MCP JSON-RPC wrapper with debug integration and error handling.

**Basic Usage**:
```typescript
import { RPCClient } from './rpc-client.js';

const rpc = new RPCClient();
const result = await rpc.call('get_page', { id: 123 });
// result.data contains the response data
// result.debug contains debug data if present
```

**Debug Options**:
Debug options are automatically captured from the current overlay if not provided:

```typescript
// Debug options automatically read from overlay
const result = await rpc.call('modify_name', { page_id: 123, name: 'New Name' });

// Or provide explicitly
const result = await rpc.call('modify_name', { page_id: 123, name: 'New Name' }, debugOptions);
```

**Error Handling**:
```typescript
try {
  const result = await rpc.call('some_tool', params);
} catch (error) {
  // error is RPCError with:
  // - message: Main error message
  // - code: Error code
  // - errors: Array of { type, content } for multiple errors
  // - debug: Optional debug data
  // - requestInfo: { method, params }
}
```

**RPCError Class**:
```typescript
class RPCError extends Error {
  errors: Array<{ type: string; content: string }>;
  code: number;
  debug?: DebugData;
  requestInfo?: { method: string; params: any };
}
```

**Response Structure**:
MCP responses have structure:
```json
{
  "content": [
    {
      "type": "text",
      "text": "<JSON_STRING>"
    },
    {
      "type": "text",
      "text": "<DEBUG_JSON_STRING>"
    }
  ]
}
```

`extractMCPData()` automatically parses all content items and separates main data from debug data.

**Specialized Methods**:
```typescript
// Get page data as PageData instance
const pageData = await rpc.getPage(pageId);

// Display error to user
rpc.showError('operationName', error);
```

---

## 5. Action Handlers

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

**Handler Lookup Order**:
1. Check PageData class for method matching action ID
2. Warn if handler not found

**Handler Signature**:
```typescript
async actionId(rpc: any): Promise<void> {
  // Handler implementation
}
```

### Handler Location Pattern

**Standard Pattern**: Handlers live in PageData classes
- Base handlers: `page-data.ts` (modify_name, modify_text, delete_page, add_page, combo, Upload)
- Derived handlers: `source-code-file-page-data.ts` (source_code_file_combo)
- One file per page class type

### Handler Types

**UPDATE Handlers** (modify_name, modify_text, combo):
- Use `processOperationsIncrementally()` for multiple field updates
- Register fields with `getField('fieldName', 'form')`
- Use PageManager for change detection and optimal tool selection

**CREATE Handlers** (add_page):
- Direct `rpc.call()` (no field registry needed)
- Form validation before submission
- Redirect to new page after creation

**DELETE Handlers** (delete_page):
- Direct `rpc.call()` with confirmation
- Redirect to parent after deletion

**READ Handlers** (pageInfo - not yet implemented):
- Display-only, no form submission
- Show information in overlay

---

## 6. Form Patterns

Forms follow standardized patterns for field registration, change detection, and submission.

### Field Registration Pattern

**Standard Approach**: Use `getField()` with `'form'` context

```typescript
// Register field for editing
const currentName = this.getField('name', 'form') || '';
const currentText = this.getField('text', 'form') || '';

// Field automatically registered with PageManager
// Field type auto-detected (text, textarea, checkbox, number)
```

**Field ID Standardization**:
All form fields must use standardized IDs:
```html
<input type="text" id="page-field-name" ...>
<textarea id="page-field-text" ...>
<input type="checkbox" id="page-field-someFlag" ...>
```

Pattern: `#page-field-{fieldName}`

### Form HTML Structure

**Standard Form Sections**:
```html
<div class="overlay-form-section">
  <h3 class="overlay-section-title">Editable Fields:</h3>
  <div class="overlay-form-group">
    <label>Field Label:</label>
    <input type="text" id="page-field-fieldName" class="overlay-form-input">
  </div>
</div>

<div class="overlay-form-divider">
  <h3 class="overlay-section-title">Read-Only Fields:</h3>
  <div class="overlay-form-grid">
    <div><strong>Label:</strong></div>
    <div>Value</div>
  </div>
</div>
```

### Operation Processing Patterns

**UPDATE Operations** (multiple fields):
```typescript
onSubmit: async () => {
  const changedFields = pageManager.detectChangedFields();
  const editableFields = changedFields.filter(field => field !== 'class');
  
  if (editableFields.length === 0) {
    return { success: true, noChanges: true, _showMessage: 'No changes made', _autoFade: true };
  }
  
  const optimalMappings = pageManager.selectOptimalMappings(editableFields);
  const currentValues = pageManager.extractFormValues();
  
  const result = await this.processOperationsIncrementally(rpc, optimalMappings, currentValues, pageId);
  
  if (result.success && result.errors.length === 0) {
    // Update DOM, refresh data, etc.
    return { ...result, _autoFade: true, debug: result.debug };
  } else {
    // Errors already shown in overlay
    return { ...result, debug: result.debug };
  }
}
```

**CREATE Operations** (single operation):
```typescript
onSubmit: async () => {
  // Validate form
  const params = {
    target_page: pageId,
    class: selectedClass,
    name: nameValue
  };
  
  const result = await rpc.call('add_page', params);
  
  return {
    success: true,
    _showMessage: `Page created successfully.`,
    _autoFade: true,
    _redirectAfterFade: this.getPageUrl(newPageId),
    debug: result.debug
  };
}
```

**DELETE Operations** (with confirmation):
```typescript
onSubmit: async () => {
  const confirmCheckbox = document.getElementById('page-delete-confirm') as HTMLInputElement;
  if (!confirmCheckbox || !confirmCheckbox.checked) {
    throw new Error('You must confirm deletion by checking the confirmation box');
  }
  
  const result = await rpc.call('delete_page', {
    page_id: pageId,
    confirm: true
  });
  
  return {
    success: true,
    _showMessage: `Page deleted successfully.`,
    _autoFade: true,
    _redirectAfterFade: this.getPageUrl(parentId),
    debug: result.debug
  };
}
```

### processOperationsIncrementally

**Purpose**: Process multiple MCP operations sequentially, updating overlay as each completes.

**Features**:
- Processes operations one at a time (not parallel)
- Updates overlay with success/error messages incrementally
- Handles debug data for each operation
- Captures debug options once at start (all operations use same options)

**Usage**:
```typescript
const result = await this.processOperationsIncrementally(
  rpc,
  optimalMappings,  // Array of { mapping, fields }
  currentValues,     // { fieldName: value }
  pageId
);
```

**Return Value**:
```typescript
{
  success: boolean;
  noChanges: boolean;
  operations: Array<{
    mapping: string;
    fields: string[];
    success: boolean;
    result?: any;
    error?: any;
    message: string;
  }>;
  successes: Array<...>;
  errors: Array<...>;
  debug?: {};  // Present if any operation had debug data
}
```

---

## 7. Debug Integration

The debug system is integrated into the overlay and RPC systems. Users can enable debug output for MCP calls from overlay forms.

### Debug Options Component

**File**: `overlay-debug-options.ts`

Debug options UI component that appears in overlay footer when submit button is shown.

**Standard Behavior**:
- Always present in overlay footer (when submit button shown)
- Collapsed by default (like response section)
- Expandable section with checkboxes and filter inputs
- Checkboxes: Debug, Log
- Filter inputs: Blacklist, Graylist, Whitelist, Limit

**Debug Options Interface**:
```typescript
interface DebugOptions {
  debug: boolean;
  log: boolean;
  white?: string;
  gray?: string;
  black?: string;
  debugLimit?: number;
}
```

**Accessing Debug Options**:
```typescript
const overlay = OverlayManager.getInstance().getTopOverlay();
const debugOptions = overlay?.getDebugOptions();
// Returns DebugOptions or null
```

### Debug Options in RPC Calls

**Automatic Capture**:
RPC calls automatically capture debug options from current overlay:

```typescript
// Debug options automatically read from overlay
const result = await rpc.call('modify_name', { page_id: 123, name: 'New Name' });
```

**Explicit Override**:
```typescript
// Provide debug options explicitly
const result = await rpc.call('modify_name', { page_id: 123, name: 'New Name' }, {
  debug: true,
  log: true,
  gray: 'response.py'
});
```

**Debug Options Merging**:
Debug options are merged into RPC params:
- `debug: true` → `params.debug = 1`
- `log: true` → `params.log = 1`
- `white: "*gateway*"` → `params.white = "*gateway*"`
- `gray: "response.py"` → `params.gray = "response.py"`
- `black: "dispatch"` → `params.black = "dispatch"`
- `debugLimit: 10` → `params['debug-limit'] = 10`

### Debug Data Display

**Automatic Extraction**:
RPC responses automatically extract debug data from MCP content items.

**Debug Table Overlay**:
When debug data is present, a separate overlay window is automatically created:

```typescript
// In processOperationsIncrementally or error handling
if (rawResult.debug && Array.isArray(rawResult.debug.entries) && rawResult.debug.entries.length > 0) {
  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
  handleRPCResponseWithDebug(rawResult, method, params);
}
```

**Debug Overlay Structure**:
- Request section (expanded by default): Tool name and arguments
- Response section (collapsed by default): Response data JSON
- Debug table section (no header): Debug entries table

**Debug Table Format**:
- Columns: Time, Level, Module, File, Function, Message
- Color-coded by module, filename, function
- Timestamps as deltas from first entry

### Debug Helper

**File**: `debug-helper.ts`

Helper function for creating debug overlay windows.

```typescript
import { handleRPCResponseWithDebug } from './debug-helper.js';

handleRPCResponseWithDebug(rpcResult, 'modify_name', { page_id: 123, name: 'New Name' });
```

**Features**:
- Automatically creates overlay with Request/Response/Debug sections
- Handles both success and error responses
- Only creates overlay if debug data has entries

---

## 8. Derived PageData Classes

Derived PageData classes extend the base class to provide page-type-specific field mappings and handlers.

### Factory Pattern

**File**: `page-data-factory.ts`

Factory creates appropriate PageData instance based on page class:

```typescript
const pageData = PageDataFactory.create(getPageResponse);
// Returns: PageData, SourceCodeFilePageData, MCPRequestPageData, MCPActionPageData, WorkDocketPageData
```

**Supported Classes**:
- `source_code_file` → `SourceCodeFilePageData`
- `mcp_request` → `MCPRequestPageData`
- `mcp_action` or `mcp_action_request` → `MCPActionPageData`
- `work_docket` → `WorkDocketPageData`
- Default → `PageData`

### SourceCodeFilePageData

**File**: `source-code-file-page-data.ts`

Handles source code file pages with `file_path` and `language` fields.

**Field Mappings**:
```typescript
{
  fields: ['file_path'],
  mcpTool: 'modify_path',
  priority: 0
},
{
  fields: ['language'],
  mcpTool: 'modify_language',
  priority: 0
}
```

**Handler**: `source_code_file_combo` - Edit text, file_path, and language together

### MCPRequestPageData

**File**: `mcp-request-page-data.ts`

Handles MCP request pages with transaction fields.

**Field Mappings**:
- Group mapping for all transaction fields to `modify_mcp_request`
- Priority 1 (group operation)

### MCPActionPageData

**File**: `mcp-action-page-data.ts`

Handles MCP action request pages.

**Field Mappings**:
- Group mapping for all action fields to `modify_mcp_action_request`
- Priority 1 (group operation)

### WorkDocketPageData

**File**: `work-docket-page-data.ts`

Handles work docket pages with `status`, `meta`, and `sort_order` fields.

**Field Mappings**:
```typescript
{
  fields: ['status'],
  mcpTool: 'modify_status',
  priority: 0
}
```

### Creating New Derived Classes

**Pattern**:
1. Create new file: `{page-class}-page-data.ts`
2. Extend `PageData` base class
3. Override `getFieldMappings()` to add class-specific mappings
4. Add handler methods for class-specific operations
5. Register in `PageDataFactory.create()`

**Example**:
```typescript
import { PageData, GetPageResponse, FieldMapping } from './page-data.js';

export class MyPageData extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings(),  // Include base mappings
      {
        fields: ['my_field'],
        mcpTool: 'modify_my_field',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          my_field: values['my_field']
        })
      }
    ];
  }

  async my_handler(rpc: any): Promise<void> {
    // Handler implementation
  }
}
```

---

## 9. File Upload

The upload handler provides image file upload functionality with progress tracking and sequential processing.

### UploadHandler

**File**: `upload-handler.ts`

Handles image file uploads with multi-file support.

**Usage**:
```typescript
import { UploadHandler } from './upload-handler.js';

const handler = new UploadHandler(rpc, seedData);
await handler.handle();
```

**Features**:
- Multiple file selection
- Upload progress bars
- Sequential processing (upload all, then process one at a time)
- Debug options support
- Success/error messages per file

**Upload Flow**:
1. User selects files (via "Choose Files" button)
2. Files added to overlay with pending status
3. User clicks "Upload"
4. All files upload in parallel (with progress bars)
5. Files convert to "pending processing" state
6. Files process sequentially (one MCP call per file)
7. Success/error messages shown per file
8. Overlay auto-fades and refreshes page on success

**Debug Integration**:
- Debug options captured when "Upload" clicked
- Same debug options applied to all file processing calls
- Debug overlays shown for each file with debug data

---

## 10. Best Practices

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

**Array-Based System** (required):
```typescript
content: [
  '<div>Section 1 HTML</div>',
  '<div>Section 2 HTML</div>',
  someHTMLElement
],
contentHeaders: ['Section 1', 'Section 2', '']  // Empty = no header
```

All content must be provided as an array, even for single items:
```typescript
content: ['Single item content'],
contentHeaders: ['']
```

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

**Standardized Redirect Pattern**:
```typescript
{
  _redirectAfterFade: 'parent'  // Redirect to parent page
  _redirectAfterFade: 'self'    // Refresh current page
  _redirectAfterFade: '/123'     // Redirect to specific URL
  // Omit or null = no redirect, just fade
}
```

**When to Redirect**:
- DELETE: Always redirect to parent
- CREATE: Redirect to new page
- UPDATE: Usually no redirect (DOM updated dynamically)
- Exception: Text updates may refresh page due to processing complexity

### Form Patterns

**Standard Form Structure**:
```html
<div class="overlay-form-section">
  <h3 class="overlay-section-title">Editable Fields:</h3>
  <div class="overlay-form-group">
    <label>Field Label:</label>
    <input type="text" id="page-field-fieldName" class="overlay-form-input">
  </div>
</div>

<div class="overlay-form-divider">
  <h3 class="overlay-section-title">Read-Only Fields:</h3>
  <div class="overlay-form-grid">
    <div><strong>Label:</strong></div>
    <div>Value</div>
  </div>
</div>
```

**Field Cleanup**:
Always clear field registry on cancel/unmount:
```typescript
onCancel: () => {
  pageManager.clearFieldRegistry();
},
onUnmount: () => {
  pageManager.clearFieldRegistry();
}
```

### RPC Call Patterns

**Standard RPC Call**:
```typescript
const result = await rpc.call('tool_name', {
  param1: value1,
  param2: value2
});
// result.data contains response
// result.debug contains debug data if present
```

**With Explicit Debug Options**:
```typescript
const result = await rpc.call('tool_name', params, {
  debug: true,
  log: true,
  gray: 'response.py'
});
```

**Error Handling**:
```typescript
try {
  const result = await rpc.call('tool_name', params);
} catch (error) {
  // error is RPCError with multiple error messages
  // Errors automatically displayed in overlay
  // No need to manually handle display
}
```

---

## Summary

The TypeScript system provides client-side functionality for the Henhouse HTTP interface:

- **Overlay System**: Component-based modal dialogs with array-based content structure
- **PageData Architecture**: Field management and form processing with automatic MCP tool selection
- **RPC Integration**: MCP JSON-RPC wrapper with automatic debug handling
- **Standardized Patterns**: Consistent handler patterns, field registration, and error handling
- **Debug Integration**: Debug system integrated with overlay UI

The system can be extended with new page types and handlers following the patterns documented above.


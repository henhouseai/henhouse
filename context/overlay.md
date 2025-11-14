# Overlay System Architecture - Planning Document

This document outlines the design and implementation plan for a modern TypeScript-based overlay system, modeled after React patterns but built as a lightweight custom framework integrated with the Henhouse MCP/RPC system.

## Table of Contents

1. [Vision & Goals](#vision--goals)
2. [Architecture Overview](#architecture-overview)
3. [Component Hierarchy](#component-hierarchy)
4. [Core Components](#core-components)
5. [Content Components](#content-components)
6. [State Management](#state-management)
7. [Event System](#event-system)
8. [Integration Points](#integration-points)
9. [Implementation Phases](#implementation-phases)
10. [Checklist](#checklist)

---

## Vision & Goals

### Primary Goals

1. **Modern Replacement**: Replace legacy jQuery-based overlay system with TypeScript/ES modules
2. **React-Inspired Design**: Use React patterns (components, props, state, lifecycle) without React framework
3. **Lightweight & Integrated**: Custom framework built specifically for Henhouse MCP/RPC system
4. **Flexible Foundation**: Support multiple use cases (basic modals, image viewer, CRUD forms, browser navigation)
5. **Progressive Enhancement**: Python HTTP backend renders initial HTML, TypeScript enhances with interactivity

### Use Cases

The overlay system must support:

1. **Basic Modals**: Simple content display with submit/cancel
2. **Image Viewer**: Full-screen image viewing with zoom, pan, navigation
3. **CRUD Forms**: Dynamic form generation from field configuration
4. **Browser Navigation**: Hierarchical page/image navigation (target, path, contents, images)
5. **Text Editor**: Rich text editing with browser integration for inserting images
6. **File Upload**: Image upload with progress and validation

### Design Principles

- **Component-Based**: Modular, composable components
- **Declarative**: Describe what you want, framework handles DOM updates
- **Unidirectional Data Flow**: Props down, events up
- **Lifecycle Hooks**: onMount, onUnmount, onSubmit, onError
- **State Isolation**: Each overlay instance manages its own state
- **Event-Driven**: Components communicate via events, not direct callbacks
- **MCP Integration**: Built-in support for MCP/RPC calls

---

## Architecture Overview

### System Boundaries

**TypeScript (Client-Side):**
- All component hierarchy and UI logic
- OverlayManager singleton
- Event system and state management
- DOM manipulation and rendering
- RPC client integration

**Python (Server-Side):**
- HTTP backend renders initial HTML with hooks
- MCP tool handlers (whitelisted routines in gateway)
- Returns JSON data for TypeScript consumption

**Communication Layer:**
- MCP/RPC protocol for data fetching
- JSON-RPC 2.0 format
- `/mcp` HTTP endpoint

### Data Flow

```
Python HTTP Backend
    ↓ (renders HTML with data attributes, IDs, seed data)
TypeScript Framework
    ↓ (attaches event handlers, initializes components)
User Interaction
    ↓ (clicks action link)
Overlay System
    ↓ (shows overlay, calls MCP tool)
Python Gateway
    ↓ (executes MCP tool, returns JSON)
TypeScript Components
    ↓ (updates DOM, manages state)
User Sees Updated UI
```

---

## Component Hierarchy

### High-Level Structure

```
OverlayManager (singleton)
    ├─ Manages overlay instances
    ├─ Handles z-index stacking
    ├─ Manages focus and keyboard shortcuts
    └─ Coordinates event routing
    
Overlay Instance
    ├─ OverlayBackdrop (modal backdrop)
    └─ OverlayWindow (modal container)
        ├─ OverlayHeader (title, buttons)
        ├─ OverlayContent (pluggable content area)
        │   ├─ Browser (hierarchical navigation)
        │   ├─ FormBuilder (dynamic forms)
        │   ├─ ImageViewer (full-screen image)
        │   ├─ TextEditor (rich text editing)
        │   └─ SimpleContent (HTML string/element)
        └─ OverlayFooter (optional)
```

### Component Relationships

- **OverlayManager**: Singleton that creates and manages Overlay instances
- **Overlay**: Base component that handles modal lifecycle
- **Content Components**: Pluggable components that render inside OverlayContent
- **Overlay doesn't know about specific content types** - it just provides container and lifecycle

---

## Core Components

### OverlayManager

**Purpose**: Singleton manager for all overlay instances

**Responsibilities:**
- Create and destroy overlay instances
- Manage z-index stacking (multiple overlays)
- Handle global keyboard shortcuts (ESC to close top overlay)
- Coordinate focus management
- Route events between components

**API:**
```typescript
class OverlayManager {
  static getInstance(): OverlayManager
  show(options: OverlayOptions): Overlay
  close(overlay: Overlay): void
  closeAll(): void
  getTopOverlay(): Overlay | null
  isActive(): boolean
}
```

**State:**
- Array of active overlay instances
- Current z-index counter
- Global event listeners

### Overlay

**Purpose**: Base overlay component (modal window)

**Props:**
```typescript
interface OverlayProps {
  header?: string | HTMLElement
  content?: string | HTMLElement | Component
  footer?: string | HTMLElement
  closable?: boolean
  submitLabel?: string
  cancelLabel?: string
  onMount?: () => void
  onUnmount?: () => void
  onSubmit?: () => Promise<any> | any
  onCancel?: () => void
  onError?: (error: Error) => void
  className?: string
  style?: CSSProperties
}
```

**State:**
```typescript
interface OverlayState {
  isVisible: boolean
  isLoading: boolean
  error: string | null
  success: string | null
  zIndex: number
}
```

**Lifecycle:**
1. **Mount**: Create DOM elements, attach event listeners, call onMount
2. **Render**: Render header, content, footer based on props
3. **Update**: Re-render when props/state change
4. **Unmount**: Remove DOM elements, cleanup, call onUnmount

**Methods:**
- `render()`: Returns DOM structure
- `update(props: Partial<OverlayProps>)`: Update props and re-render
- `setState(updates: Partial<OverlayState>)`: Update state and re-render
- `show()`: Display overlay
- `hide()`: Hide overlay
- `remove()`: Remove overlay completely

### OverlayBackdrop

**Purpose**: Modal backdrop (dark overlay behind window)

**Props:**
- `onClick`: Handler for backdrop click (usually closes overlay)
- `opacity`: Backdrop opacity (default 0.7)

**Behavior:**
- Covers entire viewport
- Blocks interaction with page behind
- Clicking backdrop can close overlay (configurable)

### OverlayWindow

**Purpose**: Modal window container

**Props:**
- `width`: Width (default: auto, max 90%)
- `height`: Height (default: auto, max 90%)
- `position`: Position strategy (center, top, custom)
- `className`: Additional CSS classes
- `style`: Custom styles

**Behavior:**
- Centered by default
- Responsive (max-width/height constraints)
- Scrollable if content overflows
- Focus trap (keeps focus inside modal)

### OverlayHeader

**Purpose**: Header bar with title and action buttons

**Props:**
- `title`: Header text
- `showCancel`: Show cancel button (default: true)
- `showSubmit`: Show submit button (default: true)
- `cancelLabel`: Cancel button text (default: "Cancel")
- `submitLabel`: Submit button text (default: "Submit")
- `onCancel`: Cancel button handler
- `onSubmit`: Submit button handler

**Features:**
- Loading state on submit button (shows spinner)
- Disabled state when loading
- Custom button labels

### OverlayContent

**Purpose**: Container for pluggable content components

**Props:**
- `children`: Content component or HTML
- `className`: Additional CSS classes

**Behavior:**
- Renders whatever component/HTML is passed as children
- Handles scrolling if content overflows
- Provides consistent padding/spacing

### OverlayFooter

**Purpose**: Optional footer area

**Props:**
- `children`: Footer content
- `className`: Additional CSS classes

---

## Content Components

### Browser

**Purpose**: Hierarchical page/image navigation component

**Props:**
```typescript
interface BrowserProps {
  id: number | string  // Page or image ID
  onNavigate?: (id: number | string) => void
  onSelect?: (id: number | string) => void
  showTarget?: boolean
  showPath?: boolean
  showContents?: boolean
  showImages?: boolean
  imageClickable?: boolean
}
```

**State:**
```typescript
interface BrowserState {
  target: Page | Image | null
  path: Page[]
  contents: Page[]
  images: Image[]
  loading: boolean
  error: string | null
}
```

**Sections:**
1. **Target**: Current page/image being viewed (with image/name)
2. **Path**: Breadcrumb navigation (clickable path)
3. **Contents**: Child pages (tile grid, clickable)
4. **Images**: Images on current page (tile grid, clickable)

**Data Fetching:**
- Calls MCP tool `get_browser` with page/image ID
- Receives JSON with target, path, contents, images
- Renders tiles using Tile component

**Interactions:**
- Clicking path item navigates to that page
- Clicking content item navigates to that page
- Clicking image selects it (if imageClickable) or navigates

### FormBuilder

**Purpose**: Dynamic form generation from field configuration

**Props:**
```typescript
interface FormBuilderProps {
  fields: FieldConfig[]
  initialValues?: Record<string, any>
  onSubmit?: (values: Record<string, any>) => Promise<any> | any
  onFieldChange?: (field: string, value: any) => void
}
```

**Field Types:**
- `text`: Text input
- `textarea`: Multi-line text
- `select`: Dropdown
- `checkbox`: Checkbox
- `radio`: Radio buttons
- `browser`: Browser component for page/image selection
- `link`: Multi-link selector (class + link dropdowns)

**Field Configuration:**
```typescript
interface FieldConfig {
  name: string
  label: string
  type: 'text' | 'textarea' | 'select' | 'checkbox' | 'radio' | 'browser' | 'link'
  required?: boolean
  defaultValue?: any
  options?: SelectOption[]  // For select/radio
  validation?: (value: any) => string | null
  dataType?: 'int' | 'float' | 'currency' | 'varchar' | 'link'
  inputType?: 'input' | 'select' | 'browser'
}
```

**Features:**
- Automatic form validation
- Field-level error display
- Loading states during submission
- Success/error message display

### ImageViewer

**Purpose**: Full-screen image viewing with controls

**Props:**
```typescript
interface ImageViewerProps {
  imageId: number | string
  images?: Image[]  // For navigation between images
  onEdit?: () => void
  onDelete?: () => void
  onOptions?: () => void
  onClose?: () => void
}
```

**State:**
```typescript
interface ImageViewerState {
  currentImage: Image | null
  currentIndex: number
  scale: number
  position: { x: number; y: number }
  loading: boolean
}
```

**Features:**
- Zoom (mouse wheel, pinch gesture)
- Pan (drag, touch)
- Navigation (previous/next image)
- Keyboard shortcuts (arrows, ESC, E for edit, D for delete)
- Image controls (edit, delete, options, close)
- Responsive sizing (fits viewport)

**Interactions:**
- Mouse wheel: Zoom in/out
- Drag: Pan when zoomed
- Touch gestures: Pinch to zoom, swipe to navigate
- Keyboard: Arrow keys, ESC, letter shortcuts

### TextEditor

**Purpose**: Rich text editing with browser integration

**Props:**
```typescript
interface TextEditorProps {
  pageId: number | string
  initialText?: string
  onSubmit?: (text: string) => Promise<any> | any
  showBrowser?: boolean
  browserId?: number | string
}
```

**State:**
```typescript
interface TextEditorState {
  text: string
  loading: boolean
  browserVisible: boolean
}
```

**Features:**
- Large textarea for editing
- Browser component for inserting image references
- Auto-resize textarea
- Loading state when fetching initial text
- Insert image syntax (e.g., `{{{{123}}}}`)

### SimpleContent

**Purpose**: Render HTML string or element

**Props:**
```typescript
interface SimpleContentProps {
  content: string | HTMLElement
  className?: string
}
```

**Behavior:**
- If string: Sets innerHTML
- If element: Appends element
- Provides consistent styling container

---

## State Management

### Component State

Each component manages its own local state:
- Overlay: visibility, loading, error, success
- Browser: target, path, contents, images
- FormBuilder: field values, validation errors
- ImageViewer: current image, scale, position

### State Updates

**Pattern:**
```typescript
// Component calls setState
this.setState({ loading: true })

// Component re-renders affected parts
this.render()
```

**Re-render Strategy:**
- Only re-render changed parts (not full DOM replacement)
- Use document fragments for batch updates
- Track what changed to minimize DOM operations

### Shared State (if needed)

For cross-component state:
- Small state store (similar to React Context)
- Event bus for communication
- Or pass state down as props

---

## Event System

### Event Types

**Lifecycle Events:**
- `mount`: Component mounted
- `unmount`: Component unmounting
- `update`: Component updated

**User Interaction Events:**
- `submit`: Form/overlay submitted
- `cancel`: Overlay cancelled
- `navigate`: Browser navigation
- `select`: Item selected
- `error`: Error occurred

**Custom Events:**
- Components can emit custom events
- OverlayManager routes events to handlers

### Event Flow

```
User Action
    ↓
Component emits event
    ↓
OverlayManager receives event
    ↓
Routes to appropriate handler
    ↓
Handler updates state or calls MCP
    ↓
Component re-renders with new state
```

### Event Handler Pattern

```typescript
// Component emits event
this.emit('submit', { values: formData })

// OverlayManager handles event
overlayManager.on('submit', async (data) => {
  const result = await rpc.call('modify_page', data)
  overlay.setState({ success: 'Updated!' })
})
```

---

## Integration Points

### MCP/RPC Integration

**RPC Client Usage:**
- All components have access to RPCClient instance
- Components call MCP tools via RPC client
- Results flow back as props or state updates

**Common MCP Tools:**
- `get_browser`: Get browser data (target, path, contents, images)
- `get_page`: Get page data
- `modify_page`: Update page
- `add_page`: Create page
- `delete_page`: Delete page
- `modify_text`: Update page text
- `get_image`: Get image data
- `modify_caption`: Update image caption
- And more...

**Error Handling:**
- RPC errors caught by components
- Displayed in overlay error area
- Components can retry or handle gracefully

### Python HTTP Backend Integration

**Initial HTML Structure:**
- Python renders HTML with data attributes
- Example: `<button data-action="edit-page" data-page-id="123">`
- TypeScript attaches handlers based on data attributes

**Seed Data:**
- Python includes seed data in JSON script tag
- TypeScript reads seed data on page load
- Used for initial page ID, user info, etc.

**Action Links:**
- Python renders action links with specific IDs/classes
- TypeScript finds and attaches overlay handlers
- Example: `id="edit-page-123"` → attaches edit handler

---

## Implementation Phases

### Phase 1: Core Foundation

**Goal**: Basic overlay system working

**Tasks:**
1. Create OverlayManager singleton
2. Create base Overlay component
3. Create OverlayBackdrop component
4. Create OverlayWindow component
5. Create OverlayHeader component
6. Create OverlayContent component
7. Basic show/hide functionality
8. Keyboard shortcuts (ESC, Enter)
9. Focus management
10. Z-index stacking

**Deliverable**: Can show/hide simple overlay with header and content

### Phase 2: Simple Content

**Goal**: Display simple HTML content in overlay

**Tasks:**
1. Create SimpleContent component
2. Support HTML string rendering
3. Support HTMLElement rendering
4. Basic styling and layout

**Deliverable**: Can show overlay with custom HTML content

### Phase 3: Browser Component

**Goal**: Hierarchical navigation working

**Tasks:**
1. Create Browser component
2. Implement target section (page/image display)
3. Implement path section (breadcrumb navigation)
4. Implement contents section (child pages grid)
5. Implement images section (images grid)
6. Tile component for page/image display
7. Navigation event handling
8. MCP integration (`get_browser` tool)
9. Loading states
10. Error handling

**Deliverable**: Can navigate pages/images in browser overlay

### Phase 4: Form Builder

**Goal**: Dynamic form generation working

**Tasks:**
1. Create FormBuilder component
2. Implement field rendering (text, textarea, select, etc.)
3. Implement field validation
4. Implement link field type (multi-select with classes)
5. Implement browser field type (page/image picker)
6. Form state management
7. Submit handling
8. Error display
9. Success handling

**Deliverable**: Can generate and submit forms dynamically

### Phase 5: Image Viewer

**Goal**: Full-screen image viewing working

**Tasks:**
1. Create ImageViewer component
2. Implement image display and sizing
3. Implement zoom (mouse wheel)
4. Implement pan (drag)
5. Implement touch gestures (pinch, swipe)
6. Implement navigation (previous/next)
7. Implement keyboard shortcuts
8. Image controls (edit, delete, options)
9. MCP integration (`get_image` tool)
10. Responsive sizing

**Deliverable**: Can view images full-screen with zoom/pan/navigation

### Phase 6: Text Editor

**Goal**: Rich text editing with browser integration

**Tasks:**
1. Create TextEditor component
2. Large textarea with auto-resize
3. Browser integration for image insertion
4. Insert image syntax handling
5. Loading initial text
6. Submit handling
7. MCP integration (`get_text`, `modify_text` tools)

**Deliverable**: Can edit page text with image insertion

### Phase 7: Integration & Polish

**Goal**: Full integration with existing system

**Tasks:**
1. Replace legacy overlay calls with new system
2. Update Python HTTP backend to render action links
3. Add data attributes for TypeScript attachment
4. Test all use cases
5. Error handling improvements
6. Loading state improvements
7. Animation/transitions
8. Accessibility improvements
9. Documentation

**Deliverable**: Fully functional overlay system replacing legacy code

---

## Checklist

### Phase 1: Core Foundation

**Goal**: Basic overlay system working - can show/hide simple overlay

- [ ] Create `overlay/` directory structure
- [ ] Implement OverlayManager singleton class
  - [ ] Static `getInstance()` method
  - [ ] `show(options)` method
  - [ ] `close(overlay)` method
  - [ ] `closeAll()` method
  - [ ] `getTopOverlay()` method
  - [ ] Active overlays array management
  - [ ] Z-index counter management
- [ ] Create base Overlay class
  - [ ] Props interface (OverlayProps)
  - [ ] State interface (OverlayState)
  - [ ] Constructor with props
  - [ ] `render()` method
  - [ ] `mount(parent)` method
  - [ ] `unmount()` method
  - [ ] `update(props)` method
  - [ ] `setState(updates)` method
  - [ ] `show()` method
  - [ ] `hide()` method
  - [ ] `remove()` method
- [ ] Implement OverlayBackdrop component
  - [ ] Create backdrop element
  - [ ] Styling (position, size, opacity)
  - [ ] Click handler (close on backdrop click)
- [ ] Implement OverlayWindow component
  - [ ] Create window element
  - [ ] Styling (position, size, centering)
  - [ ] Responsive constraints (max-width/height)
  - [ ] Scroll handling
- [ ] Implement OverlayHeader component
  - [ ] Header element with title
  - [ ] Cancel button
  - [ ] Submit button
  - [ ] Button styling and handlers
- [ ] Implement OverlayContent component
  - [ ] Content container element
  - [ ] Support for HTML string
  - [ ] Support for HTMLElement
  - [ ] Padding and spacing
- [ ] Implement keyboard shortcuts
  - [ ] ESC key closes overlay
  - [ ] Enter key triggers submit (when not in textarea)
  - [ ] Event listener management
- [ ] Implement focus management
  - [ ] Focus trap (keep focus inside modal)
  - [ ] Focus first focusable element on show
  - [ ] Restore focus on close
- [ ] Implement z-index stacking
  - [ ] Increment z-index for each overlay
  - [ ] Top overlay receives keyboard events
- [ ] Create CSS file `overlay.css`
  - [ ] Backdrop styles
  - [ ] Window styles
  - [ ] Header styles
  - [ ] Content styles
  - [ ] Button styles
  - [ ] Loading/error/success message styles
- [ ] Create `index.ts` export file
  - [ ] Export OverlayManager
  - [ ] Export Overlay
  - [ ] Export component types
- [ ] Test Phase 1 functionality
  - [ ] Can show overlay
  - [ ] Can hide overlay
  - [ ] ESC closes overlay
  - [ ] Enter triggers submit
  - [ ] Focus trap works
  - [ ] Multiple overlays stack correctly

### Phase 2: Simple Content

**Goal**: Display simple HTML content in overlay

- [ ] Create SimpleContent component class
  - [ ] Props interface (SimpleContentProps)
  - [ ] `render()` method
  - [ ] Handle HTML string (innerHTML)
  - [ ] Handle HTMLElement (append)
- [ ] Integrate SimpleContent with Overlay
  - [ ] Pass SimpleContent as content prop
  - [ ] Render in OverlayContent
- [ ] Test Phase 2 functionality
  - [ ] Can show overlay with HTML string
  - [ ] Can show overlay with HTMLElement
  - [ ] Content renders correctly
  - [ ] Styling applied correctly

### Phase 3: Browser Component

**Goal**: Hierarchical page/image navigation working

*Note: Detailed implementation will be planned after Phases 1-2 are complete and tested*

- [ ] Create Browser component class
- [ ] Implement browser sections (target, path, contents, images)
- [ ] Create Tile component for page/image display
- [ ] Implement navigation and selection
- [ ] Integrate with MCP `get_browser` tool
- [ ] Add loading and error states
- [ ] Test browser navigation

### Phase 4: Form Builder

**Goal**: Dynamic form generation working

*Note: Detailed implementation will be planned after Phases 1-2 are complete and tested*

- [ ] Create FormBuilder component class
- [ ] Implement field types (text, textarea, select, checkbox, radio, browser, link)
- [ ] Implement form validation
- [ ] Implement form state management
- [ ] Implement submit handling
- [ ] Test form generation and submission

### Phase 5: Image Viewer

**Goal**: Full-screen image viewing working

*Note: Detailed implementation will be planned after Phases 1-2 are complete and tested*

- [ ] Create ImageViewer component class
- [ ] Implement image display and sizing
- [ ] Implement zoom and pan
- [ ] Implement touch gestures
- [ ] Implement keyboard navigation
- [ ] Integrate with MCP `get_image` tool
- [ ] Test image viewer functionality

### Phase 6: Text Editor

**Goal**: Rich text editing with browser integration

*Note: Detailed implementation will be planned after Phases 1-2 are complete and tested*

- [ ] Create TextEditor component class
- [ ] Implement textarea with auto-resize
- [ ] Integrate Browser component for image insertion
- [ ] Implement image syntax insertion
- [ ] Integrate with MCP `get_text` and `modify_text` tools
- [ ] Test text editing with image insertion

### Phase 7: Integration & Polish

**Goal**: Full integration with existing system

*Note: Detailed tasks will be determined based on Phases 1-2 implementation*

- [ ] Update app.ts to use new overlay system
- [ ] Replace legacy overlay calls
- [ ] Update Python HTTP backend for action links
- [ ] Add TypeScript handlers for action links
- [ ] End-to-end testing
- [ ] Error handling improvements
- [ ] Loading state improvements
- [ ] Animations/transitions
- [ ] Accessibility improvements
- [ ] Documentation

### MCP Tools (Python Side)

*Note: Verify/implement as needed for each phase*

- [ ] Phase 1-2: No MCP tools needed (simple content only)
- [ ] Phase 3: Verify `get_browser` MCP tool exists
- [ ] Phase 4: Verify form-related MCP tools exist
- [ ] Phase 5: Verify `get_image` MCP tool exists
- [ ] Phase 6: Verify `get_text` and `modify_text` MCP tools exist
- [ ] Add any missing MCP tools as needed

---

## Technical Details

### File Structure

**TypeScript Modules (split into separate files, not monolithic):**

```
hh/deploy/site/ts/
  ├─ overlay/
  │   ├─ overlay-manager.ts      # OverlayManager singleton
  │   ├─ overlay.ts               # Base Overlay class
  │   ├─ overlay-backdrop.ts      # OverlayBackdrop component
  │   ├─ overlay-window.ts        # OverlayWindow component
  │   ├─ overlay-header.ts        # OverlayHeader component
  │   ├─ overlay-content.ts       # OverlayContent component
  │   └─ index.ts                 # Exports (public API)
  ├─ browser.ts                   # Browser component (Phase 3)
  ├─ form-builder.ts              # FormBuilder component (Phase 4)
  ├─ image-viewer.ts              # ImageViewer component (Phase 5)
  ├─ text-editor.ts               # TextEditor component (Phase 6)
  ├─ tile.ts                      # Tile component (for page/image display)
  ├─ app.ts                       # Main app (updated to use overlay system)
  ├─ rpc-client.ts                # RPC client (already exists)
  └─ seed.ts                      # Seed data (already exists)
```

**CSS Files (layout separated from colors, multiple files for different tiers):**

```
hh/deploy/site/css/
  ├─ overlay.css                  # Base layout/structure (from legacy overlay.css)
  ├─ overlay-colors-guest.css     # Tier 1 (guest) color scheme
  ├─ overlay-colors-verified.css # Tier 2 (verified) color scheme
  ├─ overlay-colors-admin.css    # Tier 3 (admin) color scheme
  └─ overlay-colors-root.css     # Tier 4 (root) color scheme
```

### Architecture Decisions

**Component Pattern:**
- **Class-based components** (not functional)
- Each component is a class with methods: `render()`, `mount()`, `unmount()`, `setState()`, etc.

**Rendering Strategy:**
- `render()` method returns HTMLElement
- Caller appends returned element to DOM
- On updates: replace old element with new element (full re-render for Phase 1)
- Can optimize to diff/update later if needed

**RPC Client Access:**
- RPCClient passed to OverlayManager constructor
- Components access RPCClient via OverlayManager (centralized access)
- Keeps RPC client centralized and testable

**CSS Approach:**
- Separate CSS files (no CSS-in-JavaScript)
- Base layout in `overlay.css` (based on legacy overlay.css)
- Color schemes separated into tier-specific files
- Inline styles only for dynamic properties (position, z-index)
- CSS classes for static styling

### TypeScript Types

**Core Types:**
```typescript
interface OverlayOptions {
  header?: string | HTMLElement
  content?: string | HTMLElement | Component
  footer?: string | HTMLElement
  closable?: boolean
  submitLabel?: string
  cancelLabel?: string
  onMount?: () => void
  onUnmount?: () => void
  onSubmit?: () => Promise<any> | any
  onCancel?: () => void
  onError?: (error: Error) => void
  className?: string
  style?: CSSProperties
}

interface Component {
  render(): HTMLElement
  mount(parent: HTMLElement): void
  unmount(): void
  update?(props: any): void
}
```

### CSS Styling

**CSS Structure (based on legacy overlay.css):**

**Base Layout (`overlay.css`):**
- Layout and structure styles
- Uses CSS variables for colors (allows color separation)
- Key elements:
  - `#overlay` - Backdrop (fixed position, full viewport, opacity)
  - `#overlayWindow` - Modal window (positioned, border, padding)
  - `.overlayHeader` - Header bar (title, buttons)
  - `.overlayContent` - Content area (padding, border, background)
  - `.overlaySuccess`, `.overlayError`, `.overlayWarning` - Message styles
  - Button styles (`.submitButton`, `.cancelButton`, `.grayLink`)
  - Input/select/textarea styles
  - Browser-specific styles (`.browser`, `.overlayTileList`)
  - Group editor table styles

**Color Files (tier-specific):**
- Define CSS variable values for each tier
- Variables used in base layout:
  - `--overlay-window` - Window background
  - `--overlay-window-border` - Window border
  - `--overlay-header-text` - Header text color
  - `--overlay-header-link` - Link button background
  - `--overlay-header-link-text` - Link button text
  - `--overlay-header-link-hover` - Link button hover
  - `--overlay-header-submit-button` - Submit button colors
  - `--overlay-header-cancel-button` - Cancel button colors
  - `--overlay-content` - Content background
  - `--overlay-content-text` - Content text color
  - `--overlay-success`, `--overlay-error`, `--overlay-warning` - Message colors
  - And more...

**Styling Approach:**
- Inline styles for dynamic properties (position, z-index, display)
- CSS classes for static styling
- CSS variables for colors (allows tier-specific color files)
- Layout in base file, colors in separate tier files

### Performance Considerations

- **Minimal DOM Manipulation**: Only update changed parts
- **Event Delegation**: Use event delegation where possible
- **Lazy Loading**: Load browser/form data only when needed
- **Debouncing**: Debounce rapid events (scroll, resize)
- **Memory Management**: Clean up event listeners on unmount

### Accessibility

- **ARIA Labels**: Proper ARIA attributes for screen readers
- **Focus Management**: Focus trap in modal, restore focus on close
- **Keyboard Navigation**: Full keyboard support
- **Semantic HTML**: Use proper HTML elements (button, form, etc.)

---

## Future Enhancements

### Potential Additions

1. **Animation System**: Smooth transitions for show/hide
2. **Drag to Resize**: Resizable overlay windows
3. **Multiple Overlays**: Stack multiple overlays (nested modals)
4. **Overlay Templates**: Pre-built templates for common use cases
5. **Form Validation Library**: More advanced validation
6. **Rich Text Editor**: WYSIWYG editor integration
7. **File Upload Component**: Drag-and-drop file upload
8. **Toast Notifications**: Non-modal notifications
9. **Confirmation Dialogs**: Reusable confirmation component
10. **Progress Indicators**: Better loading/progress feedback

---

This document serves as the planning foundation and implementation roadmap for the overlay system. Update as implementation progresses and decisions are made.


# Image Group Viewer System Architecture

This document covers the implementation of the image viewer overlay system, a full-screen image viewer with pan/zoom support that opens when clicking images in a page's image group. The viewer is a read-only interface for viewing images with advanced zoom and pan controls.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Legacy System Reference](#2-legacy-system-reference)
3. [Architecture Design](#3-architecture-design)
4. [Backend Implementation](#4-backend-implementation)
5. [Frontend Implementation](#5-frontend-implementation)
6. [Integration Points](#6-integration-points)

## Agent Quick Reference

- **Core Concept**: Image viewer is a custom overlay that displays images with pan/zoom capabilities
- **MCP Tool**: `get_image_group` - returns JSON data for all images in a page's image group
- **TypeScript Class**: `ImageViewer` - manages viewer state, pan/zoom, and navigation
- **Library**: `interact.js` - handles gesture-based pan/zoom interactions
- **Link Interception**: Images in page image groups (both table and tile views) open the viewer
- **Zoom States**: Special points control panning behavior (centered → X-only → X+Y)
- **Read-Only**: No editing, deleting, or caption modification (viewer only)

## Agent Training Notes

### Current State
- Image groups display images in table or tile views
- View toggle system works for hot-swapping views
- Overlay system supports z-stacking
- No image viewer exists yet

### Goal
- Enable full-screen image viewing with pan/zoom
- Support keyboard navigation (arrow keys, Esc)
- Support touch gestures (swipe for navigation, pinch-to-zoom)
- Support mouse wheel zoom
- Maintain read-only interface (no editing capabilities)
- Integrate with existing image group links

### Design Principles
- **Read-Only Viewer**: No editing, deleting, or caption modification
- **JSON Data Source**: Backend returns JSON, not HTML (for flexibility)
- **Custom Overlay**: Extends overlay system similar to `ImageGroupSorter`
- **Library Integration**: Uses `interact.js` for pan/zoom gestures
- **Instance Selection**: Automatically selects best image size for display
- **Preloading**: Loads full-size images on zoom start
- **State-Based Panning**: Panning constraints change based on zoom level
- **Overlay Scaling**: Overlay window scales with image zoom

---

## 1. System Overview

The image viewer system provides a full-screen viewing experience for images in a page's image group. Users can click any image link (in either table or tile view) to open the viewer, which displays the image with pan/zoom capabilities. The viewer supports keyboard navigation, touch gestures, and mouse wheel zooming.

### Architecture Flow

1. **Image Link Click**: User clicks an image link in the page's image group (table or tile view)
2. **Link Interception**: `view-toggle.ts` intercepts the click and calls `ImageViewer.openFromImageLink()`
3. **Data Loading**: Viewer calls `get_image_group` MCP tool to fetch all images and instances
4. **Overlay Creation**: Viewer creates a custom overlay with the clicked image displayed
5. **Interaction Setup**: Viewer sets up `interact.js` for pan/zoom, keyboard handlers, and touch handlers
6. **Navigation**: User can navigate between images using arrow keys, swipe gestures, or control links
7. **Zoom/Pan**: User can zoom with mouse wheel or pinch gestures, pan by dragging (with state-based constraints)

### Key Components

- **`get_image_group` Action**: Backend action that returns JSON data for all images in a page's image group
- **`ImageViewer` Class**: TypeScript class managing viewer state, pan/zoom, and navigation
- **`interact.js` Library**: JavaScript library for handling pan/zoom gestures
- **Overlay Link Helpers**: Generalized link interception utilities (shared with browser system)
- **CSS Styling**: Layout styles in `image-viewer.css`, color styles in tier-specific CSS files

---

## 2. Legacy System Reference

### Legacy Files to Review

**JavaScript Files:**
- `legacy/core/js/image.js` - Original image viewer implementation
  - XML-based data loading (we use JSON instead)
  - Pan/zoom with `interact.js`
  - Touch gesture handlers for swipe navigation
  - Keyboard shortcuts (Esc, Left/Right arrows)
  - Image instance selection logic
  - Caption editing and deletion (removed in new version)

**CSS Files:**
- `legacy/core/css/image.css` - Original image viewer styles
  - Layout styles ported to `image-viewer.css`
  - Color styles ported to tier-specific CSS files (using CSS variables)
  - Overlay positioning and sizing
  - Image container and zoom container styles

**PHP Files:**
- `legacy/core/php/Image.php` - Image data retrieval
  - Instance selection logic
  - Image metadata (caption, visibility, view count)

### Key Differences from Legacy

1. **Data Format**: Legacy used XML (`getImageViewerXML` action), new version uses JSON via `get_image_group` (see `legacy/core/js/image.js` lines 83, 107-136)
2. **No Editing**: Legacy had caption editing, deletion, and options (lines 279-281, 490-578), new version is read-only
3. **TypeScript**: New version is TypeScript, legacy was JavaScript with jQuery
4. **Overlay System**: New version uses modern overlay system with z-stacking; legacy manually created divs (lines 78, 213-218)
5. **Link Interception**: New version uses generalized overlay link helpers; legacy used jQuery selectors (lines 14-18)
6. **CSS Variables**: New version uses CSS variables for tier-specific colors
7. **Panning System**: Legacy used simple boundary constraints with interact.js `restrict` modifier (lines 260-264, 422-451); new version uses state-based panning with special points that change behavior (centered → X-only → X+Y)
8. **Overlay Scaling**: Legacy kept overlay size fixed; new version scales overlay window with zoom level (see `updateOverlaySize()` method)
9. **Full-Size Image Loading**: Legacy loaded `instances[0]` (first instance) on zoom start (line 338); new version loads `instances[instances.length - 1]` (largest instance)
10. **Instance Selection**: Legacy looped backwards through instances (lines 157-166); new version loops forwards (finds first >= targetWidth, or uses largest)
11. **Special Point Snapping**: New version snaps to center when zooming out past special points; legacy had no snapping behavior

---

## 3. Architecture Design

### Custom Overlay Pattern

The image viewer follows the same pattern as `ImageGroupSorter` - it's a custom overlay that extends the base overlay system. The viewer:

- Creates a single overlay instance that persists across image navigation
- Updates overlay content instead of creating new overlays
- Manages its own state (current image index, zoom level, pan position)
- Handles cleanup on close (removes event listeners, unbinds interact.js)

### Data Flow

1. **Initial Load**: `get_image_group` returns JSON with all images and their instances
2. **Instance Selection**: Viewer selects best instance based on target dimensions
3. **Display**: Viewer renders image with calculated dimensions
4. **Zoom Start**: Viewer loads full-size instance when zoom begins
5. **Pan/Zoom**: `interact.js` handles gestures, viewer applies constraints
6. **Navigation**: Viewer updates overlay content for next/previous image

### Zoom State System

The viewer implements a state-based panning system with three distinct zoom modes and two transition points (inflection points). Panning behavior changes at each transition, creating smooth zooming with appropriate constraints.

#### Default/Normal Mode (State 1: scale ≤ 1.0 to first inflection)

- **Visual State**: Entire image visible with border around it, overlay mask visible, page behind visible through gray backdrop
- **Panning**: Locked to center on both X and Y axes - no panning allowed
- **Behavior**: Image stays perfectly centered as it grows during zoom in
- **Transition**: Continues until the first edge of the image touches the edge of the browser window (or screen if fullscreen)
- **Starting State**: Always begins in this mode when viewer opens or when navigating to a new image

#### Between Inflections (State 2: first inflection to second inflection)

- **Visual State**: First axis (width or height, whichever touched first) now fills window edge-to-edge, other axis still has border
- **Panning**: 
  - First axis (that touched edge): X or Y panning enabled (whichever axis touched first)
  - Other axis: Still locked to center
- **Behavior**: Can pan side-to-side (or up-down) on the axis that touched first, but only to expose the full image - never past the image edges
- **Transition**: Continues until the second set of edges touches the window edges
- **Constraint**: Panning only allowed insofar as to expose the entirety of the image, but nothing past that

#### Deep Zoom Mode (State 3: after second inflection)

- **Visual State**: Image completely fills entire browser window/screen, clipped on both axes
- **Panning**: Both X and Y panning enabled
- **Behavior**: Can pan in both directions, but constrained so image edges never go past viewport edges
- **Constraint**: Always have image in screen - no background or container window exposed (unless image can't reach this state due to pixel size limitations)
- **Max Zoom**: Hard limit at 3-4x pixel size (prevents forcing into deep zoom if image/window size doesn't accommodate)

#### Transition Behavior

- **Zooming In**: Smoothly transitions through states, enabling panning on appropriate axes at each inflection point
- **Zooming Out**: Honors all panning limits and smoothly transitions back to default state
- **Snapping**: When zooming out past inflection points, viewer snaps to center on the axis that becomes locked
- **Hard Limits**: 
  - Default state is always the starting point (fully zoomed out)
  - Max zoom is hard limit (3-4x pixel size) - never force deep zoom if image/window can't accommodate

**Legacy Comparison**: Legacy system (see `legacy/core/js/image.js` lines 422-451) used simple boundary constraints - panning was always enabled when zoomed, with interact.js `restrict` modifier keeping image within parent container. No state-based behavior, no inflection points, no axis-specific panning locks.

### Overlay Scaling

The overlay window scales with the image zoom level. When the user zooms in, the overlay grows to accommodate the larger image, spilling past screen edges and getting clipped. This provides a more immersive viewing experience.

**Legacy Comparison**: Legacy system (see `legacy/core/js/image.js` line 234) kept overlay size fixed - only the image inside scaled, not the overlay window itself.

---

## 4. Backend Implementation

### `get_image_group` Action

**File**: `hh/page/get_image_group.py`

**Purpose**: Returns JSON data for all images in a page's image group, including all instances sorted by width.

**Parameters**:
- `id` or `page_id` (required): The page ID to get images from

**Response Format**:
```json
{
  "page_id": 123,
  "images": [
    {
      "id": 456,
      "caption": "Image caption",
      "visibility": 1,
      "viewCount": 42,
      "instances": [
        {
          "width": 300,
          "height": 200,
          "filesize": 12345,
          "src": "path/to/image_300x200.jpg"
        },
        // ... more instances sorted by width (ascending)
      ]
    }
  ]
}
```

**Implementation Details**:
- Uses `page.get_images_data()` to fetch image data
- Transforms instances to viewer format (width, height, filesize, src)
- Sorts instances by width (ascending) - smallest first
- Returns JSON payload via `success_payload()`

**Parser**:
- Custom parser displays full JSON structure in CLI table
- Useful for debugging and verification
- Shows page ID, number of images, and complete JSON data

**MCP Registration**:
- Registered as MCP tool (tiers 1-4, read-only)
- Can be called via MCP protocol or HTTP backend

---

## 5. Frontend Implementation

### TypeScript Class: `ImageViewer`

**File**: `hh/deploy/site/ts/image-viewer.ts`

**Key Methods**:

- **`show()`**: Initializes viewer, loads data, and displays overlay
- **`loadAndRender()`**: Fetches image data and renders overlay
- **`renderOrUpdateOverlay()`**: Creates or updates overlay with current image
- **`getBestInstance()`**: Selects best image instance based on target dimensions (loops forwards, finds first >= targetWidth or uses largest). Legacy version (lines 31-47) looped backwards through instances.
- **`calculateDisplayDimensions()`**: Calculates display size for image
- **`setupInteract()`**: Configures `interact.js` for pan/zoom
- **`onGestureStart/Move/End()`**: Handles pinch-to-zoom gestures
- **`onDragStart/Move/End()`**: Handles drag-based panning
- **`handleWheelZoom()`**: Handles mouse wheel zooming
- **`navigateImage()`**: Navigates to next/previous image
- **`getZoomState()`**: Determines current zoom state
- **`applyPanConstraints()`**: Applies panning constraints based on zoom state
- **`updateOverlaySize()`**: Updates overlay dimensions based on zoom level

**State Management**:
- `currentImageIndex`: Current image in the group
- `currentScale`: Current zoom level
- `panX`, `panY`: Current pan position
- `scaleForWidthMatch`, `scaleForHeightMatch`: Special point scales
- `baseImageWidth`, `baseImageHeight`: Base image dimensions
- `baseOverlayWidth`, `baseOverlayHeight`: Base overlay dimensions

**Event Handlers**:
- Keyboard: Esc (close), Left/Right arrows (navigate)
- Touch: Swipe left/right (navigate), pinch-to-zoom
- Mouse: Wheel zoom, drag to pan

### Link Interception

**File**: `hh/deploy/site/ts/view-toggle.ts`

The viewer integrates with the view toggle system to intercept image links:

- `setupImageViewerLinks()`: Sets up link interception for image group
- Called on initial page load and after view swaps
- Uses `interceptLinks()` helper from `overlay-link-helpers.ts`
- Opens viewer with clicked image ID

**Integration Point**:
- `view-toggle.ts` calls `setupImageViewerLinks()` after image section view swaps
- Only intercepts links on main page (not in overlays)
- Uses `__imageViewerIntercepted` marker to avoid duplicate handlers

### Overlay Link Helpers

**File**: `hh/deploy/site/ts/overlay/overlay-link-helpers.ts`

The viewer uses the generalized overlay link helpers (shared with browser system):

- `interceptLinks()`: Scans container for links and intercepts them
- Supports page, image, and file link patterns
- Custom matchers and handlers for special cases
- Marker property to prevent duplicate interception

**Usage in Viewer**:
- Viewer doesn't directly use link helpers (handled by view-toggle)
- But the same infrastructure is used for browser and other overlays

### CSS Styling

**Layout Styles**: `hh/deploy/site/css/image-viewer.css`

- `#imageViewerOverlayWindow`: Overlay window container
- `#imageViewerTargetImageWrapper`: Image wrapper with border
- `#imageZoomContainer`: Zoom container with pan/zoom transforms
- `#imageViewerTargetImage`: Actual image element
- `#imageViewerCaption`: Caption display
- `#imageViewerVisibility`: Visibility label
- `#imageViewerControlLinks`: Navigation and close links

**Color Styles**: Tier-specific CSS files

- `site-guest.css`, `site-verified.css`, `site-admin.css`, `site-root.css`
- CSS variables: `--image-viewer-border`, `--image-viewer-text`, `--image-viewer`, `--image-viewer-link-text`
- Mapped to existing semantic color variables

### interact.js Integration

**Library**: `hh/deploy/site/js/interact.min.js`

**Usage**:
- Imported as side-effect (adds to `window.interact`)
- Used for gesture-based pan/zoom
- Configured with `gesturable()` for pinch-to-zoom
- Configured with `draggable()` for panning
- Inertia disabled for precise control

**Configuration**:
```typescript
this.interactInstance = interact(zoomContainer)
  .gesturable({
    listeners: {
      start: (event) => this.onGestureStart(event),
      move: (event) => this.onGestureMove(event),
      end: (event) => this.onGestureEnd(event)
    }
  })
  .draggable({
    inertia: false,
    listeners: {
      start: (event) => this.onDragStart(event),
      move: (event) => this.onDragMove(event),
      end: (event) => this.onDragEnd(event)
    }
  });
```

---

## 6. Integration Points

### View Toggle System

**File**: `hh/deploy/site/ts/view-toggle.ts`

- Calls `setupImageViewerLinks()` after image section view swaps
- Ensures image links are intercepted in both table and tile views
- Only sets up links on main page (not in overlays)

### Overlay System

**File**: `hh/deploy/site/ts/overlay/overlay.ts`

- Viewer extends overlay system
- Uses `OverlayManager` to create and manage overlay
- Updates existing overlay instead of creating new ones
- Handles cleanup on close

### RPC Client

**File**: `hh/deploy/site/ts/rpc-client.ts`

- Viewer uses `RPCClient` to call `get_image_group` MCP tool
- Handles debug options and error extraction
- Returns JSON data for viewer processing

### Image Group Rendering

**Files**: 
- `hh/render/html/image_group.py`
- `hh/page/render_helpers.py`

- Image groups render with links to image pages
- Links are intercepted by view-toggle system
- Works in both table and tile views

### CSS Whitelist

**File**: `hh/deploy/conf/css_whitelist.py`

- `image-viewer.css` added to CSS whitelist
- Required for CSS to be loaded in HTTP backend

---

## Summary of System Changes

### Backend Changes

1. **New Action**: `hh/page/get_image_group.py`
   - Action script: `get_image_group_action()`
   - Parser: `get_image_group_parser()`
   - MCP registration: Tiers 1-4, read-only

2. **MCP Registration**: `hh/page/mcp_utils.py`
   - Registered `get_image_group` as MCP tool

3. **Label Registration**: `hh/page/config_labels.py`
   - Added labels for `get_image_group` parser

### Frontend Changes

1. **New TypeScript Class**: `hh/deploy/site/ts/image-viewer.ts`
   - Complete viewer implementation
   - Pan/zoom with state-based constraints
   - Keyboard, touch, and mouse support

2. **View Toggle Integration**: `hh/deploy/site/ts/view-toggle.ts`
   - Added `setupImageViewerLinks()` method
   - Calls viewer on image link clicks
   - Integrated with view swap callbacks

3. **Overlay Link Helpers**: `hh/deploy/site/ts/overlay/overlay-link-helpers.ts`
   - Generalized link interception utilities
   - Shared with browser system
   - Supports custom matchers and handlers

4. **CSS Styling**: 
   - `hh/deploy/site/css/image-viewer.css` (layout styles)
   - Tier-specific CSS files (color styles with CSS variables)

5. **CSS Whitelist**: `hh/deploy/conf/css_whitelist.py`
   - Added `image-viewer.css` to whitelist

6. **Library**: `hh/deploy/site/js/interact.min.js`
   - interact.js library for pan/zoom gestures

### Design Decisions

1. **JSON Data Source**: Backend returns JSON instead of HTML for flexibility
2. **Read-Only Interface**: No editing capabilities (viewer only)
3. **Custom Overlay**: Extends overlay system similar to `ImageGroupSorter`
4. **State-Based Panning**: Panning constraints change based on zoom level (legacy used simple boundary constraints - see `legacy/core/js/image.js` lines 422-451)
5. **Overlay Scaling**: Overlay window scales with image zoom (legacy kept overlay fixed - see line 234)
6. **Instance Selection**: Automatically selects best image size for display (legacy looped backwards - see lines 157-166)
7. **Preloading**: Loads full-size images on zoom start (legacy loaded `instances[0]`, new loads largest instance - see line 338 vs new implementation)
8. **Generalized Link Helpers**: Shared infrastructure with browser system

---

## Future Enhancements

Potential future improvements (not yet implemented):

1. **Image Links in Processed Text**: Support opening viewer from image links in page text
2. **Animation Effects**: Add carousel-style transitions between images
3. **Zoom Origin**: Zoom from mouse/touch position instead of center
4. **Image Preloading**: Preload adjacent images for faster navigation
5. **Full-Screen Mode**: Toggle full-screen viewing
6. **Image Metadata**: Display additional metadata (EXIF data, etc.)

---

## Simplification Plan

### Goals

Simplify the image viewer implementation to focus on core zoom/pan functionality by removing UI elements and streamlining the DOM structure. The goal is to get the state-based panning system working correctly without distractions from scrollbars, containers, or unnecessary UI elements.

### Current Issues

- Scrollbars appearing in the image container (unwanted)
- Complex DOM structure with multiple wrapper divs
- UI elements (caption, visibility, control links) adding complexity
- Need to verify state-based panning system works correctly through all zoom states

### Simplification Approach

**Phase 1: Strip Out UI Elements**
- Remove caption, visibility label, and control links from HTML generation
- Remove event handlers for removed elements
- Keep only essential overlay → wrapper div → image structure

**Phase 2: Simplify DOM Structure**
- **Single wrapper only**: Use `imageZoomContainer` as the only wrapper around the image
- Remove `imageViewerTargetImageWrapper` (eliminate double-wrapping)
- Structure: Overlay → `imageZoomContainer` → `<img>` (3-tier structure)
- Apply transforms to `imageZoomContainer` (not directly to image)
- Ensure `overflow: hidden` on container to prevent scrollbars
- Position container absolutely

**Phase 3: Minimal Window Setup**
- Keep `updateOverlaySize()` method but make window scale 1:1 with image
- Window should be invisible/minimal (no padding/borders initially)
- Window and image locked together, no scrollbars ever visible
- Window can be expanded later with padding/borders if needed

**Phase 4: Focus on Default → First Inflection**
- Keep state detection logic but add a "stop" at first inflection point for testing
- Ensure image stays perfectly centered (no panning) from default state to first edge touch
- Test mouse wheel zoom and pinch-to-zoom
- Verify no scrollbars appear
- Test that image grows while staying centered until first edge touches window edge

**Phase 5: Touch Gesture Setup (Basic)**
- Set up interact.js for swipe-to-navigate at default state only
- Use standard momentum/threshold approach for swipe detection
- Swipe must be large/fast enough to overcome detent/momentum threshold
- At default state: swipe navigates between images
- When zoomed: swipe pans the image (implement after zoom states work)
- Leave panning gestures for later (after zoom states are verified)

### Interaction Model

**Desktop Users:**
- Mouse wheel: Zoom in/out
- Arrow keys: Navigate between images
- Escape: Close viewer
- Click backdrop: Close viewer

**Touch Screen Users:**
- Pinch-to-zoom: Zoom in/out
- Swipe (at default state): Navigate between images (with momentum threshold)
- Swipe (when zoomed): Pan image (after zoom states work)
- Tap backdrop: Close viewer (when at default state)

### Testing Strategy

1. **Default State**: Verify image displays with border, overlay mask visible, page behind visible
2. **Default → First Inflection**: Test zooming in while image stays centered, no panning allowed
3. **First Inflection Detection**: Verify system correctly detects when first edge touches window edge
4. **Stop at First Inflection**: Add temporary stop/indicator to verify state detection works
5. **No Scrollbars**: Verify no scrollbars appear at any zoom level
6. **Touch Gestures**: Test swipe-to-navigate at default state with momentum threshold

### Architecture Decisions

- **Keep OverlayManager**: Use minimal/empty overlay to leverage escape key and backdrop click handling
- **Keep State-Based Panning**: This is the core feature we're trying to dial in
- **Keep updateOverlaySize()**: Method will scale window 1:1 with image, can be expanded later
- **CSS-Based Sizing**: Use CSS for image sizing at default state (maintain aspect ratio automatically)
- **Single Wrapper**: Only `imageZoomContainer` wraps the image (no double-wrapping)

### Future Expansion

Once core zoom/pan functionality is working correctly:
- Can add back caption, visibility, control links if needed
- Can add padding/borders to window container
- Can refine touch gesture thresholds
- Can add animation/transitions between images


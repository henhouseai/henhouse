# Image Group Viewer System Architecture

This document covers the implementation of the image viewer overlay system, a full-screen image viewer with pan/zoom support that opens when clicking images in a page's image group. The viewer is a read-only interface for viewing images with advanced zoom and pan controls.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Design](#2-architecture-design)
3. [Overlay System Integration](#3-overlay-system-integration)
4. [Backend Implementation](#4-backend-implementation)
5. [Frontend Implementation](#5-frontend-implementation)
6. [CSS Styling](#6-css-styling)

## Agent Quick Reference

- **Core Concept**: Image viewer integrates with overlay system using `mode: 'zoomable'`
- **MCP Tool**: `get_image_group` - returns JSON data for all images in a page's image group
- **TypeScript Class**: `ImageViewer` in `hh/deploy/site/ts/image-viewer.ts`
- **Overlay Integration**: Uses `OverlayManager.getInstance().show()` with special options
- **Zoom States**: Three states control panning behavior (centered → single-axis → both axes)
- **Read-Only**: No editing, deleting, or caption modification (viewer only)

## Agent Training Notes

### Current State
- Image viewer is integrated with the overlay system
- Uses overlay `mode: 'zoomable'` to trigger special behavior
- Native event handling for pan/zoom/touch (no external library)
- Header shows "Image Viewer" title with Cancel button (from overlay system)
- Footer shows caption with same styling as header

### Key Design Decisions
- **Overlay Integration**: Uses `OverlayManager.getInstance().show()` instead of custom overlay
- **Width-Only Sizing**: Only sets width on window, lets height auto-calculate naturally
- **Raw Content Mode**: Image goes directly into overlay without `div.content` wrapper
- **Native Events**: Pan/zoom handled with native mouse, wheel, and touch events
- **State-Based Panning**: Panning constraints change based on zoom level

---

## 1. System Overview

The image viewer provides a full-screen viewing experience for images in a page's image group. Users can click any image link to open the viewer, which displays the image with pan/zoom capabilities. The viewer supports keyboard navigation, touch gestures, and mouse wheel zooming.

### Architecture Flow

1. **Image Link Click**: User clicks an image link in the page's image group
2. **Viewer Creation**: `ImageViewer.openFromImageLink(pageId, imageId)` called
3. **Data Loading**: Viewer calls `get_image_group` MCP tool to fetch all images and instances
4. **Overlay Creation**: Viewer uses `OverlayManager.getInstance().show()` with `mode: 'zoomable'`
5. **Interaction Setup**: Viewer sets up native event handlers for pan/zoom/touch
6. **Navigation**: User can navigate between images using arrow keys or swipe gestures
7. **Zoom/Pan**: User can zoom with mouse wheel or pinch gestures, pan by dragging

### Key Components

- **`get_image_group` Action**: Backend action returning JSON data for all images
- **`ImageViewer` Class**: TypeScript class managing viewer state, pan/zoom, and navigation
- **Overlay System**: Uses zoomable mode (raw content, footer)
- **CSS Styling**: zoomable classes (`overlay-window-zoomable`, `zoomable`)
- **Caption Link**: Caption is an anchor to `/img/{id}`

---

## 2. Architecture Design

### Overlay System Integration

The image viewer uses the standard overlay system with `mode: 'zoomable'`:

```typescript
OverlayManager.getInstance().show({
  header: 'Image Viewer',
  content: [imageContainer],
  mode: 'zoomable',             // Zoomable behavior
  footerContent: captionElement, // Caption below image
  closable: true,
  showSubmit: false,            // No submit button
  cancelLabel: 'Close',
  onCancel: () => this.cleanup(),
  onUnmount: () => this.cleanupHandlers()
});
```

### What zoomable mode does

When `mode: 'zoomable'`:
1. **No Debug Options**: Debug options section is not rendered
2. **Raw Content**: Content goes directly into overlay without `div.content` wrapper
3. **Footer Support**: `footerContent` is rendered after main content
4. **Touch Handling**: `touch-action: none` on window/backdrop; explicit pinch handlers

### Zoom State System

The viewer implements three distinct zoom states:

#### State 1: Default (scale = 1.0 to first inflection)
- Image fully visible, centered
- No panning allowed
- Continues until first edge touches viewport edge

#### State 2: Between Inflections
- First axis fills viewport edge-to-edge
- Single-axis panning enabled (only the axis that touched first)
- Other axis locked to center

#### State 3: Deep Zoom (after second inflection)
- Image fills entire viewport
- Both X and Y panning enabled
- Constrained so image edges never go past viewport

### Sizing Approach

**Width-Only Control**: The viewer only sets width on the overlay window and lets height calculate naturally:

1. Calculate target width based on image aspect ratio and viewport constraints
2. Set only `width`/`maxWidth` on window element (no height)
3. Let header, image, and footer stack vertically with natural heights
4. Read `offsetHeight` after rendering for inflection calculations; images set intrinsic width/height to avoid first-load mis-measurements

This avoids complex height calculations that must account for header, footer, padding, and borders.

---

## 3. Overlay System Integration

### Changes to Overlay System

**File: `hh/deploy/site/ts/overlay/overlay-manager.ts`**

Added new options to `OverlayOptions` interface:
```typescript
interface OverlayOptions {
  // ... existing options ...
  imageViewerMode?: boolean;     // Special mode for image viewer
  footerContent?: string | HTMLElement;  // Footer content (caption)
}
```

**File: `hh/deploy/site/ts/overlay/overlay.ts`**

- Passes `rawContent: true` to OverlayContent when `imageViewerMode` is true
- Renders `footerContent` after main content (uses `contentWrapperHeader overlay` class for consistent styling)
- Skips debug options when `imageViewerMode` is true

**File: `hh/deploy/site/ts/overlay/overlay-content.ts`**

Added `rawContent` option:
```typescript
interface OverlayContentProps {
  // ... existing props ...
  rawContent?: boolean;  // If true, append content directly without div.content wrapper
}
```

When `rawContent: true`, content items are appended directly to the container without being wrapped in `div.content`.

### CSS Changes

**File: `hh/deploy/site/css/overlay.css`**

Changed all `#overlayWindow` selectors to `.overlay-window` (87 occurrences) to:
1. Support z-stacking with multiple overlays (no duplicate IDs)
2. Allow class-based specificity for overrides

Added rule for image viewer:
```css
.image-viewer-overlay {
  overflow: hidden;
}
```

**File: `hh/deploy/site/ts/overlay/overlay-window.ts`**

Removed `window.id = 'overlayWindow'` - now uses class only.

---

## 4. Backend Implementation

### `get_image_group` Action

**File**: `hh/page/get_image_group.py`

Returns JSON data for all images in a page's image group.

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
          "src": "path/to/image.jpg"
        }
      ]
    }
  ]
}
```

---

## 5. Frontend Implementation

### TypeScript Class: `ImageViewer`

**File**: `hh/deploy/site/ts/image-viewer.ts`

#### Key Properties

```typescript
class ImageViewer {
  private overlay: Overlay | null = null;
  private windowEl: HTMLElement | null = null;
  private headerEl: HTMLElement | null = null;
  private contentEl: HTMLElement | null = null;
  private footerEl: HTMLElement | null = null;
  private headerHeight = 0;
  private footerHeight = 0;
  
  // Zoom/pan state
  private currentScale = 1;
  private panX = 0;
  private panY = 0;
  private scaleForWidthMatch = 1;
  private scaleForHeightMatch = 1;
  private detentActive = false;
  
  // Layout state
  private baseOverlayWidth = 0;
  private baseOverlayHeight = 0;
  private baseInnerWidth = 0;
  private baseInnerHeight = 0;
  private intrinsicWidth = 0;
  private intrinsicHeight = 0;
  
  // Image data
  private images: ImageData[] = [];
  private currentImageIndex = 0;
}
```

#### Key Methods

- **`show()`**: Entry point - loads data and renders overlay
- **`loadAndRender()`**: Fetches image data via RPC, calls `renderOverlay()`
- **`renderOverlay()`**: Creates overlay using `OverlayManager.getInstance().show()`
- **`createImageElement()`**: Creates the image box element
- **`updateImageContent()`**: Updates image when navigating between images
- **`initializeBaseSizes()`**: Calculates initial sizing based on viewport and image dimensions
- **`applyTransforms()`**: Applies width to window, reads actual height, applies pan transform
- **`applyScale()`**: Handles zoom with detent logic at inflection points
- **`clampPan()`**: Constrains panning based on zoom state
- **`getZoomState()`**: Returns current state ('zoomedOut', 'between', 'zoomedIn')
- **`bindEvents()`**: Sets up mouse, wheel, touch, and keyboard handlers
- **`navigate()`**: Moves to next/previous image
- **`cleanup()`**: Removes event handlers and cleans up state

#### Event Handling

**Mouse:**
- Wheel: Zoom in/out
- Drag: Pan image (when zoomed)

**Touch:**
- Pinch: Zoom in/out
- Drag: Pan image (when zoomed)
- Swipe: Navigate between images (when at default scale)

**Keyboard:**
- Arrow Left/Right: Navigate between images
- Escape: Close viewer (handled by overlay system)

#### Sizing Logic

```typescript
private initializeBaseSizes(intrinsicW: number, intrinsicH: number): void {
  // Measure header/footer heights (already rendered by overlay)
  this.headerHeight = this.headerEl?.offsetHeight || 0;
  this.footerHeight = this.footerEl?.offsetHeight || 0;
  
  // Calculate available space for image
  const maxW = viewportWidth - margin;
  const maxH = viewportHeight - margin - headerHeight - footerHeight - padding;
  
  // Scale to fit, preserving aspect ratio
  const fitScale = Math.min(maxW / intrinsicW, maxH / intrinsicH, 1);
  
  this.baseInnerWidth = intrinsicW * fitScale;
  this.baseInnerHeight = intrinsicH * fitScale;
  
  // Only set width on window, let height auto-calculate
  this.windowEl.style.width = `${this.baseOverlayWidth}px`;
  this.windowEl.style.height = 'auto';
  
  // Read actual rendered height for inflection calculations
  this.baseOverlayHeight = this.windowEl.offsetHeight;
}
```

#### Static Entry Point

```typescript
static async openFromImageLink(pageId: number, imageId?: number): Promise<void> {
  const viewer = new ImageViewer(pageId, imageId);
  await viewer.show();
}
```

---

## 6. CSS Styling

### Image Viewer Overlay

**File**: `hh/deploy/site/css/overlay.css`

```css
/* Image viewer overlay - no scrollbars, we handle pan/zoom */
.image-viewer-overlay {
  overflow: hidden;
}
```

### Image Viewer Elements

**File**: `hh/deploy/site/css/image-viewer.css`

```css
.image-viewer-box {
  box-sizing: border-box;
}

.image-viewer-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
```

### Overlay Window Class Selectors

All overlay CSS uses `.overlay-window` class selector (not `#overlayWindow` ID) to support z-stacking multiple overlays without duplicate IDs.

---

## Summary

### What's Implemented

- ✅ Integration with overlay system via `imageViewerMode`
- ✅ Raw content mode (no div.content wrapper)
- ✅ Footer content for caption (same styling as header)
- ✅ Width-only sizing with auto height
- ✅ State-based panning (centered → single-axis → both axes)
- ✅ Detent system at first inflection point
- ✅ Mouse wheel zoom
- ✅ Touch pinch-to-zoom
- ✅ Touch swipe navigation
- ✅ Keyboard navigation (arrow keys)
- ✅ Escape to close (via overlay system)
- ✅ Backdrop click to close (via overlay system)
- ✅ Window resize handling
- ✅ Image navigation with state reset

### Files Modified

1. **`hh/deploy/site/ts/image-viewer.ts`** - Main viewer class
2. **`hh/deploy/site/ts/overlay/overlay-manager.ts`** - Added `imageViewerMode` and `footerContent` options
3. **`hh/deploy/site/ts/overlay/overlay.ts`** - Handle imageViewerMode, render footer
4. **`hh/deploy/site/ts/overlay/overlay-content.ts`** - Added `rawContent` option
5. **`hh/deploy/site/ts/overlay/overlay-window.ts`** - Removed ID, class only
6. **`hh/deploy/site/css/overlay.css`** - Changed `#overlayWindow` to `.overlay-window`, added `.image-viewer-overlay`

### Future Enhancements

Potential improvements (not yet implemented):

1. **Animation Effects**: Smooth transitions between images
2. **Zoom Origin**: Zoom from mouse/touch position instead of center
3. **Image Preloading**: Preload adjacent images for faster navigation
4. **Full-Screen Mode**: Toggle browser full-screen
5. **Thumbnail Strip**: Show all images in group as thumbnails

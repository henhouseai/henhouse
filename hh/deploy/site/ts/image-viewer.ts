/**
 * ImageViewer - Full-screen image viewer overlay with pan/zoom support.
 * Ported from legacy/core/js/image.js
 */

import { RPCClient } from './rpc-client.js';
// Import interact.js as a side-effect (it will be available as window.interact)
import './interact.min.js';

// Get interact from global scope
declare global {
  interface Window {
    interact: any;
  }
}
const interact = (window as any).interact;

interface ImageInstance {
  width: number;
  height: number;
  filesize: number;
  src: string;
}

interface ImageData {
  id: number;
  caption: string;
  visibility: number;
  viewCount: number;
  instances: ImageInstance[];
}

interface ImageGroupResponse {
  page_id: number;
  images: ImageData[];
}

export class ImageViewer {
  private rpc: RPCClient;
  private backdrop: HTMLElement | null = null;
  private container: HTMLElement | null = null;
  private pageId: number;
  private images: ImageData[] = [];
  private currentImageIndex: number = 0;
  private touchStartX: number | null = null;
  private touchStartY: number | null = null;
  private touchStartTime: number | null = null;
  private keyboardHandler: ((e: KeyboardEvent) => void) | null = null;
  private resizeHandler: (() => void) | null = null;
  private interactInstance: any = null;
  private zIndex: number = 1000;

  private initialImageId?: number;
  
  // Zoom/pan state
  private baseImageWidth: number = 0;
  private baseImageHeight: number = 0;
  private baseOverlayWidth: number = 0;
  private baseOverlayHeight: number = 0;
  private currentScale: number = 1.0;
  private panX: number = 0;
  private panY: number = 0;
  private scaleForWidthMatch: number = 1.0;
  private scaleForHeightMatch: number = 1.0;
  
  // Store full-size dimensions for resize calculations
  private fullSizeWidth: number = 0;
  private fullSizeHeight: number = 0;

  constructor(pageId: number, initialImageId?: number) {
    this.rpc = new RPCClient();
    this.pageId = pageId;
    this.initialImageId = initialImageId;
  }

  /**
   * Show the image viewer overlay.
   */
  async show(): Promise<void> {
    await this.loadAndRender();
  }

  /**
   * Load image group data and render overlay.
   */
  private async loadAndRender(): Promise<void> {
    try {
      // Call get_image_group MCP tool (accepts either 'id' or 'page_id')
      const result = await this.rpc.call('get_image_group', { id: this.pageId });
      const groupData = result.data as ImageGroupResponse;

      if (!groupData || !groupData.images || groupData.images.length === 0) {
        throw new Error('No images found in image group');
      }

      this.images = groupData.images;

      // Find initial image index if provided
      if (this.initialImageId !== undefined) {
        const index = this.images.findIndex(img => img.id === this.initialImageId);
        if (index >= 0) {
          this.currentImageIndex = index;
        }
      }

      // Render overlay
      this.renderOverlay();

    } catch (error) {
      console.error('Error loading image viewer:', error);
      this.rpc.showError('image_viewer', error);
    }
  }

  /**
   * Get the best image instance for a given target width.
   * Ported from legacy getBestInstance logic.
   */
  private getBestInstance(targetWidth: number, instances: ImageInstance[]): ImageInstance | null {
    if (!instances || instances.length === 0) {
      return null;
    }

    // Instances are already sorted by width (ascending) from backend
    // Find the first instance that is >= targetWidth, or use the largest
    let best = instances[0];
    
    for (let i = 1; i < instances.length; i++) {
      if (instances[i].width >= targetWidth) {
        best = instances[i];
        break;
      }
    }
    
    // If we didn't find one >= targetWidth, use the largest (last one)
    if (best.width < targetWidth && instances.length > 0) {
      best = instances[instances.length - 1];
    }

    return best;
  }

  /**
   * Calculate display dimensions for an image instance.
   * Ported from legacy getImage logic.
   */
  private calculateDisplayDimensions(
    instance: ImageInstance,
    maxWidth: number,
    maxHeight: number
  ): { width: number; height: number } {
    let w = instance.width;
    let h = instance.height;

    // Scale down if necessary
    if (w > maxWidth) {
      h = h * (maxWidth / w);
      w = maxWidth;
    }
    if (h > maxHeight) {
      w = w * (maxHeight / h);
      h = maxHeight;
    }

    // Further scaling for tall narrow images
    if (h > maxWidth * 1.5) {
      w = (maxWidth * w * 1.5) / h;
      h = maxWidth * 1.5;
    }

    return {
      width: Math.round(w),
      height: Math.round(h)
    };
  }


  /**
   * Measure window with full-size wrapper and calculate optimal sizes.
   * Returns optimal wrapper and window dimensions.
   */
  private measureAndCalculateOptimalSize(fullSizeWidth: number, fullSizeHeight: number): {
    optimalWrapperWidth: number;
    optimalWrapperHeight: number;
    optimalWindowWidth: number;
    optimalWindowHeight: number;
  } {
    if (!this.container) {
      throw new Error('Container not found');
    }
    
    const imageWrapper = this.container.querySelector('#imageWrapper') as HTMLElement;
    if (!imageWrapper) {
      throw new Error('Image wrapper not found');
    }

    // Set wrapper to full-size dimensions
    imageWrapper.style.width = `${fullSizeWidth}px`;
    imageWrapper.style.height = `${fullSizeHeight}px`;

    // Force reflow to ensure styles are applied
    void this.container.offsetHeight;

    // Measure the window size (wrapper + padding + border)
    const windowWidth = this.container.offsetWidth;
    const windowHeight = this.container.offsetHeight;

    // Calculate optimal size to fit on screen with 40px margin on all sides
    const pageWidth = this.getPageWidth();
    const pageHeight = this.getPageHeight();
    const maxWindowWidth = pageWidth - 80; // 40px margin each side
    const maxWindowHeight = pageHeight - 80;

    // Calculate scaling factor based on limiting dimension
    const scaleX = maxWindowWidth / windowWidth;
    const scaleY = maxWindowHeight / windowHeight;
    const optimalScale = Math.min(scaleX, scaleY, 1.0); // Don't scale up, only down

    // Calculate optimal sizes
    const optimalWrapperWidth = fullSizeWidth * optimalScale;
    const optimalWrapperHeight = fullSizeHeight * optimalScale;
    const optimalWindowWidth = windowWidth * optimalScale;
    const optimalWindowHeight = windowHeight * optimalScale;

    return {
      optimalWrapperWidth,
      optimalWrapperHeight,
      optimalWindowWidth,
      optimalWindowHeight
    };
  }

  /**
   * Apply optimal sizes to wrapper and window.
   */
  private applyOptimalSizes(
    optimalWrapperWidth: number,
    optimalWrapperHeight: number,
    optimalWindowWidth: number,
    optimalWindowHeight: number
  ): void {
    if (!this.container) {
      return;
    }
    
    const imageWrapper = this.container.querySelector('#imageWrapper') as HTMLElement;
    if (imageWrapper) {
      imageWrapper.style.width = `${optimalWrapperWidth}px`;
      imageWrapper.style.height = `${optimalWrapperHeight}px`;
    }

    this.container.style.width = `${optimalWindowWidth}px`;
    this.container.style.height = `${optimalWindowHeight}px`;
    this.container.style.maxWidth = `${optimalWindowWidth}px`;
    this.container.style.maxHeight = `${optimalWindowHeight}px`;

    // Store base dimensions for zoom calculations
    this.baseImageWidth = optimalWrapperWidth;
    this.baseImageHeight = optimalWrapperHeight;
    this.baseOverlayWidth = optimalWindowWidth;
    this.baseOverlayHeight = optimalWindowHeight;

    // Calculate special point scales based on CONTAINER size touching viewport edge
    const viewportWidth = this.getPageWidth();
    const viewportHeight = this.getPageHeight();
    this.scaleForWidthMatch = viewportWidth / optimalWindowWidth;
    this.scaleForHeightMatch = viewportHeight / optimalWindowHeight;
  }

  /**
   * Load optimal image instance based on wrapper size.
   */
  private loadOptimalImage(
    optimalWrapperWidth: number,
    optimalWrapperHeight: number,
    fullSizeSrc: string,
    caption: string
  ): void {
    if (!this.container) {
      return;
    }
    
    const currentImage = this.images[this.currentImageIndex];
    
    // Select optimal image instance based on scaled-down wrapper size
    const displayInstance = this.getBestInstance(optimalWrapperWidth, currentImage.instances);
    if (!displayInstance) {
      console.error('No display instance found');
      return;
    }

    // Calculate display dimensions
    const displayDims = this.calculateDisplayDimensions(
      displayInstance,
      optimalWrapperWidth,
      optimalWrapperHeight
    );

    // Format image src with /srv/images/ prefix
    const imageSrc = displayInstance.src.startsWith('/srv/images/') 
      ? displayInstance.src 
      : `/srv/images/${displayInstance.src}`;

    // Get or create image element
    let img = this.container.querySelector('#imageViewerTargetImage') as HTMLImageElement;
    if (!img) {
      const imageWrapper = this.container.querySelector('#imageWrapper') as HTMLElement;
      if (!imageWrapper) return;
      
      img = document.createElement('img');
      img.id = 'imageViewerTargetImage';
      imageWrapper.appendChild(img);
    }

    // Update image
    img.src = imageSrc;
    img.alt = caption;
    img.setAttribute('width', String(displayDims.width));
    img.setAttribute('height', String(displayDims.height));
    
    // Store full-size src for later zoom swap
    (img as any).dataset.fullSizeSrc = fullSizeSrc;
  }

  /**
   * Render the overlay with current image.
   */
  private renderOverlay(): void {
    if (this.images.length === 0) {
      return;
    }

    const currentImage = this.images[this.currentImageIndex];
    
    // Get full-size image dimensions (largest instance, which is last in sorted array)
    const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
    this.fullSizeWidth = fullSizeInstance.width;
    this.fullSizeHeight = fullSizeInstance.height;
    const fullSizeSrc = fullSizeInstance.src.startsWith('/srv/images/') 
      ? fullSizeInstance.src 
      : `/srv/images/${fullSizeInstance.src}`;

    // Reset pan and scale for new image
    this.currentScale = 1.0;
    this.panX = 0;
    this.panY = 0;

    // Create custom overlay with full-size dimensions, it will measure and adjust
    this.createCustomOverlay(this.fullSizeWidth, this.fullSizeHeight, fullSizeSrc, currentImage.caption);

    // Preload full-size image
    const preloadImg = new Image();
    preloadImg.src = fullSizeSrc;

    // Set up interact.js after a short delay
    setTimeout(() => {
      this.setupInteract();
      this.setupEventHandlers();
      this.bindKeys();
    }, 50);
  }

  /**
   * Set up interact.js for pan/zoom.
   */
  private setupInteract(): void {
    const imageWrapper = document.getElementById('imageWrapper');
    if (!imageWrapper) {
      return;
    }

    // Initialize transform data
    (imageWrapper as any).dataset.scale = '1';
    (imageWrapper as any).dataset.x = '0';
    (imageWrapper as any).dataset.y = '0';
    (imageWrapper as any).dataset.fullsize = 'false';

    // Set initial transform - only translate, no scale (scaling handled by container size)
    imageWrapper.style.transform = 'translate(0, 0)';

    // Set up interact.js
    this.interactInstance = interact(imageWrapper)
      .gesturable({
        listeners: {
          start: (event: any) => this.onGestureStart(event),
          move: (event: any) => this.onGestureMove(event),
          end: (event: any) => this.onGestureEnd(event)
        }
      })
      .draggable({
        inertia: false, // Disable inertia for precise control
        listeners: {
          start: (event: any) => this.onDragStart(event),
          move: (event: any) => this.onDragMove(event),
          end: (event: any) => this.onDragEnd(event)
        }
      });
  }

  /**
   * Get current zoom state based on scale.
   */
  private getZoomState(scale: number): 'zoomedOut' | 'widthMatch' | 'between' | 'heightMatch' | 'zoomedIn' {
    if (scale <= 1.0) return 'zoomedOut';
    if (Math.abs(scale - this.scaleForWidthMatch) < 0.01) return 'widthMatch';
    if (scale > this.scaleForWidthMatch && scale < this.scaleForHeightMatch) return 'between';
    if (Math.abs(scale - this.scaleForHeightMatch) < 0.01) return 'heightMatch';
    return 'zoomedIn';
  }

  /**
   * Apply panning constraints based on zoom state.
   */
  private applyPanConstraints(scale: number, panX: number, panY: number): { x: number; y: number } {
    const state = this.getZoomState(scale);
    const viewportWidth = this.getPageWidth();
    const viewportHeight = this.getPageHeight();
    
    const scaledImageWidth = this.baseImageWidth * scale;
    const scaledImageHeight = this.baseImageHeight * scale;
    
    let constrainedX = panX;
    let constrainedY = panY;

    // Get container position in viewport
    if (!this.container) {
      return { x: panX, y: panY };
    }

    const overlayRect = this.container.getBoundingClientRect();
    const overlayCenterX = overlayRect.left + overlayRect.width / 2;
    const overlayCenterY = overlayRect.top + overlayRect.height / 2;

    // Calculate image bounds in viewport coordinates
    // Image is centered in overlay, so offset from overlay center
    const imageLeft = overlayCenterX - scaledImageWidth / 2 + panX;
    const imageRight = overlayCenterX + scaledImageWidth / 2 + panX;
    const imageTop = overlayCenterY - scaledImageHeight / 2 + panY;
    const imageBottom = overlayCenterY + scaledImageHeight / 2 + panY;

    // TESTING: Stop at first inflection point (widthMatch or heightMatch, whichever comes first)
    const firstInflectionScale = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
    if (scale >= firstInflectionScale && scale <= firstInflectionScale + 0.01) {
      // At first inflection - stop here for testing
      console.log('STOPPED AT FIRST INFLECTION POINT - Scale:', scale, 'First inflection:', firstInflectionScale);
      constrainedX = 0;
      constrainedY = 0;
      // Prevent further zooming in for testing
      return { x: constrainedX, y: constrainedY };
    }

    if (state === 'zoomedOut' || state === 'widthMatch') {
      // Locked to center - no panning allowed
      constrainedX = 0;
      constrainedY = 0;
    } else if (state === 'between') {
      // X panning enabled, Y locked to center
      constrainedY = 0;
      
      // Constrain X so image edges don't go past viewport
      const minX = viewportWidth / 2 - imageRight; // When right edge hits right viewport
      const maxX = viewportWidth / 2 - imageLeft; // When left edge hits left viewport
      constrainedX = Math.max(minX, Math.min(maxX, panX));
    } else {
      // Both X and Y panning enabled
      // Constrain so image edges don't go past viewport
      const minX = viewportWidth / 2 - imageRight;
      const maxX = viewportWidth / 2 - imageLeft;
      const minY = viewportHeight / 2 - imageBottom;
      const maxY = viewportHeight / 2 - imageTop;
      
      constrainedX = Math.max(minX, Math.min(maxX, panX));
      constrainedY = Math.max(minY, Math.min(maxY, panY));
    }

    return { x: constrainedX, y: constrainedY };
  }

  /**
   * Update overlay size based on current scale.
   */
  private updateOverlaySize(scale: number): void {
    if (!this.container) return;

    const scaledWidth = this.baseOverlayWidth * scale;
    const scaledHeight = this.baseOverlayHeight * scale;

    // Update size (centering transform is in CSS)
    this.container.style.width = `${scaledWidth}px`;
    this.container.style.height = `${scaledHeight}px`;
    this.container.style.maxWidth = `${scaledWidth}px`;
    this.container.style.maxHeight = `${scaledHeight}px`;
  }

  /**
   * Handle drag start.
   */
  private onDragStart(event: any): void {
    // Store initial pan position
    const imageWrapper = event.target;
    const dataset = (imageWrapper as any).dataset;
    dataset.initialPanX = this.panX.toString();
    dataset.initialPanY = this.panY.toString();
  }

  /**
   * Handle drag move with state-based constraints.
   */
  private onDragMove(event: any): void {
    const imageWrapper = event.target;
    const dataset = (imageWrapper as any).dataset;
    
    const initialPanX = parseFloat(dataset.initialPanX) || 0;
    const initialPanY = parseFloat(dataset.initialPanY) || 0;
    
    // Calculate new pan position from gesture
    const newPanX = initialPanX + event.dx;
    const newPanY = initialPanY + event.dy;
    
    // Apply constraints based on zoom state
    const constrained = this.applyPanConstraints(this.currentScale, newPanX, newPanY);
    
    this.panX = constrained.x;
    this.panY = constrained.y;
    
    // Update transform
    imageWrapper.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.currentScale})`;
  }

  /**
   * Handle drag end.
   */
  private onDragEnd(event: any): void {
    // Pan constraints are already applied in onDragMove
  }

  /**
   * Create custom overlay (backdrop + container) without using OverlayManager.
   */
  private createCustomOverlay(fullSizeWidth: number, fullSizeHeight: number, fullSizeSrc: string, caption: string): void {
    // Create backdrop (static styles in CSS, only zIndex is dynamic)
    this.backdrop = document.createElement('div');
    this.backdrop.id = 'imageViewerBackdrop';
    this.backdrop.style.zIndex = String(this.zIndex);
    
    // Backdrop click handler
    this.backdrop.addEventListener('click', (e) => {
      // Only close if clicking directly on backdrop (not on container)
      if (e.target === this.backdrop) {
        this.cleanup();
      }
    });

    // Prevent default touch behaviors on backdrop (pinch-to-zoom, etc.)
    this.backdrop.addEventListener('touchstart', (e) => {
      // Prevent default browser zoom when pinching on backdrop
      if (e.touches.length > 1) {
        e.preventDefault();
      }
      // Also handle touch for gesture detection
      this.handleTouchStart(e);
    }, { passive: false });
    
    this.backdrop.addEventListener('touchmove', (e) => {
      // Prevent default browser zoom/scroll when pinching
      if (e.touches.length > 1) {
        e.preventDefault();
      }
      // Also handle touch for gesture detection
      this.handleTouchMove(e);
    }, { passive: false });
    
    this.backdrop.addEventListener('touchend', (e) => {
      // Handle touch end for gesture detection
      this.handleTouchEnd(e);
    }, { passive: false });

    // Create window with opacity: 0 (invisible for measurement)
    this.container = document.createElement('div');
    this.container.id = 'imageViewerWindow';
    this.container.style.opacity = '0';
    this.container.style.zIndex = String(this.zIndex + 1);
    // Don't set size yet - will be determined by wrapper + padding/border

    // Create image wrapper set to full-size dimensions (no image yet)
    const imageWrapper = document.createElement('div');
    imageWrapper.id = 'imageWrapper';
    imageWrapper.style.width = `${fullSizeWidth}px`;
    imageWrapper.style.height = `${fullSizeHeight}px`;

    this.container.appendChild(imageWrapper);

    // Append to body (invisible)
    document.body.appendChild(this.backdrop);
    document.body.appendChild(this.container);

    // Measure and calculate optimal sizes
    const optimalSizes = this.measureAndCalculateOptimalSize(fullSizeWidth, fullSizeHeight);
    
    // Apply optimal sizes
    this.applyOptimalSizes(
      optimalSizes.optimalWrapperWidth,
      optimalSizes.optimalWrapperHeight,
      optimalSizes.optimalWindowWidth,
      optimalSizes.optimalWindowHeight
    );

    // Load optimal image
    this.loadOptimalImage(
      optimalSizes.optimalWrapperWidth,
      optimalSizes.optimalWrapperHeight,
      fullSizeSrc,
      caption
    );

    // Fade in
    this.container.style.transition = 'opacity 0.2s';
    this.container.style.opacity = '1';

    // Prevent body scroll
    document.body.style.overflow = 'hidden';
  }

  /**
   * Create window only (for navigation - backdrop already exists).
   */
  private createWindowOnly(fullSizeWidth: number, fullSizeHeight: number, fullSizeSrc: string, caption: string): void {
    // Create window with opacity: 0 (invisible for measurement)
    this.container = document.createElement('div');
    this.container.id = 'imageViewerWindow';
    this.container.style.opacity = '0';
    this.container.style.zIndex = String(this.zIndex + 1);
    // Don't set size yet - will be determined by wrapper + padding/border

    // Create image wrapper set to full-size dimensions (no image yet)
    const imageWrapper = document.createElement('div');
    imageWrapper.id = 'imageWrapper';
    imageWrapper.style.width = `${fullSizeWidth}px`;
    imageWrapper.style.height = `${fullSizeHeight}px`;

    this.container.appendChild(imageWrapper);

    // Append to body (invisible, backdrop already exists)
    document.body.appendChild(this.container);

    // Measure and calculate optimal sizes
    const optimalSizes = this.measureAndCalculateOptimalSize(fullSizeWidth, fullSizeHeight);
    
    // Apply optimal sizes
    this.applyOptimalSizes(
      optimalSizes.optimalWrapperWidth,
      optimalSizes.optimalWrapperHeight,
      optimalSizes.optimalWindowWidth,
      optimalSizes.optimalWindowHeight
    );

    // Load optimal image
    this.loadOptimalImage(
      optimalSizes.optimalWrapperWidth,
      optimalSizes.optimalWrapperHeight,
      fullSizeSrc,
      caption
    );

    // Fade in
    this.container.style.transition = 'opacity 0.2s';
    this.container.style.opacity = '1';
  }

  /**
   * Set up event handlers for navigation and controls.
   */
  private setupEventHandlers(): void {
    // Touch handlers for swipe navigation - attach to zoom container
    const imageWrapper = document.getElementById('imageWrapper');
    if (imageWrapper) {
      imageWrapper.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
      imageWrapper.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
      imageWrapper.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: false });
      
      // Wheel zoom
      imageWrapper.addEventListener('wheel', (e) => this.handleWheelZoom(e));
    }

    // Also attach touch handlers to container to catch gestures there too
    if (this.container) {
      this.container.addEventListener('touchstart', (e) => {
        if (e.touches.length > 1) {
          e.preventDefault(); // Prevent browser zoom
        }
        this.handleTouchStart(e);
      }, { passive: false });
      
      this.container.addEventListener('touchmove', (e) => {
        if (e.touches.length > 1) {
          e.preventDefault(); // Prevent browser zoom
        }
        this.handleTouchMove(e);
      }, { passive: false });
      
      this.container.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: false });
    }

    // Window resize handler - just recalculate optimal size and apply it
    this.resizeHandler = () => {
      if (!this.container || this.fullSizeWidth === 0 || this.fullSizeHeight === 0) {
        return;
      }
      
      // Recalculate optimal sizes from stored full-size dimensions
      const optimalSizes = this.measureAndCalculateOptimalSize(this.fullSizeWidth, this.fullSizeHeight);
      
      // Apply optimal sizes (no fade, just resize)
      this.applyOptimalSizes(
        optimalSizes.optimalWrapperWidth,
        optimalSizes.optimalWrapperHeight,
        optimalSizes.optimalWindowWidth,
        optimalSizes.optimalWindowHeight
      );
    };
    window.addEventListener('resize', this.resizeHandler);
  }

  /**
   * Navigate to a different image.
   */
  private navigateImage(increment: number): void {
    if (this.images.length === 0 || !this.container) {
      return;
    }

    // Update index
    this.currentImageIndex = (this.currentImageIndex + increment + this.images.length) % this.images.length;

    // Update existing overlay instead of creating a new one
    this.updateOverlay();
  }

  /**
   * Update the existing overlay with new image content.
   */
  private updateOverlay(): void {
    if (!this.container || this.images.length === 0) {
      return;
    }

    const currentImage = this.images[this.currentImageIndex];
    
    // Get full-size image dimensions
    const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
    this.fullSizeWidth = fullSizeInstance.width;
    this.fullSizeHeight = fullSizeInstance.height;
    const fullSizeSrc = fullSizeInstance.src.startsWith('/srv/images/') 
      ? fullSizeInstance.src 
      : `/srv/images/${fullSizeInstance.src}`;

    // Fade out old window
    this.container.style.transition = 'opacity 0.2s';
    this.container.style.opacity = '0';

    // After fade out, remove old window and create new one (reuse backdrop)
    setTimeout(() => {
      // Remove old window
      if (this.container && this.container.parentNode) {
        this.container.parentNode.removeChild(this.container);
      }
      this.container = null as any;

      // Reset pan and scale
      this.currentScale = 1.0;
      this.panX = 0;
      this.panY = 0;

      // Create new window only (backdrop already exists)
      this.createWindowOnly(this.fullSizeWidth, this.fullSizeHeight, fullSizeSrc, currentImage.caption);

      // Preload full-size image
      const preloadImg = new Image();
      preloadImg.src = fullSizeSrc;
    }, 200);

    // Re-setup interact.js
    setTimeout(() => {
      if (this.interactInstance) {
        this.interactInstance.unset();
      }
      this.setupInteract();
    }, 150);
  }

  /**
   * Handle touch start for swipe detection.
   */
  private handleTouchStart(event: TouchEvent): void {
    const touch = event.touches[0];
    this.touchStartX = touch.clientX;
    this.touchStartY = touch.clientY;
    this.touchStartTime = event.timeStamp;
  }

  /**
   * Handle touch move - prevent scrolling if not zoomed.
   */
  private handleTouchMove(event: TouchEvent): void {
    const imageWrapper = document.getElementById('imageWrapper');
    if (!imageWrapper) return;
    
    const scale = parseFloat((imageWrapper as any).dataset.scale) || 1;
    if (scale === 1) {
      // Only prevent default scrolling if not zoomed in
      event.preventDefault();
    }
  }

  /**
   * Handle touch end - detect swipe gestures for navigation (at default state only).
   * Uses momentum/threshold approach to distinguish navigation swipes from panning.
   */
  private handleTouchEnd(event: TouchEvent): void {
    const imageWrapper = document.getElementById('imageWrapper');
    if (!imageWrapper) return;
    
    const scale = parseFloat((imageWrapper as any).dataset.scale) || 1;
    
    // Only handle swipe navigation at default state (scale === 1.0)
    // When zoomed, swipes are handled by interact.js drag gestures
    if (scale === 1.0 && this.touchStartX !== null && this.touchStartY !== null) {
      const touch = event.changedTouches[0];
      const touchEndX = touch.clientX;
      const touchEndY = touch.clientY;

      const deltaX = touchEndX - this.touchStartX;
      const deltaY = touchEndY - this.touchStartY;
      const deltaTime = this.touchStartTime ? event.timeStamp - this.touchStartTime : 0;
      
      // Calculate swipe distance and velocity
      const swipeDistance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
      const isHorizontal = Math.abs(deltaX) > Math.abs(deltaY);
      const velocity = deltaTime > 0 ? swipeDistance / deltaTime : 0;
      
      // Threshold for navigation swipe: must be horizontal, long enough, and fast enough
      // Standard approach: 100px minimum distance or high velocity (0.3 pixels per ms)
      const minSwipeDistance = 100;
      const minSwipeVelocity = 0.3;
      
      if (isHorizontal && (swipeDistance >= minSwipeDistance || velocity >= minSwipeVelocity)) {
        if (deltaX > 0) {
          // Swipe right - go to previous image
          if (this.images.length > 1) {
            this.navigateImage(-1);
          }
        } else {
          // Swipe left - go to next image
          if (this.images.length > 1) {
            this.navigateImage(1);
          }
        }
      }
    }

    // Reset touch positions
    this.touchStartX = null;
    this.touchStartY = null;
    this.touchStartTime = null;
  }

  /**
   * Handle wheel zoom.
   */
  private handleWheelZoom(event: WheelEvent): void {
    event.preventDefault();

    const imageWrapper = document.getElementById('imageWrapper');
    if (!imageWrapper) return;

    let scale = this.currentScale;

    // Load full-size image if not already loaded
    
    if (!(imageWrapper as any).dataset.fullsize || (imageWrapper as any).dataset.fullsize === 'false') {
      const currentImage = this.images[this.currentImageIndex];
      const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
      const fullSizeSrc = fullSizeInstance.src.startsWith('/srv/images/') 
        ? fullSizeInstance.src 
        : `/srv/images/${fullSizeInstance.src}`;
      const img = imageWrapper.querySelector('img') as HTMLImageElement;
      if (img) {
        img.src = fullSizeSrc;
      }
      (imageWrapper as any).dataset.fullsize = 'true';
    }

    const zoomSensitivity = 0.1;
    const delta = event.deltaY;
    const oldScale = scale;

    if (delta < 0) {
      scale += zoomSensitivity;
    } else {
      scale -= zoomSensitivity;
    }

    const minScale = 1;
    const maxScale = 3; // 300% of full size

    // TESTING: Stop at first inflection point
    const firstInflectionScale = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
    if (scale > firstInflectionScale) {
      scale = firstInflectionScale;
      console.log('STOPPED AT FIRST INFLECTION POINT - Scale limited to:', scale);
    }

    scale = Math.max(minScale, Math.min(maxScale, scale));
    this.currentScale = scale;

    // Update overlay size
    this.updateOverlaySize(scale);

    // Check if crossing special points when zooming out - snap to center
    const oldState = this.getZoomState(oldScale);
    const newState = this.getZoomState(scale);
    
    if (delta > 0 && (oldState === 'between' || oldState === 'zoomedIn' || oldState === 'heightMatch') && 
        (newState === 'widthMatch' || newState === 'zoomedOut')) {
      // Zooming out past special point - snap to center
      this.panX = 0;
      this.panY = 0;
    } else if (delta > 0 && oldState === 'zoomedIn' && newState === 'heightMatch') {
      // Zooming out to height match - keep X pan, center Y
      this.panY = 0;
    }

    // Apply pan constraints
    const constrained = this.applyPanConstraints(scale, this.panX, this.panY);
    this.panX = constrained.x;
    this.panY = constrained.y;

    // Update transforms - only translate for panning
    // Scaling is handled by container size, so image scales naturally (no transform scale needed)
    if (imageWrapper) {
      (imageWrapper as any).dataset.scale = scale.toString();
      imageWrapper.style.transform = `translate(${this.panX}px, ${this.panY}px)`;
    }
  }

  /**
   * Interact.js gesture start handler.
   */
  private onGestureStart(event: any): void {
    const target = event.target;
    const dataset = (target as any).dataset;

    // Load full-size image if not already loaded (when pinch-to-zoom starts)
    if (!dataset.fullsize || dataset.fullsize === 'false') {
      const currentImage = this.images[this.currentImageIndex];
      // Full-size is the largest instance (last in sorted ascending array)
      const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
      const fullSizeSrc = fullSizeInstance.src.startsWith('/srv/images/') 
        ? fullSizeInstance.src 
        : `/srv/images/${fullSizeInstance.src}`;
      const img = target.querySelector('img') as HTMLImageElement;
      if (img) {
        img.src = fullSizeSrc;
      }
      dataset.fullsize = 'true';
    }

    // Store initial scale and position
    dataset.initialScale = dataset.scale || '1';
    dataset.initialX = dataset.x || '0';
    dataset.initialY = dataset.y || '0';
  }

  /**
   * Interact.js gesture move handler.
   */
  private onGestureMove(event: any): void {
    event.preventDefault();

    const target = event.target;
    const dataset = (target as any).dataset;

    const initialScale = parseFloat(dataset.initialScale) || 1;
    let scale = initialScale * event.scale;

    const minScale = 1;
    const maxScale = 3;

    // TESTING: Stop at first inflection point
    const firstInflectionScale = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
    if (scale > firstInflectionScale) {
      scale = firstInflectionScale;
      console.log('STOPPED AT FIRST INFLECTION POINT (gesture) - Scale limited to:', scale);
    }

    scale = Math.max(minScale, Math.min(maxScale, scale));
    this.currentScale = scale;

    // Update overlay size
    this.updateOverlaySize(scale);

    const initialX = parseFloat(dataset.initialX) || 0;
    const initialY = parseFloat(dataset.initialY) || 0;

    // Calculate pan from gesture (deltaX/deltaY are relative to initial position)
    const newPanX = initialX + event.deltaX;
    const newPanY = initialY + event.deltaY;

    // Update overlay size
    this.updateOverlaySize(scale);

    // Apply constraints based on zoom state
    const constrained = this.applyPanConstraints(scale, newPanX, newPanY);
    this.panX = constrained.x;
    this.panY = constrained.y;

    dataset.scale = scale.toString();
    dataset.x = this.panX.toString();
    dataset.y = this.panY.toString();

    // Only translate for panning - scaling is handled by container size
    target.style.transform = `translate(${this.panX}px, ${this.panY}px)`;
  }

  /**
   * Interact.js gesture end handler.
   */
  private onGestureEnd(event: any): void {
    this.dragMoveListener(event);
  }

  /**
   * Interact.js drag move listener.
   */
  private dragMoveListener(event: any): void {
    const target = event.target;
    const dataset = (target as any).dataset;

    let x = (parseFloat(dataset.x) || 0) + event.dx;
    let y = (parseFloat(dataset.y) || 0) + event.dy;
    const scale = parseFloat(dataset.scale) || 1;

    // Get dimensions
    const imageWidth = (target as HTMLElement).offsetWidth * scale;
    const imageHeight = (target as HTMLElement).offsetHeight * scale;
    const containerWidth = (target.parentElement as HTMLElement).offsetWidth;
    const containerHeight = (target.parentElement as HTMLElement).offsetHeight;

    // Calculate boundaries
    const maxX = Math.max(0, (imageWidth - containerWidth) / 2);
    const maxY = Math.max(0, (imageHeight - containerHeight) / 2);

    // Constrain x and y
    x = Math.max(-maxX, Math.min(x, maxX));
    y = Math.max(-maxY, Math.min(y, maxY));

    // Update position data
    dataset.x = x.toString();
    dataset.y = y.toString();

    // Apply transform - only translate, scaling handled by container size
    target.style.transform = `translate(${x}px, ${y}px)`;
  }

  /**
   * Bind keyboard shortcuts (escape and arrow keys).
   */
  private bindKeys(): void {
    this.keyboardHandler = (event: KeyboardEvent) => {
      // Only handle if viewer is active
      if (!this.container || !this.backdrop) {
        return;
      }

      switch (event.keyCode || event.which) {
        case 27: // Esc
          this.cleanup();
          event.preventDefault();
          event.stopPropagation();
          break;
        case 37: // Left Arrow
          if (this.images.length > 1) {
            this.navigateImage(-1);
            event.preventDefault();
            event.stopPropagation();
          }
          break;
        case 39: // Right Arrow
          if (this.images.length > 1) {
            this.navigateImage(1);
            event.preventDefault();
            event.stopPropagation();
          }
          break;
      }
    };
    document.addEventListener('keydown', this.keyboardHandler);
  }

  /**
   * Unbind keyboard shortcuts.
   */
  private unbindKeys(): void {
    if (this.keyboardHandler) {
      document.removeEventListener('keydown', this.keyboardHandler);
      this.keyboardHandler = null;
    }
  }

  /**
   * Get page width (viewport width).
   */
  private getPageWidth(): number {
    return window.innerWidth || document.documentElement.clientWidth;
  }

  /**
   * Get page height (viewport height).
   */
  private getPageHeight(): number {
    return window.innerHeight || document.documentElement.clientHeight;
  }

  /**
   * Cleanup and close the viewer.
   */
  private cleanup(): void {
    this.unbindKeys();
    
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler);
      this.resizeHandler = null;
    }

    if (this.interactInstance) {
      this.interactInstance.unset();
      this.interactInstance = null;
    }

    // Remove backdrop and container from DOM
    if (this.backdrop && this.backdrop.parentNode) {
      this.backdrop.parentNode.removeChild(this.backdrop);
      this.backdrop = null;
    }

    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
      this.container = null;
    }

    // Restore body scroll
    document.body.style.overflow = '';
  }

  /**
   * Static factory method to open viewer from an image link.
   */
  static async openFromImageLink(pageId: number, imageId: number): Promise<void> {
    const viewer = new ImageViewer(pageId, imageId);
    await viewer.show();
  }
}


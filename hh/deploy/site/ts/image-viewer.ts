/**
 * ImageViewer - Full-screen image viewer overlay with pan/zoom support.
 * Ported from legacy/core/js/image.js
 */

import { OverlayManager } from './overlay/overlay-manager.js';
import { Overlay } from './overlay/overlay.js';
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
  private overlay: Overlay | null = null;
  private pageId: number;
  private images: ImageData[] = [];
  private currentImageIndex: number = 0;
  private touchStartX: number | null = null;
  private touchStartY: number | null = null;
  private keyboardHandler: ((e: KeyboardEvent) => void) | null = null;
  private resizeHandler: (() => void) | null = null;
  private interactInstance: any = null;

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
   * Render the overlay with current image.
   */
  private renderOverlay(): void {
    if (this.images.length === 0) {
      return;
    }

    const currentImage = this.images[this.currentImageIndex];
    const pageWidth = this.getPageWidth();
    const pageHeight = this.getPageHeight();

    const maxOverlayWidth = pageWidth - 40;
    const maxOverlayHeight = pageHeight - 40;
    const maxImageWidth = maxOverlayWidth - 40;
    const maxImageHeight = maxOverlayHeight - 80;

    // Get best instance for display
    const displayInstance = this.getBestInstance(maxImageWidth, currentImage.instances);
    if (!displayInstance) {
      console.error('No display instance found');
      return;
    }

    // Calculate display dimensions
    const displayDims = this.calculateDisplayDimensions(
      displayInstance,
      maxImageWidth,
      maxImageHeight
    );

    const imageWidth = displayDims.width;
    const imageHeight = displayDims.height;
    const overlayWidth = imageWidth + 40;
    const overlayHeight = imageHeight + 80;

    // Store base dimensions for zoom calculations
    this.baseImageWidth = imageWidth;
    this.baseImageHeight = imageHeight;
    this.baseOverlayWidth = overlayWidth;
    this.baseOverlayHeight = overlayHeight;

    // Calculate special point scales
    const viewportWidth = this.getPageWidth();
    const viewportHeight = this.getPageHeight();
    this.scaleForWidthMatch = viewportWidth / imageWidth;
    this.scaleForHeightMatch = viewportHeight / imageHeight;

    // Reset pan and scale for new image
    this.currentScale = 1.0;
    this.panX = 0;
    this.panY = 0;

    // Format image src with /srv/images/ prefix
    const imageSrc = displayInstance.src.startsWith('/srv/images/') 
      ? displayInstance.src 
      : `/srv/images/${displayInstance.src}`;

    // Build HTML
    const imageHtml = `
      <div id="imageViewerTargetImageWrapper">
        <div id="imageZoomContainer">
          <img id="imageViewerTargetImage" src="${imageSrc}" alt="${currentImage.caption}" width="${imageWidth}" height="${imageHeight}">
        </div>
      </div>
    `;

    let controlLinks = '<div id="imageViewerControlLinks">';
    if (this.images.length > 1) {
      controlLinks += `<a id="retargetImageViewerToPreviousLink">&lt;&lt;</a>`;
      controlLinks += `${this.currentImageIndex + 1}/${this.images.length}`;
      controlLinks += `<a id="retargetImageViewerToNextLink">&gt;&gt;</a>`;
    }
    controlLinks += '<a id="closeImageViewerLink">close</a>';
    controlLinks += '</div>';

    let visibilityString = '<div id="imageViewerVisibility">';
    switch (currentImage.visibility.toString()) {
      case '-1':
        visibilityString += 'PRIVATE';
        break;
      case '0':
        visibilityString += 'HIDDEN';
        break;
      default:
        // Public - no label
        break;
    }
    visibilityString += '</div>';

    const captionHtml = `<div id="imageViewerCaption">${currentImage.caption}</div>`;

    // Preload full-size image (largest instance, which is last in sorted array)
    const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
    const fullSizeSrc = fullSizeInstance.src.startsWith('/srv/images/') 
      ? fullSizeInstance.src 
      : `/srv/images/${fullSizeInstance.src}`;
    const preloadImg = new Image();
    preloadImg.src = fullSizeSrc;

    const overlayManager = OverlayManager.getInstance();
    this.overlay = overlayManager.show({
      header: '',
      content: [imageHtml + visibilityString + captionHtml + controlLinks],
      contentHeaders: [''],
      closable: true,
      showSubmit: false,
      onCancel: () => {
        this.cleanup();
      }
    });

    // Get the overlay window element
    const windowEl = (this.overlay as any).windowEl;
    if (!windowEl) {
      console.error('Could not find overlay window element');
      return;
    }

    // Set overlay dimensions and center it
    // The overlay system uses position: fixed with top: 50% and left: 50%
    // We need to set transform to center it properly and override default overlay CSS
    windowEl.style.width = `${overlayWidth}px`;
    windowEl.style.height = `${overlayHeight}px`;
    windowEl.style.maxWidth = `${overlayWidth}px`;
    windowEl.style.maxHeight = `${overlayHeight}px`;
    windowEl.style.position = 'fixed';
    windowEl.style.top = '50%';
    windowEl.style.left = '50%';
    windowEl.style.transform = 'translate(-50%, -50%)';
    windowEl.style.marginLeft = '0';
    windowEl.style.marginTop = '0';

    // Set image wrapper dimensions
    const imageWrapper = windowEl.querySelector('#imageViewerTargetImageWrapper') as HTMLElement;
    if (imageWrapper) {
      imageWrapper.style.width = `${imageWidth}px`;
      imageWrapper.style.height = `${imageHeight}px`;
    }

    // Set caption and control links width
    const caption = windowEl.querySelector('#imageViewerCaption') as HTMLElement;
    const controlLinksEl = windowEl.querySelector('#imageViewerControlLinks') as HTMLElement;
    if (caption) caption.style.width = `${overlayWidth - 36}px`;
    if (controlLinksEl) controlLinksEl.style.width = `${overlayWidth - 36}px`;

    // Set up interact.js after a short delay
    setTimeout(() => {
      this.setupInteract();
      this.setupEventHandlers(windowEl);
      this.bindKeys();
    }, 50);
  }

  /**
   * Set up interact.js for pan/zoom.
   */
  private setupInteract(): void {
    const zoomContainer = document.getElementById('imageZoomContainer');
    if (!zoomContainer) {
      return;
    }

    // Initialize transform data
    (zoomContainer as any).dataset.scale = '1';
    (zoomContainer as any).dataset.x = '0';
    (zoomContainer as any).dataset.y = '0';
    (zoomContainer as any).dataset.fullsize = 'false';

    // Set initial transform
    zoomContainer.style.transform = 'scale(1)';
    zoomContainer.style.transformOrigin = 'center center';

    // Set up interact.js
    this.interactInstance = interact(zoomContainer)
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

    // Get overlay position in viewport
    const overlayWrapper = document.getElementById('imageViewerTargetImageWrapper');
    const overlayWindow = overlayWrapper?.closest('#overlayWindow') as HTMLElement;
    if (!overlayWrapper || !overlayWindow) {
      return { x: panX, y: panY };
    }

    const overlayRect = overlayWindow.getBoundingClientRect();
    const overlayCenterX = overlayRect.left + overlayRect.width / 2;
    const overlayCenterY = overlayRect.top + overlayRect.height / 2;

    // Calculate image bounds in viewport coordinates
    // Image is centered in overlay, so offset from overlay center
    const imageLeft = overlayCenterX - scaledImageWidth / 2 + panX;
    const imageRight = overlayCenterX + scaledImageWidth / 2 + panX;
    const imageTop = overlayCenterY - scaledImageHeight / 2 + panY;
    const imageBottom = overlayCenterY + scaledImageHeight / 2 + panY;

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
    const overlayWindow = document.querySelector('#overlayWindow') as HTMLElement;
    if (!overlayWindow) return;

    const scaledWidth = this.baseOverlayWidth * scale;
    const scaledHeight = this.baseOverlayHeight * scale;

    overlayWindow.style.width = `${scaledWidth}px`;
    overlayWindow.style.height = `${scaledHeight}px`;
    overlayWindow.style.maxWidth = `${scaledWidth}px`;
    overlayWindow.style.maxHeight = `${scaledHeight}px`;
  }

  /**
   * Handle drag start.
   */
  private onDragStart(event: any): void {
    // Store initial pan position
    const zoomContainer = event.target;
    const dataset = (zoomContainer as any).dataset;
    dataset.initialPanX = this.panX.toString();
    dataset.initialPanY = this.panY.toString();
  }

  /**
   * Handle drag move with state-based constraints.
   */
  private onDragMove(event: any): void {
    const zoomContainer = event.target;
    const dataset = (zoomContainer as any).dataset;
    
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
    zoomContainer.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.currentScale})`;
  }

  /**
   * Handle drag end.
   */
  private onDragEnd(event: any): void {
    // Pan constraints are already applied in onDragMove
  }

  /**
   * Set up event handlers for navigation and controls.
   */
  private setupEventHandlers(windowEl: HTMLElement): void {
    // Previous/Next navigation
    const prevLink = windowEl.querySelector('#retargetImageViewerToPreviousLink') as HTMLElement;
    const nextLink = windowEl.querySelector('#retargetImageViewerToNextLink') as HTMLElement;
    const closeLink = windowEl.querySelector('#closeImageViewerLink') as HTMLElement;

    if (prevLink) {
      prevLink.addEventListener('click', () => {
        this.navigateImage(-1);
      });
    }

    if (nextLink) {
      nextLink.addEventListener('click', () => {
        this.navigateImage(1);
      });
    }

    if (closeLink) {
      closeLink.addEventListener('click', () => {
        this.cleanup();
      });
    }

    // Touch handlers for swipe navigation
    const imageWrapper = windowEl.querySelector('#imageViewerTargetImageWrapper') as HTMLElement;
    if (imageWrapper) {
      imageWrapper.addEventListener('touchstart', (e) => this.handleTouchStart(e));
      imageWrapper.addEventListener('touchmove', (e) => this.handleTouchMove(e));
      imageWrapper.addEventListener('touchend', (e) => this.handleTouchEnd(e));
    }

    // Wheel zoom
    if (imageWrapper) {
      imageWrapper.addEventListener('wheel', (e) => this.handleWheelZoom(e));
    }

    // Window resize handler
    this.resizeHandler = () => {
      this.navigateImage(0); // Re-render with new dimensions
    };
    window.addEventListener('resize', this.resizeHandler);
  }

  /**
   * Navigate to a different image.
   */
  private navigateImage(increment: number): void {
    if (this.images.length === 0 || !this.overlay) {
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
    if (!this.overlay || this.images.length === 0) {
      return;
    }

    const currentImage = this.images[this.currentImageIndex];
    const pageWidth = this.getPageWidth();
    const pageHeight = this.getPageHeight();

    const maxOverlayWidth = pageWidth - 40;
    const maxOverlayHeight = pageHeight - 40;
    const maxImageWidth = maxOverlayWidth - 40;
    const maxImageHeight = maxOverlayHeight - 80;

    // Get best instance for display
    const displayInstance = this.getBestInstance(maxImageWidth, currentImage.instances);
    if (!displayInstance) {
      console.error('No display instance found');
      return;
    }

    // Calculate display dimensions
    const displayDims = this.calculateDisplayDimensions(
      displayInstance,
      maxImageWidth,
      maxImageHeight
    );

    const imageWidth = displayDims.width;
    const imageHeight = displayDims.height;
    const overlayWidth = imageWidth + 40;
    const overlayHeight = imageHeight + 80;

    // Format image src with /srv/images/ prefix
    const imageSrc = displayInstance.src.startsWith('/srv/images/') 
      ? displayInstance.src 
      : `/srv/images/${displayInstance.src}`;

    // Get the overlay window element
    const windowEl = (this.overlay as any).windowEl;
    if (!windowEl) {
      console.error('Could not find overlay window element');
      return;
    }

    // Update image
    const img = windowEl.querySelector('#imageViewerTargetImage') as HTMLImageElement;
    if (img) {
      // Add fade transition
      img.style.transition = 'opacity 0.2s';
      img.style.opacity = '0';
      
      setTimeout(() => {
        img.src = imageSrc;
        img.width = imageWidth;
        img.height = imageHeight;
        img.alt = currentImage.caption;
        img.style.opacity = '1';
      }, 100);
    }

    // Reset zoom container
    const zoomContainer = windowEl.querySelector('#imageZoomContainer') as HTMLElement;
    if (zoomContainer) {
      (zoomContainer as any).dataset.scale = '1';
      (zoomContainer as any).dataset.x = '0';
      (zoomContainer as any).dataset.y = '0';
      (zoomContainer as any).dataset.fullsize = 'false';
      zoomContainer.style.transform = 'scale(1)';
      zoomContainer.style.transformOrigin = 'center center';
    }

    // Update dimensions
    windowEl.style.width = `${overlayWidth}px`;
    windowEl.style.height = `${overlayHeight}px`;
    windowEl.style.maxWidth = `${overlayWidth}px`;
    windowEl.style.maxHeight = `${overlayHeight}px`;

    // Update image wrapper dimensions
    const imageWrapper = windowEl.querySelector('#imageViewerTargetImageWrapper') as HTMLElement;
    if (imageWrapper) {
      imageWrapper.style.width = `${imageWidth}px`;
      imageWrapper.style.height = `${imageHeight}px`;
    }

    // Update caption
    const caption = windowEl.querySelector('#imageViewerCaption') as HTMLElement;
    if (caption) {
      caption.textContent = currentImage.caption;
      caption.style.width = `${overlayWidth - 36}px`;
    }

    // Update visibility
    const visibility = windowEl.querySelector('#imageViewerVisibility') as HTMLElement;
    if (visibility) {
      let visibilityText = '';
      switch (currentImage.visibility.toString()) {
        case '-1':
          visibilityText = 'PRIVATE';
          break;
        case '0':
          visibilityText = 'HIDDEN';
          break;
        default:
          visibilityText = '';
          break;
      }
      visibility.textContent = visibilityText;
    }

    // Update control links
    const controlLinks = windowEl.querySelector('#imageViewerControlLinks') as HTMLElement;
    if (controlLinks) {
      let linksHtml = '';
      if (this.images.length > 1) {
        linksHtml = `<a id="retargetImageViewerToPreviousLink">&lt;&lt;</a>${this.currentImageIndex + 1}/${this.images.length}<a id="retargetImageViewerToNextLink">&gt;&gt;</a>`;
      }
      linksHtml += '<a id="closeImageViewerLink">close</a>';
      controlLinks.innerHTML = linksHtml;
      controlLinks.style.width = `${overlayWidth - 36}px`;
      
      // Re-attach event handlers
      const prevLink = windowEl.querySelector('#retargetImageViewerToPreviousLink') as HTMLElement;
      const nextLink = windowEl.querySelector('#retargetImageViewerToNextLink') as HTMLElement;
      const closeLink = windowEl.querySelector('#closeImageViewerLink') as HTMLElement;
      
      if (prevLink) {
        prevLink.addEventListener('click', () => this.navigateImage(-1));
      }
      if (nextLink) {
        nextLink.addEventListener('click', () => this.navigateImage(1));
      }
      if (closeLink) {
        closeLink.addEventListener('click', () => this.cleanup());
      }
    }

    // Preload full-size image
    const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
    const fullSizeSrc = fullSizeInstance.src.startsWith('/srv/images/') 
      ? fullSizeInstance.src 
      : `/srv/images/${fullSizeInstance.src}`;
    const preloadImg = new Image();
    preloadImg.src = fullSizeSrc;

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
  }

  /**
   * Handle touch move - prevent scrolling if not zoomed.
   */
  private handleTouchMove(event: TouchEvent): void {
    const zoomContainer = document.getElementById('imageZoomContainer');
    if (!zoomContainer) return;

    const scale = parseFloat((zoomContainer as any).dataset.scale) || 1;
    if (scale === 1) {
      // Only prevent default scrolling if not zoomed in
      event.preventDefault();
    }
  }

  /**
   * Handle touch end - detect swipe gestures.
   */
  private handleTouchEnd(event: TouchEvent): void {
    const zoomContainer = document.getElementById('imageZoomContainer');
    if (!zoomContainer) return;

    const scale = parseFloat((zoomContainer as any).dataset.scale) || 1;
    if (scale === 1 && this.touchStartX !== null && this.touchStartY !== null) {
      const touch = event.changedTouches[0];
      const touchEndX = touch.clientX;
      const touchEndY = touch.clientY;

      const deltaX = touchEndX - this.touchStartX;
      const deltaY = touchEndY - this.touchStartY;

      // Check if the swipe is horizontal and long enough
      if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
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
  }

  /**
   * Handle wheel zoom.
   */
  private handleWheelZoom(event: WheelEvent): void {
    event.preventDefault();

    const zoomContainer = document.getElementById('imageZoomContainer');
    if (!zoomContainer) return;

    let scale = this.currentScale;

    // Load full-size image if not already loaded
    if (!(zoomContainer as any).dataset.fullsize || (zoomContainer as any).dataset.fullsize === 'false') {
      const currentImage = this.images[this.currentImageIndex];
      const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
      const fullSizeSrc = fullSizeInstance.src.startsWith('/srv/images/') 
        ? fullSizeInstance.src 
        : `/srv/images/${fullSizeInstance.src}`;
      const img = zoomContainer.querySelector('img') as HTMLImageElement;
      if (img) {
        img.src = fullSizeSrc;
      }
      (zoomContainer as any).dataset.fullsize = 'true';
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

    // Update transforms
    (zoomContainer as any).dataset.scale = scale.toString();
    zoomContainer.style.transformOrigin = 'center center';
    zoomContainer.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${scale})`;
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

    scale = Math.max(minScale, Math.min(maxScale, scale));
    this.currentScale = scale;

    // Update overlay size
    this.updateOverlaySize(scale);

    const initialX = parseFloat(dataset.initialX) || 0;
    const initialY = parseFloat(dataset.initialY) || 0;

    // Calculate pan from gesture (deltaX/deltaY are relative to initial position)
    const newPanX = initialX + event.deltaX;
    const newPanY = initialY + event.deltaY;

    // Apply constraints based on zoom state
    const constrained = this.applyPanConstraints(scale, newPanX, newPanY);
    this.panX = constrained.x;
    this.panY = constrained.y;

    dataset.scale = scale.toString();
    dataset.x = this.panX.toString();
    dataset.y = this.panY.toString();

    target.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${scale})`;
    target.style.transformOrigin = 'center center';
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

    // Apply transform
    target.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
  }

  /**
   * Bind keyboard shortcuts.
   */
  private bindKeys(): void {
    this.keyboardHandler = (event: KeyboardEvent) => {
      switch (event.keyCode || event.which) {
        case 27: // Esc
          this.cleanup();
          event.preventDefault();
          break;
        case 37: // Left Arrow
          if (this.images.length > 1) {
            this.navigateImage(-1);
            event.preventDefault();
          }
          break;
        case 39: // Right Arrow
          if (this.images.length > 1) {
            this.navigateImage(1);
            event.preventDefault();
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

    if (this.overlay) {
      // Overlay cleanup is handled by OverlayManager
      this.overlay = null;
    }
  }

  /**
   * Static factory method to open viewer from an image link.
   */
  static async openFromImageLink(pageId: number, imageId: number): Promise<void> {
    const viewer = new ImageViewer(pageId, imageId);
    await viewer.show();
  }
}


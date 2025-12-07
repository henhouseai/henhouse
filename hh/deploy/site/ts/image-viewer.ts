/**
 * ImageViewer - Image group viewer integrated with overlay system.
 * Uses OverlayManager for modal handling, provides pan/zoom/touch functionality.
 */

import { RPCClient } from './rpc-client.js';
import { OverlayManager } from './overlay/overlay-manager.js';
import { Overlay } from './overlay/overlay.js';

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
  private windowEl: HTMLElement | null = null;
  private headerEl: HTMLElement | null = null;
  private contentEl: HTMLElement | null = null;
  private footerEl: HTMLElement | null = null;
  private headerHeight = 0;
  private footerHeight = 0;
  private readonly pageId: number;
  private readonly initialImageId?: number;

  private currentScale = 1;
  private panX = 0;
  private panY = 0;
  private scaleForWidthMatch = 1;
  private scaleForHeightMatch = 1;
  private detentActive = false;

  private resizeHandler: (() => void) | null = null;
  private keyboardHandler: ((e: KeyboardEvent) => void) | null = null;

  // Layout state
  private baseOverlayWidth = 0;
  private baseOverlayHeight = 0;
  private totalExtraX = 0;
  private totalExtraY = 0;
  private baseInnerWidth = 0;
  private baseInnerHeight = 0;
  private intrinsicWidth = 0;
  private intrinsicHeight = 0;
  private pinchStartDist: number | null = null;
  private pinchStartScale = 1;
  private swipeStartX: number | null = null;
  private swipeStartY: number | null = null;
  private swipeStartTime: number | null = null;

  private images: ImageData[] = [];
  private currentImageIndex = 0;
  private cleanupFns: Array<() => void> = [];

  constructor(pageId: number, initialImageId?: number) {
    this.rpc = new RPCClient();
    this.pageId = pageId;
    this.initialImageId = initialImageId;
  }

  async show(): Promise<void> {
    await this.loadAndRender();
  }

  // ---- Data + Rendering --------------------------------------------------

  private async loadAndRender(): Promise<void> {
    try {
      const result = await this.rpc.call('get_image_group', { id: this.pageId });
      const groupData = result.data as ImageGroupResponse;
      if (!groupData || !groupData.images || groupData.images.length === 0) {
        throw new Error('No images found in image group');
      }
      this.images = groupData.images;
      if (this.initialImageId !== undefined) {
        const idx = this.images.findIndex(img => img.id === this.initialImageId);
        if (idx >= 0) this.currentImageIndex = idx;
      }
      this.renderOverlay();
    } catch (err) {
      console.error('Error loading image viewer:', err);
      this.rpc.showError('image_viewer', err);
    }
  }

  private renderOverlay(): void {
    const image = this.images[this.currentImageIndex];
    const instance = image.instances[image.instances.length - 1]; // largest
    this.intrinsicWidth = instance.width;
    this.intrinsicHeight = instance.height;

    // Create the image element
    const imageContainer = this.createImageElement(image, instance);

    // Create footer element for caption (same styling as header)
    const footerEl = document.createElement('div');
    // Keep footer styling aligned with header; no extra class needed for sizing
    footerEl.className = 'contentWrapperHeader overlay';
    footerEl.textContent = image.caption || '';
    this.footerEl = footerEl;

    // Show overlay using OverlayManager
    const overlayManager = OverlayManager.getInstance();
    this.overlay = overlayManager.show({
      header: 'Image Viewer',
      content: [imageContainer],
      imageViewerMode: true,
      footerContent: footerEl,
      closable: true,
      showSubmit: false,
      cancelLabel: 'Close',
      mode: 'zoomable',
      onCancel: () => this.cleanup(),
      onUnmount: () => this.cleanupHandlers()
    });

    // Get references to overlay elements for pan/zoom
    this.windowEl = this.overlay?.getWindowElement ? this.overlay.getWindowElement() : null;
    this.headerEl = this.overlay?.getHeaderElement ? this.overlay.getHeaderElement() : this.windowEl?.querySelector('.contentWrapperHeader') || null;
    this.contentEl = this.windowEl?.querySelector('.contentWrapper') || null;
    this.footerEl = this.footerEl || this.windowEl?.querySelector('.overlay-footer') || null;

    // Measure header and footer heights
    this.measureChromeHeights();

    // Prevent body scroll while overlay is open
    document.body.style.overflow = 'hidden';

    // Initial sizing and inflection thresholds
    this.initializeBaseSizes(this.intrinsicWidth, this.intrinsicHeight);
    this.currentScale = 1;
    this.applyTransforms(1);

    // Re-measure after layout settle to capture footer/header height accurately
    requestAnimationFrame(() => {
      this.measureChromeHeights();
      this.initializeBaseSizes(this.intrinsicWidth, this.intrinsicHeight);
      this.applyTransforms(this.currentScale);
      // Second pass after layout to ensure overflow-based pan gating uses real dimensions
      requestAnimationFrame(() => this.applyTransforms(this.currentScale));
    });

    this.bindEvents();
  }

  private createImageElement(image: ImageData, instance: ImageInstance): HTMLElement {
    const box = document.createElement('div');
    box.id = 'imageViewerTargetImage';
    box.className = 'image-viewer-box';
    box.style.boxSizing = 'border-box';
    // Dimensions will be set by initializeBaseSizes/applyTransforms

    const img = document.createElement('img');
    img.id = 'imageViewerImg';
    img.className = 'image-viewer-img';
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'contain';
    const src = instance.src.startsWith('/srv/images/') ? instance.src : `/srv/images/${instance.src}`;
    img.src = src;
    img.alt = image.caption || '';

    box.appendChild(img);
    return box;
  }

  private updateImageContent(): void {
    if (!this.contentEl) return;
    const image = this.images[this.currentImageIndex];
    const instance = image.instances[image.instances.length - 1]; // largest
    this.intrinsicWidth = instance.width;
    this.intrinsicHeight = instance.height;

    const img = this.contentEl.querySelector('#imageViewerImg') as HTMLImageElement | null;
    if (img) {
      const src = instance.src.startsWith('/srv/images/') ? instance.src : `/srv/images/${instance.src}`;
      img.src = src;
      img.alt = image.caption || '';
    }
    if (this.footerEl) {
      this.footerEl.textContent = image.caption || '';
    }

    this.currentScale = 1;
    this.panX = 0;
    this.panY = 0;
    this.detentActive = false;
    this.measureChromeHeights();
    this.initializeBaseSizes(this.intrinsicWidth, this.intrinsicHeight);
    this.applyTransforms(1);
    requestAnimationFrame(() => this.applyTransforms(this.currentScale));
  }

  private initializeBaseSizes(intrinsicW: number, intrinsicH: number): void {
    if (!this.windowEl) return;
    
    // Measure padding/border extras from computed style
    this.measureExtras();

    const vw = this.getPageWidth();
    const vh = this.getPageHeight();
    const margin = 200;
    const maxW = vw - margin;
    // Estimate available height for image (viewport - margin - header - footer - padding)
    const maxH = vh - margin - this.headerHeight - this.footerHeight - this.totalExtraY;

    // Scale to fit, preserving aspect ratio, but only apply width to the window; let height flow
    const scaleX = (maxW - this.totalExtraX) / intrinsicW;
    const scaleY = maxH / intrinsicH;
    const fitScale = Math.min(scaleX, scaleY, 1);

    this.baseInnerWidth = intrinsicW * fitScale;
    this.baseInnerHeight = intrinsicH * fitScale;

    // Width-only apply; height flows
    const initialOverlayWidth = this.baseInnerWidth + this.totalExtraX;
    this.windowEl.style.width = `${initialOverlayWidth}px`;
    this.windowEl.style.height = '';
    this.windowEl.style.maxHeight = '';

    // Adjust width iteratively to fit available height (within 1px tolerance)
    const targetHeight = vh - margin;
    const adjusted = this.adjustWidthToFit(targetHeight, maxW, 50, 1);
    this.baseOverlayWidth = adjusted.width;
    this.baseOverlayHeight = adjusted.height;

    this.recomputeInflections();
  }

  private recomputeInflections(): void {
    const vw = this.getPageWidth();
    const vh = this.getPageHeight();
    this.scaleForWidthMatch = vw / this.baseOverlayWidth;
    this.scaleForHeightMatch = vh / this.baseOverlayHeight;
  }

  private measureExtras(): void {
    if (!this.windowEl) return;
    const cs = getComputedStyle(this.windowEl);
    const padX = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
    const padY = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);
    const borderX = (parseFloat(cs.borderLeftWidth) || 0) + (parseFloat(cs.borderRightWidth) || 0);
    const borderY = (parseFloat(cs.borderTopWidth) || 0) + (parseFloat(cs.borderBottomWidth) || 0);
    this.totalExtraX = padX + borderX;
    this.totalExtraY = padY + borderY;
  }

  // ---- Transform and state ----------------------------------------------

  private applyTransforms(scale: number): void {
    if (!this.windowEl) return;
    const innerW = this.baseInnerWidth * scale;
    const innerH = this.baseInnerHeight * scale;
    const overlayW = innerW + this.totalExtraX;
    const overlayH = innerH + this.totalExtraY + this.headerHeight + this.footerHeight;

    // Width-only apply; let height auto. Do not refit during zoom to avoid jitter.
    this.windowEl.style.width = `${overlayW}px`;
    this.windowEl.style.height = '';
    this.windowEl.style.maxWidth = `${overlayW}px`;
    this.windowEl.style.maxHeight = '';

    // Use current rendered dimensions for clamping
    const effectiveW = this.windowEl.offsetWidth || overlayW;
    const effectiveH = this.windowEl.offsetHeight || overlayH;

    const clamped = this.clampPan(this.panX, this.panY, effectiveW, effectiveH);
    this.panX = clamped.x;
    this.panY = clamped.y;
    this.windowEl.style.transform = `translate(-50%, -50%) translate(${this.panX}px, ${this.panY}px)`;
  }

  private applyScale(newScale: number, oldScale: number): void {
    const first = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
    // Cap so displayed pixels do not exceed 4x intrinsic
    const pixelPerDisplay = this.baseInnerWidth > 0 ? this.baseInnerWidth / this.intrinsicWidth : 1;
    const maxScale = Math.max(1, 4 / pixelPerDisplay);

    if (!this.detentActive && oldScale < first && newScale >= first) {
      newScale = first;
      this.detentActive = true;
    } else if (this.detentActive && newScale > first) {
      this.detentActive = false;
    }
    if (newScale < first) {
      this.detentActive = false;
    }

    newScale = Math.max(1, Math.min(maxScale, newScale));
    this.currentScale = newScale;

    const oldState = this.getZoomState(oldScale);
    const newState = this.getZoomState(newScale);
    if (oldState !== 'zoomedOut' && newState === 'zoomedOut') {
      this.panX = 0;
      this.panY = 0;
    }

    this.applyTransforms(newScale);
  }

  private getZoomState(scale: number): 'zoomedOut' | 'between' | 'zoomedIn' {
    const first = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
    const second = Math.max(this.scaleForWidthMatch, this.scaleForHeightMatch);
    if (scale <= first + 1e-3) return 'zoomedOut';
    if (scale < second - 1e-3) return 'between';
    return 'zoomedIn';
  }

  private clampPan(panX: number, panY: number, actualWidth: number, actualHeight: number): { x: number; y: number } {
    // Determine overflow per axis based on current rendered size vs viewport
    const vw = this.getPageWidth();
    const vh = this.getPageHeight();
    const overflowX = Math.max(0, actualWidth - vw);
    const overflowY = Math.max(0, actualHeight - vh);
    const halfOverflowX = overflowX / 2;
    const halfOverflowY = overflowY / 2;

    const xOver = overflowX > 0;
    const yOver = overflowY > 0;

    if (!xOver && !yOver) {
      return { x: 0, y: 0 };
    }
    if (xOver && !yOver) {
      return { x: Math.max(-halfOverflowX, Math.min(halfOverflowX, panX)), y: 0 };
    }
    if (!xOver && yOver) {
      return { x: 0, y: Math.max(-halfOverflowY, Math.min(halfOverflowY, panY)) };
    }
    return {
      x: Math.max(-halfOverflowX, Math.min(halfOverflowX, panX)),
      y: Math.max(-halfOverflowY, Math.min(halfOverflowY, panY))
    };
  }

  // ---- Input handlers ----------------------------------------------------

  private handleWheel = (e: WheelEvent) => {
    e.preventDefault();
    const oldScale = this.currentScale;
    const sens = 0.1;
    const delta = e.deltaY < 0 ? sens : -sens;
    const newScale = oldScale + delta;
    this.applyScale(newScale, oldScale);
  };

  private handleDragMove = (dx: number, dy: number) => {
    const state = this.getZoomState(this.currentScale);
    const widthHitsFirst = this.scaleForWidthMatch < this.scaleForHeightMatch;
    let newPanX = this.panX + dx;
    let newPanY = this.panY + dy;
    if (state === 'between') {
      if (widthHitsFirst) {
        newPanY = 0;
      } else {
        newPanX = 0;
      }
    }
    this.panX = newPanX;
    this.panY = newPanY;
    this.applyTransforms(this.currentScale);
  };

  // ---- Events binding ----------------------------------------------------

  private bindEvents(): void {
    if (!this.windowEl) return;
    
    // Wheel zoom on window
    this.windowEl.addEventListener('wheel', this.handleWheel, { passive: false });
    this.cleanupFns.push(() => this.windowEl?.removeEventListener('wheel', this.handleWheel));
    window.addEventListener('wheel', this.handleWheel, { passive: false });
    this.cleanupFns.push(() => window.removeEventListener('wheel', this.handleWheel));

    // Mouse drag for pan
    let dragging = false;
    let lastX = 0, lastY = 0;
    const onMouseDown = (e: MouseEvent) => { e.preventDefault(); dragging = true; lastX = e.clientX; lastY = e.clientY; };
    const onMouseUp = () => { dragging = false; };
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX; lastY = e.clientY;
      this.handleDragMove(dx, dy);
    };
    this.windowEl.addEventListener('mousedown', onMouseDown);
    this.windowEl.addEventListener('mouseup', onMouseUp);
    this.windowEl.addEventListener('mouseleave', onMouseUp);
    document.addEventListener('mouseup', onMouseUp);
    document.addEventListener('mousemove', onMouseMove);
    this.cleanupFns.push(() => {
      this.windowEl?.removeEventListener('mousedown', onMouseDown);
      this.windowEl?.removeEventListener('mouseup', onMouseUp);
      this.windowEl?.removeEventListener('mouseleave', onMouseUp);
      document.removeEventListener('mouseup', onMouseUp);
      document.removeEventListener('mousemove', onMouseMove);
    });

    // Touch handling: pinch zoom + drag pan
    const onPinchMove = (touches: TouchList) => {
      if (touches.length !== 2 || this.pinchStartDist === null) return;
      const dist = this.getTouchDistance(touches);
      if (dist > 0) {
        const proposedScale = this.pinchStartScale * (dist / this.pinchStartDist);
        // Clamp and reset baseline at max to prevent rubber-band stretch
        const first = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
        const pixelPerDisplay = this.baseInnerWidth > 0 ? this.baseInnerWidth / this.intrinsicWidth : 1;
        const maxScale = Math.max(1, 4 / pixelPerDisplay);
        let newScale = Math.max(1, Math.min(maxScale, proposedScale));
        if (newScale === this.currentScale && proposedScale > newScale) {
          // Already at max; ignore further pinch-in
          return;
        }
        if (newScale === maxScale && proposedScale >= maxScale) {
          // Reset pinch baseline so further pinch-in doesn’t accumulate
          this.pinchStartScale = newScale;
          this.pinchStartDist = dist;
        }
        this.applyScale(newScale, this.currentScale);
      }
    };

    const startPinch = (e: TouchEvent) => {
      this.pinchStartDist = this.getTouchDistance(e.touches);
      this.pinchStartScale = this.currentScale;
    };

    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        startPinch(e);
        dragging = false;
        this.swipeStartX = null;
        this.swipeStartY = null;
        this.swipeStartTime = null;
      } else if (e.touches.length === 1) {
        const t = e.touches[0];
        lastX = t.clientX; lastY = t.clientY; dragging = true;
        this.swipeStartX = t.clientX;
        this.swipeStartY = t.clientY;
        this.swipeStartTime = e.timeStamp;
      }
    };
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 1 && this.currentScale === 1) {
        e.preventDefault();
      }
      if (e.touches.length === 2) {
        e.preventDefault();
        dragging = false;
        if (this.pinchStartDist) onPinchMove(e.touches);
        return;
      }
      if (!dragging) return;
      const t = e.touches[0];
      const dx = t.clientX - lastX;
      const dy = t.clientY - lastY;
      lastX = t.clientX; lastY = t.clientY;
      this.handleDragMove(dx, dy);
    };
    const onTouchEnd = (e: TouchEvent) => {
      dragging = false;

      // Swipe navigation: only when at default scale
      if (this.images.length > 1 && this.currentScale === 1 && this.swipeStartX !== null && this.swipeStartY !== null && this.swipeStartTime !== null) {
        const touch = e.changedTouches[0];
        const dx = touch.clientX - this.swipeStartX;
        const dy = touch.clientY - this.swipeStartY;
        const dt = e.timeStamp - this.swipeStartTime;
        const dist = Math.hypot(dx, dy);
        const isHorizontal = Math.abs(dx) > Math.abs(dy);
        const velocity = dt > 0 ? dist / dt : 0;
        const minSwipeDistance = 100;
        const minSwipeVelocity = 0.3;
        if (isHorizontal && (dist >= minSwipeDistance || velocity >= minSwipeVelocity)) {
          if (dx > 0) this.navigate(-1); else this.navigate(1);
        }
      }

      this.swipeStartX = null;
      this.swipeStartY = null;
      this.swipeStartTime = null;
      this.pinchStartDist = null;
    };

    this.windowEl.addEventListener('touchstart', onTouchStart, { passive: false });
    this.windowEl.addEventListener('touchmove', onTouchMove, { passive: false });
    this.windowEl.addEventListener('touchend', onTouchEnd, { passive: false });
    this.cleanupFns.push(() => {
      this.windowEl?.removeEventListener('touchstart', onTouchStart);
      this.windowEl?.removeEventListener('touchmove', onTouchMove);
      this.windowEl?.removeEventListener('touchend', onTouchEnd);
    });

    // Block scroll/zoom on backdrop
    const backdrop = document.querySelector('.overlay-backdrop') as HTMLElement | null;
    if (backdrop) {
      const onBackdropWheel = this.handleWheel;
      const onBackdropTouchStart = (e: Event) => {
        const te = e as TouchEvent;
        if (te.touches.length === 2) {
          e.preventDefault();
          startPinch(te);
        }
      };
      const onBackdropTouchMove = (e: Event) => {
        const te = e as TouchEvent;
        if (te.touches.length === 2) {
          e.preventDefault();
          onPinchMove(te.touches);
        }
      };
      const onBackdropTouchEnd = () => {
        this.pinchStartDist = null;
      };
      backdrop.addEventListener('wheel', onBackdropWheel, { passive: false });
      backdrop.addEventListener('touchstart', onBackdropTouchStart, { passive: false });
      backdrop.addEventListener('touchmove', onBackdropTouchMove, { passive: false });
      backdrop.addEventListener('touchend', onBackdropTouchEnd, { passive: false });
      this.cleanupFns.push(() => {
        backdrop.removeEventListener('wheel', onBackdropWheel);
        backdrop.removeEventListener('touchstart', onBackdropTouchStart);
        backdrop.removeEventListener('touchmove', onBackdropTouchMove);
        backdrop.removeEventListener('touchend', onBackdropTouchEnd);
      });
    }

    // Global pinch for two-finger anywhere
    const onWindowTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        startPinch(e);
      }
    };
    const onWindowTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        onPinchMove(e.touches);
      }
    };
    const onWindowTouchEnd = () => {
      this.pinchStartDist = null;
    };
    window.addEventListener('touchstart', onWindowTouchStart, { passive: false });
    window.addEventListener('touchmove', onWindowTouchMove, { passive: false });
    window.addEventListener('touchend', onWindowTouchEnd, { passive: false });
    this.cleanupFns.push(() => {
      window.removeEventListener('touchstart', onWindowTouchStart);
      window.removeEventListener('touchmove', onWindowTouchMove);
      window.removeEventListener('touchend', onWindowTouchEnd);
    });

    this.resizeHandler = () => {
      if (this.intrinsicWidth && this.intrinsicHeight) {
        this.initializeBaseSizes(this.intrinsicWidth, this.intrinsicHeight);
      } else {
        this.recomputeInflections();
      }
      this.currentScale = 1;
      this.panX = 0;
      this.panY = 0;
      this.detentActive = false;
      this.applyTransforms(1);
    };
    window.addEventListener('resize', this.resizeHandler);
    this.cleanupFns.push(() => { if (this.resizeHandler) window.removeEventListener('resize', this.resizeHandler); });

    // Arrow keys for image navigation (ESC handled by overlay system)
    this.keyboardHandler = (e: KeyboardEvent) => {
      if (!this.windowEl) return;
      if (e.key === 'ArrowLeft') { if (this.images.length > 1) { this.navigate(-1); e.preventDefault(); } }
      else if (e.key === 'ArrowRight') { if (this.images.length > 1) { this.navigate(1); e.preventDefault(); } }
    };
    document.addEventListener('keydown', this.keyboardHandler);
    this.cleanupFns.push(() => { if (this.keyboardHandler) document.removeEventListener('keydown', this.keyboardHandler); });
  }

  // ---- Utils -------------------------------------------------------------

  private getPageWidth(): number {
    return window.innerWidth || document.documentElement.clientWidth;
  }

  private getPageHeight(): number {
    return window.innerHeight || document.documentElement.clientHeight;
  }

  private measureChromeHeights(): void {
    this.headerHeight = this.headerEl?.offsetHeight || 0;
    this.footerHeight = this.footerEl?.offsetHeight || 0;
  }

  /**
   * Iteratively adjust overlay width so the rendered height is within tolerance of target.
   * Leaves height auto-flowing; only width is set.
   */
  private adjustWidthToFit(targetHeight: number, maxWidth: number, minWidth: number = 50, tolerance: number = 1): { width: number; height: number } {
    if (!this.windowEl) return { width: 0, height: 0 };
    let width = parseFloat(this.windowEl.style.width || '0') || this.windowEl.offsetWidth || maxWidth;
    width = Math.max(minWidth, Math.min(maxWidth, width));
    this.windowEl.style.width = `${width}px`;

    let height = this.windowEl.offsetHeight || 0;
    for (let i = 0; i < 8; i++) {
      height = this.windowEl.offsetHeight || 0;
      if (height === 0) break;
      const diff = height - targetHeight;
      if (Math.abs(diff) <= tolerance) break;
      // Adjust proportionally toward target height
      const factor = targetHeight > 0 ? targetHeight / height : 1;
      const newWidth = Math.max(minWidth, Math.min(maxWidth, width * factor));
      // If change is negligible, stop
      if (Math.abs(newWidth - width) < 0.5) {
        width = newWidth;
        this.windowEl.style.width = `${width}px`;
        break;
      }
      width = newWidth;
      this.windowEl.style.width = `${width}px`;
    }
    height = this.windowEl.offsetHeight || 0;
    return { width, height };
  }

  private getTouchDistance(touches: TouchList): number {
    if (touches.length < 2) return 0;
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.hypot(dx, dy);
  }

  private navigate(delta: number): void {
    if (!this.images.length) return;
    this.currentImageIndex = (this.currentImageIndex + delta + this.images.length) % this.images.length;
    this.updateImageContent();
  }

  private cleanupHandlers(): void {
    for (const fn of this.cleanupFns) {
      try { fn(); } catch { /* ignore */ }
    }
    this.cleanupFns = [];
    this.resizeHandler = null;
    this.keyboardHandler = null;
    document.body.style.overflow = '';
  }

  private cleanup(): void {
    this.cleanupHandlers();
    this.overlay = null;
    this.windowEl = null;
    this.headerEl = null;
    this.contentEl = null;
    this.footerEl = null;
  }

  static async openFromImageLink(pageId: number, imageId?: number): Promise<void> {
    const viewer = new ImageViewer(pageId, imageId);
    await viewer.show();
  }
}

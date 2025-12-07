/**
 * ImageViewer - single container + single child, scaled/panned via container transform.
 * Uses image aspect ratio from get_image_group to set initial sizing.
 */

import { RPCClient } from './rpc-client.js';

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
    const intrinsicW = instance.width;
    const intrinsicH = instance.height;
    this.intrinsicWidth = intrinsicW;
    this.intrinsicHeight = intrinsicH;

    // Backdrop
    this.backdrop = document.createElement('div');
    this.backdrop.id = 'imageViewerBackdrop';
    Object.assign(this.backdrop.style, {
      position: 'fixed',
      left: '0',
      top: '0',
      width: '100vw',
      height: '100vh',
      background: 'rgba(0,0,0,0.6)',
      zIndex: '1000'
    });
    this.backdrop.addEventListener('click', (e) => {
      if (e.target === this.backdrop) this.cleanup();
    });
    // Block scroll/zoom on backdrop
    this.backdrop.addEventListener('wheel', (e) => e.preventDefault(), { passive: false });
    this.backdrop.addEventListener('touchmove', (e) => e.preventDefault(), { passive: false });

    // Container
    this.container = document.createElement('div');
    this.container.id = 'imageViewerWindow';
    Object.assign(this.container.style, {
      position: 'fixed',
      left: '50%',
      top: '50%',
      transform: 'translate(-50%, -50%)',
      zIndex: '1001',
      transition: 'opacity 0.2s',
      opacity: '0'
    });

    // Child box
    const box = document.createElement('div');
    box.id = 'imageViewerTargetImage';
    Object.assign(box.style, {
      boxSizing: 'border-box',
      width: '100%',
      height: '100%',
      background: 'rgba(0,200,0,0.3)',
      border: '2px solid black'
    });

    // Image element filling the box
    const img = document.createElement('img');
    img.id = 'imageViewerImg';
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'contain';
    const bestInstance = instance;
    const src = bestInstance.src.startsWith('/srv/images/') ? bestInstance.src : `/srv/images/${bestInstance.src}`;
    img.src = src;
    img.alt = image.caption || '';

    box.appendChild(img);
    this.container.appendChild(box);

    document.body.appendChild(this.backdrop);
    document.body.appendChild(this.container);
    document.body.style.overflow = 'hidden';

    // Initial sizing and inflection thresholds
    this.initializeBaseSizes(intrinsicW, intrinsicH);
    this.currentScale = 1;
    this.applyTransforms(1);
    this.container.style.opacity = '1';

    this.bindEvents();
  }

  private updateImageContent(): void {
    if (!this.container) return;
    const image = this.images[this.currentImageIndex];
    const instance = image.instances[image.instances.length - 1]; // largest
    this.intrinsicWidth = instance.width;
    this.intrinsicHeight = instance.height;

    const img = this.container.querySelector('#imageViewerImg') as HTMLImageElement | null;
    if (img) {
      const src = instance.src.startsWith('/srv/images/') ? instance.src : `/srv/images/${instance.src}`;
      img.src = src;
      img.alt = image.caption || '';
    }

    this.currentScale = 1;
    this.panX = 0;
    this.panY = 0;
    this.detentActive = false;
    this.initializeBaseSizes(this.intrinsicWidth, this.intrinsicHeight);
    this.applyTransforms(1);
  }

  private initializeBaseSizes(intrinsicW: number, intrinsicH: number): void {
    if (!this.container) return;
    // Temporarily size to intrinsic for measurement
    this.container.style.width = `${intrinsicW}px`;
    this.container.style.height = `${intrinsicH}px`;

    // Measure padding/border extras from computed style
    this.measureExtras();

    const vw = this.getPageWidth();
    const vh = this.getPageHeight();
    // Larger margin to start smaller without arbitrary scale factor
    const margin = 200;
    const maxW = vw - margin;
    const maxH = vh - margin;

    // Scale to fit viewport minus margin, preserving aspect
    const scaleX = (maxW - this.totalExtraX) / intrinsicW;
    const scaleY = (maxH - this.totalExtraY) / intrinsicH;
    const fitScale = Math.min(scaleX, scaleY, 1);

    this.baseInnerWidth = intrinsicW * fitScale;
    this.baseInnerHeight = intrinsicH * fitScale;

    this.baseOverlayWidth = this.baseInnerWidth + this.totalExtraX;
    this.baseOverlayHeight = this.baseInnerHeight + this.totalExtraY;

    this.container.style.width = `${this.baseOverlayWidth}px`;
    this.container.style.height = `${this.baseOverlayHeight}px`;

    this.recomputeInflections();
  }

  private recomputeInflections(): void {
    const vw = this.getPageWidth();
    const vh = this.getPageHeight();
    this.scaleForWidthMatch = vw / this.baseOverlayWidth;
    this.scaleForHeightMatch = vh / this.baseOverlayHeight;
  }

  private measureExtras(): void {
    if (!this.container) return;
    const cs = getComputedStyle(this.container);
    const padX = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
    const padY = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);
    const borderX = (parseFloat(cs.borderLeftWidth) || 0) + (parseFloat(cs.borderRightWidth) || 0);
    const borderY = (parseFloat(cs.borderTopWidth) || 0) + (parseFloat(cs.borderBottomWidth) || 0);
    this.totalExtraX = padX + borderX;
    this.totalExtraY = padY + borderY;
  }

  // ---- Transform and state ----------------------------------------------

  private applyTransforms(scale: number): void {
    if (!this.container) return;
    const innerW = this.baseInnerWidth * scale;
    const innerH = this.baseInnerHeight * scale;
    const overlayW = innerW + this.totalExtraX;
    const overlayH = innerH + this.totalExtraY;
    this.container.style.width = `${overlayW}px`;
    this.container.style.height = `${overlayH}px`;
    this.container.style.maxWidth = `${overlayW}px`;
    this.container.style.maxHeight = `${overlayH}px`;

    const clamped = this.clampPan(scale, this.panX, this.panY);
    this.panX = clamped.x;
    this.panY = clamped.y;
    this.container.style.transform = `translate(-50%, -50%) translate(${this.panX}px, ${this.panY}px)`;
    this.setBorderForScale(scale);
  }

  private setBorderForScale(scale: number): void {
    if (!this.container) return;
    const first = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
    const second = Math.max(this.scaleForWidthMatch, this.scaleForHeightMatch);
    const eps = 0.001;
    if (scale > second + eps) {
      this.container.style.border = `3px solid yellow`;
    } else if (scale > first + eps) {
      this.container.style.border = `3px solid blue`;
    } else {
      this.container.style.border = `3px solid red`;
    }
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

  private clampPan(scale: number, panX: number, panY: number): { x: number; y: number } {
    const state = this.getZoomState(scale);
    const vw = this.getPageWidth();
    const vh = this.getPageHeight();
    const scaledW = (this.baseInnerWidth * scale) + this.totalExtraX;
    const scaledH = (this.baseInnerHeight * scale) + this.totalExtraY;
    const halfX = Math.max(0, (scaledW - vw) / 2);
    const halfY = Math.max(0, (scaledH - vh) / 2);
    const widthHitsFirst = this.scaleForWidthMatch < this.scaleForHeightMatch;

    if (state === 'zoomedOut') return { x: 0, y: 0 };
    if (state === 'between') {
      if (widthHitsFirst) return { x: 0, y: Math.max(-halfY, Math.min(halfY, panY)) };
      return { x: Math.max(-halfX, Math.min(halfX, panX)), y: 0 };
    }
    return {
      x: Math.max(-halfX, Math.min(halfX, panX)),
      y: Math.max(-halfY, Math.min(halfY, panY))
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
    // Enable panning in blue (between) on the limiting axis only
    if (state === 'between') {
      if (widthHitsFirst) {
        // width touched first; allow Y pan, lock X
        newPanX = 0;
      } else {
        // height touched first; allow X pan, lock Y
        newPanY = 0;
      }
    }
    this.panX = newPanX;
    this.panY = newPanY;
    this.applyTransforms(this.currentScale);
  };

  // ---- Events binding ----------------------------------------------------

  private bindEvents(): void {
    if (!this.container) return;
    this.container.addEventListener('wheel', this.handleWheel, { passive: false });
    // Allow wheel zoom anywhere while overlay is up
    window.addEventListener('wheel', this.handleWheel, { passive: false });

    // Simple mouse drag for pan
    let dragging = false;
    let lastX = 0, lastY = 0;
    this.container.addEventListener('mousedown', (e) => { e.preventDefault(); dragging = true; lastX = e.clientX; lastY = e.clientY; });
    this.container.addEventListener('mouseup', () => { dragging = false; });
    this.container.addEventListener('mouseleave', () => { dragging = false; });
    document.addEventListener('mouseup', () => { dragging = false; });
    document.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX; lastY = e.clientY;
      this.handleDragMove(dx, dy);
    });

    // Touch handling: pinch zoom + drag pan
    const onPinchMove = (touches: TouchList) => {
      if (touches.length !== 2 || this.pinchStartDist === null) return;
      const dist = this.getTouchDistance(touches);
      if (dist > 0) {
        const newScale = this.pinchStartScale * (dist / this.pinchStartDist);
        this.applyScale(newScale, this.currentScale);
      }
    };

    const startPinch = (e: TouchEvent) => {
      this.pinchStartDist = this.getTouchDistance(e.touches);
      this.pinchStartScale = this.currentScale;
    };

    this.container.addEventListener('touchstart', (e) => {
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
    }, { passive: false });

    this.container.addEventListener('touchmove', (e) => {
      // Match stage behavior: prevent scroll when at default scale
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
    }, { passive: false });

    // Single touchend handler (stage-style): detect swipe first, then reset
    this.container.addEventListener('touchend', (e) => {
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

      // Reset swipe/pinch state
      this.swipeStartX = null;
      this.swipeStartY = null;
      this.swipeStartTime = null;
      this.pinchStartDist = null;
    }, { passive: false });

    // Backdrop pinch/wheel to zoom anywhere
    if (this.backdrop) {
      this.backdrop.addEventListener('wheel', this.handleWheel, { passive: false });
      this.backdrop.addEventListener('touchstart', (e) => {
        if (e.touches.length === 2) {
          e.preventDefault();
          startPinch(e);
        }
      }, { passive: false });
      this.backdrop.addEventListener('touchmove', (e) => {
        if (e.touches.length === 2) {
          e.preventDefault();
          onPinchMove(e.touches);
        }
      }, { passive: false });
      this.backdrop.addEventListener('touchend', () => {
        this.pinchStartDist = null;
      }, { passive: false });
    }

    // Global pinch for two-finger anywhere
    window.addEventListener('touchstart', (e) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        startPinch(e);
      }
    }, { passive: false });
    window.addEventListener('touchmove', (e) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        onPinchMove(e.touches);
      }
    }, { passive: false });
    window.addEventListener('touchend', () => {
      this.pinchStartDist = null;
    }, { passive: false });

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

    this.keyboardHandler = (e: KeyboardEvent) => {
      if (!this.container || !this.backdrop) return;
      if (e.key === 'Escape') { this.cleanup(); e.preventDefault(); }
      else if (e.key === 'ArrowLeft') { if (this.images.length > 1) { this.navigate(-1); e.preventDefault(); } }
      else if (e.key === 'ArrowRight') { if (this.images.length > 1) { this.navigate(1); e.preventDefault(); } }
    };
    document.addEventListener('keydown', this.keyboardHandler);
  }

  // ---- Utils -------------------------------------------------------------

  private getPageWidth(): number {
    return window.innerWidth || document.documentElement.clientWidth;
  }

  private getPageHeight(): number {
    return window.innerHeight || document.documentElement.clientHeight;
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

  private cleanup(): void {
    if (this.resizeHandler) { window.removeEventListener('resize', this.resizeHandler); this.resizeHandler = null; }
    if (this.keyboardHandler) { document.removeEventListener('keydown', this.keyboardHandler); this.keyboardHandler = null; }
    if (this.backdrop?.parentNode) this.backdrop.parentNode.removeChild(this.backdrop);
    if (this.container?.parentNode) this.container.parentNode.removeChild(this.container);
    this.backdrop = null; this.container = null;
    document.body.style.overflow = '';
  }

  static async openFromImageLink(pageId: number, imageId?: number): Promise<void> {
    const viewer = new ImageViewer(pageId, imageId);
    await viewer.show();
  }
}
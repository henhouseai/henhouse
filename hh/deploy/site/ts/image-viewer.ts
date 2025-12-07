/**
 * ImageViewer - minimal overlay with a single container and single child.
 * One transform on the container (scale + pan). No extra layers.
 */

export class ImageViewer {
  private backdrop: HTMLElement | null = null;
  private container: HTMLElement | null = null;
  private readonly pageId: number;

  private currentScale = 1;
  private panX = 0;
  private panY = 0;
  private scaleForWidthMatch = 1;
  private scaleForHeightMatch = 1;
  private detentActive = false;

  private resizeHandler: (() => void) | null = null;
  private keyboardHandler: ((e: KeyboardEvent) => void) | null = null;

  // Layout constants
  private readonly startScale = 0.6;
  private baseOverlayWidth = 0;
  private baseOverlayHeight = 0;

  constructor(pageId: number) {
    this.pageId = pageId;
  }

  async show(): Promise<void> {
    this.renderOverlay();
  }

  // ---- Rendering ---------------------------------------------------------

  private renderOverlay(): void {
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
    this.container.appendChild(box);

    document.body.appendChild(this.backdrop);
    document.body.appendChild(this.container);

    // Initial sizing and inflection thresholds
    this.initializeBaseSizes();
    this.applyTransforms(1);
    this.container.style.opacity = '1';

    this.bindEvents();
  }

  private initializeBaseSizes(): void {
    if (!this.container) return;
    const vw = this.getPageWidth();
    const vh = this.getPageHeight();
    this.baseOverlayWidth = vw * this.startScale;
    this.baseOverlayHeight = vh * this.startScale;
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

  // ---- Transform and state ----------------------------------------------

  private applyTransforms(scale: number): void {
    if (!this.container) return;
    const clamped = this.clampPan(scale, this.panX, this.panY);
    this.panX = clamped.x;
    this.panY = clamped.y;
    this.container.style.transform = `translate(-50%, -50%) translate(${this.panX}px, ${this.panY}px) scale(${scale})`;
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

  private getZoomState(scale: number): 'zoomedOut' | 'widthMatch' | 'between' | 'heightMatch' | 'zoomedIn' {
    if (scale <= 1.0) return 'zoomedOut';
    if (Math.abs(scale - this.scaleForWidthMatch) < 0.01) return 'widthMatch';
    if (scale > this.scaleForWidthMatch && scale < this.scaleForHeightMatch) return 'between';
    if (Math.abs(scale - this.scaleForHeightMatch) < 0.01) return 'heightMatch';
    return 'zoomedIn';
  }

  private clampPan(scale: number, panX: number, panY: number): { x: number; y: number } {
    const state = this.getZoomState(scale);
    const vw = this.getPageWidth();
    const vh = this.getPageHeight();
    const scaledW = this.baseOverlayWidth * scale;
    const scaledH = this.baseOverlayHeight * scale;
    const halfX = Math.max(0, (scaledW - vw) / 2);
    const halfY = Math.max(0, (scaledH - vh) / 2);
    const widthHitsFirst = this.scaleForWidthMatch < this.scaleForHeightMatch;

    if (state === 'zoomedOut' || state === 'widthMatch' || state === 'heightMatch') {
      return { x: 0, y: 0 };
    }
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
    let scale = this.currentScale;
    const delta = e.deltaY;
    const oldScale = scale;
    const first = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
    const second = Math.max(this.scaleForWidthMatch, this.scaleForHeightMatch);
    const sens = 0.1;
    if (delta < 0) scale += sens; else scale -= sens;

    const wasBelow = oldScale <= first;
    const wasAbove = oldScale > first;
    const willBelow = scale <= first;
    const willAbove = scale > first;

    if (delta < 0) {
      if (wasBelow && willAbove) { scale = first; this.detentActive = true; }
      else if (this.detentActive && wasBelow && willAbove) scale = first;
      else this.detentActive = false;
    } else {
      if (wasAbove && willBelow) { scale = first; this.detentActive = true; }
      else if (this.detentActive && wasAbove && willBelow) scale = first;
      else this.detentActive = false;
    }

    scale = Math.max(1, Math.min(3, Math.min(scale, second)));
    this.currentScale = scale;

    const oldState = this.getZoomState(oldScale);
    const newState = this.getZoomState(scale);
    if (delta > 0 &&
        (oldState === 'between' || oldState === 'zoomedIn' || oldState === 'heightMatch' || oldState === 'widthMatch') &&
        (newState === 'widthMatch' || newState === 'zoomedOut' || newState === 'heightMatch')) {
      this.panX = 0; this.panY = 0;
    }

    this.applyTransforms(scale);
  };

  private handleDragMove = (dx: number, dy: number) => {
    const state = this.getZoomState(this.currentScale);
    const widthHitsFirst = this.scaleForWidthMatch < this.scaleForHeightMatch;
    let newPanX = this.panX + dx;
    let newPanY = this.panY + dy;
    if (state === 'between') {
      if (widthHitsFirst) { newPanX = 0; }
      else { newPanY = 0; }
    }
    this.panX = newPanX;
    this.panY = newPanY;
    this.applyTransforms(this.currentScale);
  };

  // ---- Events binding ----------------------------------------------------

  private bindEvents(): void {
    if (!this.container) return;
    this.container.addEventListener('wheel', this.handleWheel, { passive: false });

    // Simple mouse drag for pan
    let dragging = false;
    let lastX = 0, lastY = 0;
    this.container.addEventListener('mousedown', (e) => { dragging = true; lastX = e.clientX; lastY = e.clientY; });
    window.addEventListener('mouseup', () => { dragging = false; });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX; lastY = e.clientY;
      this.handleDragMove(dx, dy);
    });

    // Touch handling (basic)
    this.container.addEventListener('touchstart', (e) => {
      if (e.touches.length > 1) e.preventDefault();
      if (e.touches.length === 1) {
        // store last touch
        const t = e.touches[0];
        lastX = t.clientX; lastY = t.clientY; dragging = true;
      }
    }, { passive: false });
    this.container.addEventListener('touchmove', (e) => {
      if (e.touches.length > 1) { e.preventDefault(); return; }
      if (!dragging) return;
      const t = e.touches[0];
      const dx = t.clientX - lastX;
      const dy = t.clientY - lastY;
      lastX = t.clientX; lastY = t.clientY;
      this.handleDragMove(dx, dy);
    }, { passive: false });
    this.container.addEventListener('touchend', () => { dragging = false; }, { passive: false });

    this.resizeHandler = () => {
      this.recomputeInflections();
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

  private cleanup(): void {
    if (this.resizeHandler) { window.removeEventListener('resize', this.resizeHandler); this.resizeHandler = null; }
    if (this.keyboardHandler) { document.removeEventListener('keydown', this.keyboardHandler); this.keyboardHandler = null; }
    if (this.backdrop?.parentNode) this.backdrop.parentNode.removeChild(this.backdrop);
    if (this.container?.parentNode) this.container.parentNode.removeChild(this.container);
    this.backdrop = null; this.container = null;
    document.body.style.overflow = '';
  }

  static async openFromImageLink(pageId: number, _imageId?: number): Promise<void> {
    const viewer = new ImageViewer(pageId);
    await viewer.show();
  }
}
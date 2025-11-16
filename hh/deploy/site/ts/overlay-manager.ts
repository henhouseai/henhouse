/**
 * OverlayManager - Singleton manager for all overlay instances.
 * Handles z-index stacking, focus management, keyboard shortcuts, and event routing.
 */

import { Overlay } from './overlay.js';

export interface OverlayOptions {
  header?: string | HTMLElement;
  content?: string | HTMLElement | Array<string | HTMLElement>;
  contentHeaders?: Array<string>; // Optional headers for each content section
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

export class OverlayManager {
  private static instance: OverlayManager | null = null;
  private overlays: Overlay[] = [];
  private zIndexCounter: number = 1000;
  private globalKeyHandler: ((e: KeyboardEvent) => void) | null = null;

  private constructor() {
    // Private constructor for singleton pattern
  }

  /**
   * Get the singleton instance of OverlayManager.
   */
  static getInstance(): OverlayManager {
    if (!OverlayManager.instance) {
      OverlayManager.instance = new OverlayManager();
    }
    return OverlayManager.instance;
  }

  /**
   * Show a new overlay with the given options.
   */
  show(options: OverlayOptions): Overlay {
    const overlay = new Overlay(options, this.zIndexCounter++);
    this.overlays.push(overlay);
    overlay.mount();
    this.updateGlobalHandlers();
    return overlay;
  }

  /**
   * Close a specific overlay.
   */
  close(overlay: Overlay): void {
    const index = this.overlays.indexOf(overlay);
    if (index !== -1) {
      // Fast fade for manual close
      overlay.closeWithFade(200);
      this.overlays.splice(index, 1);
      // Update handlers after fade completes
      setTimeout(() => {
        this.updateGlobalHandlers();
      }, 200);
    }
  }

  /**
   * Close all overlays.
   */
  closeAll(): void {
    const overlays = [...this.overlays];
    overlays.forEach(overlay => overlay.closeWithFade(200));
    this.overlays = [];
    // Update handlers after fade completes
    setTimeout(() => {
      this.updateGlobalHandlers();
    }, 200);
  }

  /**
   * Get the topmost overlay (highest z-index).
   */
  getTopOverlay(): Overlay | null {
    if (this.overlays.length === 0) {
      return null;
    }
    return this.overlays[this.overlays.length - 1];
  }

  /**
   * Check if any overlay is currently active.
   */
  isActive(): boolean {
    return this.overlays.length > 0;
  }

  /**
   * Update global keyboard handlers based on active overlays.
   */
  private updateGlobalHandlers(): void {
    // Remove existing handler
    if (this.globalKeyHandler) {
      document.removeEventListener('keydown', this.globalKeyHandler);
      this.globalKeyHandler = null;
    }

    // Add handler if overlays are active
    if (this.overlays.length > 0) {
      this.globalKeyHandler = (e: KeyboardEvent) => {
        const topOverlay = this.getTopOverlay();
        if (!topOverlay) return;

        // ESC key closes top overlay
        if (e.key === 'Escape' || e.keyCode === 27) {
          e.preventDefault();
          e.stopPropagation();
          this.close(topOverlay);
        }
        // Enter key triggers submit (if not in textarea)
        else if ((e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey) {
          const target = e.target as HTMLElement;
          if (target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            e.stopPropagation();
            topOverlay.handleSubmit();
          }
        }
      };
      document.addEventListener('keydown', this.globalKeyHandler);
    }
  }
}


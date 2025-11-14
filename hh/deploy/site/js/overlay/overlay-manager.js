/**
 * OverlayManager - Singleton manager for all overlay instances.
 * Handles z-index stacking, focus management, keyboard shortcuts, and event routing.
 */
import { Overlay } from './overlay.js';
export class OverlayManager {
    constructor() {
        this.overlays = [];
        this.zIndexCounter = 1000;
        this.globalKeyHandler = null;
        // Private constructor for singleton pattern
    }
    /**
     * Get the singleton instance of OverlayManager.
     */
    static getInstance() {
        if (!OverlayManager.instance) {
            OverlayManager.instance = new OverlayManager();
        }
        return OverlayManager.instance;
    }
    /**
     * Show a new overlay with the given options.
     */
    show(options) {
        const overlay = new Overlay(options, this.zIndexCounter++);
        this.overlays.push(overlay);
        overlay.mount();
        this.updateGlobalHandlers();
        return overlay;
    }
    /**
     * Close a specific overlay.
     */
    close(overlay) {
        const index = this.overlays.indexOf(overlay);
        if (index !== -1) {
            overlay.unmount();
            this.overlays.splice(index, 1);
            this.updateGlobalHandlers();
        }
    }
    /**
     * Close all overlays.
     */
    closeAll() {
        const overlays = [...this.overlays];
        overlays.forEach(overlay => overlay.unmount());
        this.overlays = [];
        this.updateGlobalHandlers();
    }
    /**
     * Get the topmost overlay (highest z-index).
     */
    getTopOverlay() {
        if (this.overlays.length === 0) {
            return null;
        }
        return this.overlays[this.overlays.length - 1];
    }
    /**
     * Check if any overlay is currently active.
     */
    isActive() {
        return this.overlays.length > 0;
    }
    /**
     * Update global keyboard handlers based on active overlays.
     */
    updateGlobalHandlers() {
        // Remove existing handler
        if (this.globalKeyHandler) {
            document.removeEventListener('keydown', this.globalKeyHandler);
            this.globalKeyHandler = null;
        }
        // Add handler if overlays are active
        if (this.overlays.length > 0) {
            this.globalKeyHandler = (e) => {
                const topOverlay = this.getTopOverlay();
                if (!topOverlay)
                    return;
                // ESC key closes top overlay
                if (e.key === 'Escape' || e.keyCode === 27) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.close(topOverlay);
                }
                // Enter key triggers submit (if not in textarea)
                else if ((e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey) {
                    const target = e.target;
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
OverlayManager.instance = null;

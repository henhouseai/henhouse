/**
 * Overlay - Base overlay component (modal window).
 * Handles lifecycle, rendering, and state management.
 */
import { OverlayBackdrop } from './overlay-backdrop.js';
import { OverlayWindow } from './overlay-window.js';
import { OverlayHeader } from './overlay-header.js';
import { OverlayContent } from './overlay-content.js';
import { OverlayDebugOptions } from './overlay-debug-options.js';
import { PageManager } from '../page-manager.js';
import { getSeedData } from '../seed.js';
export class Overlay {
    constructor(options, zIndex) {
        this.container = null;
        this.windowEl = null;
        this.headerEl = null;
        this.previousFocus = null;
        this.isClosing = false;
        this.debugOptions = null;
        // Pannable support
        this.pannablePanY = 0;
        this.pannableCleanup = [];
        this.props = { mode: 'fixed', ...options };
        this.state = {
            isVisible: false,
            isLoading: false,
            error: null,
            success: null,
            messages: [],
            zIndex: zIndex
        };
        // Initialize components
        this.backdrop = new OverlayBackdrop({
            onClick: () => {
                if (this.props.closable !== false) {
                    this.handleCancel();
                }
            },
            opacity: 0.7
        });
        this.window = new OverlayWindow({
            width: 'auto',
            height: 'auto',
            position: 'center',
            className: this.props.className,
            mode: this.props.mode,
            style: this.props.style
        });
        // Calculate button visibility (used in both constructor and mount)
        const willShowSubmit = this.props.showSubmit !== false && !!this.props.onSubmit;
        const middleButtonIndependent = this.props.middleButtonIndependent === true;
        const willShowMiddle = (middleButtonIndependent || willShowSubmit) && !!this.props.middleButtonLabel && !!this.props.onMiddleButton;
        this.header = new OverlayHeader({
            title: this.props.header,
            showCancel: this.props.closable !== false,
            showSubmit: willShowSubmit,
            showMiddleButton: willShowMiddle,
            middleButtonIndependent: middleButtonIndependent,
            cancelLabel: this.props.cancelLabel || 'Cancel',
            submitLabel: this.props.submitLabel || 'Submit',
            middleButtonLabel: this.props.middleButtonLabel,
            onCancel: () => this.handleCancel(),
            onSubmit: () => this.handleSubmit(),
            onMiddleButton: this.props.onMiddleButton
        });
        this.content = new OverlayContent({
            children: this.props.content,
            headers: this.props.contentHeaders,
            rawContent: this.props.imageViewerMode
        });
    }
    /**
     * Mount the overlay to the DOM.
     */
    mount() {
        if (this.container) {
            return; // Already mounted
        }
        // Store previous focus
        this.previousFocus = document.activeElement;
        // Create container
        this.container = document.createElement('div');
        this.container.className = 'overlay-container';
        this.container.style.opacity = '1'; // Start fully visible
        document.body.appendChild(this.container);
        // Render components
        const backdropEl = this.backdrop.render();
        backdropEl.style.zIndex = String(this.state.zIndex);
        this.container.appendChild(backdropEl);
        const windowEl = this.window.render();
        windowEl.style.zIndex = String(this.state.zIndex + 1);
        this.container.appendChild(windowEl);
        this.windowEl = windowEl;
        const headerEl = this.header.render();
        windowEl.appendChild(headerEl);
        this.headerEl = headerEl;
        const contentEl = this.content.render();
        windowEl.appendChild(contentEl);
        // Add footer content if provided (e.g., caption in image viewer mode)
        if (this.props.footerContent) {
            if (typeof this.props.footerContent === 'string') {
                const footerEl = document.createElement('div');
                footerEl.className = 'contentWrapperHeader overlay';
                footerEl.textContent = this.props.footerContent;
                windowEl.appendChild(footerEl);
            }
            else {
                // If it's an element, append it directly (it should have its own classes)
                windowEl.appendChild(this.props.footerContent);
            }
        }
        // Only add debug options if submit button will be shown AND not in image viewer mode
        const willShowSubmit = this.props.showSubmit !== false && !!this.props.onSubmit;
        if (willShowSubmit && !this.props.imageViewerMode) {
            // Add debug options as a collapsible footer section
            this.debugOptions = new OverlayDebugOptions();
            const debugEl = this.debugOptions.render();
            windowEl.appendChild(debugEl);
        }
        // Show overlay
        this.setState({ isVisible: true });
        // Focus management
        this.trapFocus(windowEl);
        // Call onMount callback
        if (this.props.onMount) {
            this.props.onMount();
        }
        if (this.props.mode === 'pannable') {
            this.initializePannable();
        }
    }
    /**
     * Accessors for callers needing direct DOM references.
     */
    getWindowElement() {
        return this.windowEl;
    }
    getHeaderElement() {
        return this.headerEl;
    }
    /**
     * Unmount the overlay from the DOM.
     */
    unmount() {
        if (!this.container) {
            return; // Already unmounted
        }
        this.isClosing = true;
        // Call onUnmount callback
        if (this.props.onUnmount) {
            this.props.onUnmount();
        }
        // Remove from DOM
        this.container.remove();
        this.container = null;
        // Cleanup pannable listeners
        this.cleanupPannable();
        // Restore previous focus
        if (this.previousFocus && document.body.contains(this.previousFocus)) {
            this.previousFocus.focus();
        }
        this.previousFocus = null;
        this.setState({ isVisible: false });
    }
    /**
     * Update overlay props.
     */
    update(props) {
        this.props = { ...this.props, ...props };
        // Re-render would go here in a more sophisticated implementation
    }
    /**
     * Update overlay state.
     */
    setState(updates) {
        this.state = { ...this.state, ...updates };
        this.updateUI();
    }
    /**
     * Update UI based on current state.
     */
    updateUI() {
        if (!this.windowEl || !this.headerEl)
            return;
        // Update submit button visibility based on loading state
        const submitBtn = this.headerEl.querySelector('#submitOverlayWindow');
        const loadingImg = this.headerEl.querySelector('img.ajaxloading');
        if (this.state.isLoading) {
            // Hide submit button, show loading spinner
            if (submitBtn) {
                submitBtn.remove();
            }
            // Hide middle button during loading (same logic as submit button)
            const middleBtn = this.headerEl.querySelector('#middleOverlayWindow');
            if (middleBtn) {
                middleBtn.remove();
            }
            if (!loadingImg) {
                const img = document.createElement('img');
                img.src = '/site/ajaxloading.gif';
                img.className = 'ajaxloading';
                img.alt = 'Loading...';
                this.headerEl.appendChild(img);
            }
            // Collapse debug options during loading to keep things tidy
            if (this.debugOptions) {
                this.debugOptions.collapse();
            }
        }
        else {
            // Hide loading spinner
            if (loadingImg) {
                loadingImg.remove();
            }
            // Only restore submit button on error (not on success)
            if (!submitBtn && this.props.onSubmit && (this.state.error || (this.state.messages && this.state.messages.some(m => m.type === 'error')))) {
                // Restore middle button if it was configured
                const middleButtonIndependent = this.props.middleButtonIndependent === true;
                const willShowSubmit = this.props.showSubmit !== false && !!this.props.onSubmit;
                const willShowMiddle = (middleButtonIndependent || willShowSubmit) && !!this.props.middleButtonLabel && !!this.props.onMiddleButton;
                if (willShowMiddle) {
                    const middleBtn = document.createElement('a');
                    middleBtn.id = 'middleOverlayWindow';
                    middleBtn.className = 'overlay-button overlay-button-middle middleButton';
                    middleBtn.textContent = this.props.middleButtonLabel || '';
                    middleBtn.href = '#';
                    middleBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        if (this.props.onMiddleButton) {
                            this.props.onMiddleButton();
                        }
                    });
                    this.headerEl.appendChild(middleBtn);
                }
                const newSubmitBtn = document.createElement('a');
                newSubmitBtn.id = 'submitOverlayWindow';
                newSubmitBtn.className = 'overlay-button overlay-button-submit submitButton';
                newSubmitBtn.textContent = this.props.submitLabel || 'Submit';
                newSubmitBtn.href = '#';
                newSubmitBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.handleSubmit();
                });
                this.headerEl.appendChild(newSubmitBtn);
                // Debug options remain visible (collapsed) when submit button is restored
                // User can expand it if needed
            }
            else {
                // On success, debug options remain visible (collapsed) until overlay closes
                // No need to hide them
            }
        }
        // Remove existing messages
        const existingMessages = this.windowEl.querySelectorAll('.overlaySuccess, .overlayError, .overlayWarning');
        existingMessages.forEach(msg => msg.remove());
        // Add messages in order (from messages array, or fallback to error/success for backward compatibility)
        if (this.state.messages && this.state.messages.length > 0) {
            // Insert messages after header (contentWrapperHeader), in order
            let insertAfter = this.headerEl;
            for (const msg of this.state.messages) {
                const msgDiv = document.createElement('div');
                msgDiv.className = msg.type === 'success' ? 'overlaySuccess' : 'overlayError';
                msgDiv.textContent = msg.text;
                insertAfter.insertAdjacentElement('afterend', msgDiv);
                insertAfter = msgDiv;
            }
        }
        else {
            // Backward compatibility: single error or success message
            if (this.state.error) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'overlayError';
                errorDiv.textContent = this.state.error;
                this.headerEl.insertAdjacentElement('afterend', errorDiv);
            }
            if (this.state.success) {
                const successDiv = document.createElement('div');
                successDiv.className = 'overlaySuccess';
                successDiv.textContent = this.state.success;
                this.headerEl.insertAdjacentElement('afterend', successDiv);
            }
        }
    }
    /**
     * Show the overlay.
     */
    show() {
        this.setState({ isVisible: true });
        if (this.container) {
            this.container.style.display = '';
        }
        // Nudge layout for fixed/pannable so initial position is correct before user scroll
        if (this.props.mode === 'fixed' || this.props.mode === 'pannable') {
            requestAnimationFrame(() => {
                window.scrollBy(0, 1);
                window.scrollBy(0, -1);
            });
        }
    }
    /**
     * Hide the overlay.
     */
    hide() {
        this.setState({ isVisible: false });
        if (this.container) {
            this.container.style.display = 'none';
        }
    }
    /**
     * Close the overlay with a fade-out animation.
     * @param fadeDurationMs Duration of the fade-out in milliseconds (default: 200ms for fast fade)
     */
    closeWithFade(fadeDurationMs = 200) {
        if (!this.container || this.isClosing) {
            return; // Already closed or closing
        }
        this.isClosing = true;
        // Set transition for fade-out
        this.container.style.transition = `opacity ${fadeDurationMs}ms ease-out`;
        this.container.style.opacity = '0';
        // Remove from DOM after fade completes
        setTimeout(() => {
            this.unmount();
        }, fadeDurationMs);
    }
    /**
     * Remove the overlay completely (immediate, no fade).
     */
    remove() {
        this.unmount();
    }
    /**
     * Handle submit action.
     */
    async handleSubmit() {
        if (!this.props.onSubmit) {
            return;
        }
        this.setState({ isLoading: true, error: null, success: null });
        try {
            const result = await this.props.onSubmit();
            // Check if result has custom message and auto-fade flag
            const showMessage = result?._showMessage;
            const autoFade = result?._autoFade === true;
            const redirectAfterFade = result?._redirectAfterFade;
            const debugData = result?.debug;
            if (showMessage) {
                // Use custom message from onSubmit handler
                this.setState({ isLoading: false, success: showMessage });
            }
            else {
                // Default success message
                this.setState({ isLoading: false, success: 'Success!' });
            }
            // Show debug table in separate overlay window if present
            // Only show if debug data exists and has entries (prevents empty debug overlays)
            // Skip if handler already showed it via handleRPCResponseWithDebug
            const debugAlreadyShown = result?._debugAlreadyShown === true;
            const requestInfo = result?.requestInfo;
            if (debugData && Array.isArray(debugData.entries) && debugData.entries.length > 0 && !debugAlreadyShown) {
                this.showDebugTable(debugData, requestInfo);
            }
            // Check if there are any error messages in the messages array
            const hasErrorMessages = this.state.messages && this.state.messages.some(msg => msg.type === 'error');
            // Auto-close after success: wait 1-2 seconds, then slow fade out
            // Only auto-close if explicitly requested (autoFade flag) AND we have success with no error AND no error messages AND no debug data
            // Debug data or error messages disables auto-fade so user can see warnings/debug info/errors
            if (autoFade && (this.state.success && !this.state.error && !hasErrorMessages && !debugData)) {
                setTimeout(() => {
                    this.closeWithFade(1500); // 1.5 second slow fade
                    // If redirect is requested, do it after fade completes
                    if (redirectAfterFade) {
                        setTimeout(() => {
                            this.handleRedirect(redirectAfterFade);
                        }, 1500); // Wait for fade to complete
                    }
                }, 1500); // 1.5 second delay before fade starts
            }
        }
        catch (error) {
            // Check for debug data in error (from RPCError or result)
            let debugData;
            if (error && typeof error === 'object' && 'debug' in error) {
                debugData = error.debug;
            }
            // Check if it's an RPCError with multiple errors
            if (error && typeof error === 'object' && 'errors' in error && Array.isArray(error.errors) && error.errors.length > 0) {
                const rpcError = error;
                // Add each error as a separate message
                const errorMessages = rpcError.errors.map((err) => ({
                    type: 'error',
                    text: `${err.type}: ${err.content}`
                }));
                // Also add the main error message
                const mainError = {
                    type: 'error',
                    text: rpcError.message || 'RPC error'
                };
                this.setState({
                    isLoading: false,
                    messages: [mainError, ...errorMessages],
                    error: null,
                    success: null
                });
                // Show debug table in separate overlay window if present
                // Only show if debug data exists and has entries (prevents empty debug overlays)
                const requestInfo = error?.requestInfo;
                if (debugData && Array.isArray(debugData.entries) && debugData.entries.length > 0) {
                    this.showDebugTable(debugData, requestInfo);
                }
            }
            else {
                const errorMessage = error instanceof Error ? error.message : String(error);
                this.setState({ isLoading: false, error: errorMessage, messages: [] });
                // Show debug table in separate overlay window if present
                // Only show if debug data exists and has entries (prevents empty debug overlays)
                const requestInfo = error?.requestInfo;
                if (debugData && Array.isArray(debugData.entries) && debugData.entries.length > 0) {
                    this.showDebugTable(debugData, requestInfo);
                }
            }
            if (this.props.onError) {
                const errorMessage = error instanceof Error ? error.message : String(error);
                this.props.onError(error instanceof Error ? error : new Error(errorMessage));
            }
        }
    }
    /**
     * Handle cancel action.
     */
    handleCancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
        // Fast fade for manual close
        this.closeWithFade(200);
    }
    /**
     * Get current debug options from the debug options component.
     * During loading, returns stored state instead of reading from DOM.
     */
    getDebugOptions() {
        if (!this.debugOptions) {
            return null;
        }
        return this.debugOptions.getOptions();
    }
    /**
     * Initialize pannable behavior for overlays that should pan vertically instead of scrolling.
     * Wheel always pans; pinch adjusts width between 90–100% of viewport; no vertical zoom.
     */
    initializePannable() {
        if (!this.windowEl)
            return;
        const marginFrac = 0.05; // 5% margin top/bottom
        const measureAndClamp = () => {
            if (!this.windowEl)
                return;
            const vh = window.innerHeight || document.documentElement.clientHeight || 0;
            const h = this.windowEl.offsetHeight;
            const margin = marginFrac * vh;
            const minTop = Math.min(margin, vh - h - margin);
            const maxTop = margin;
            if (h + 2 * margin <= vh) {
                this.pannablePanY = (vh - h) / 2;
            }
            else {
                this.pannablePanY = Math.max(minTop, Math.min(maxTop, this.pannablePanY || margin));
            }
            this.windowEl.style.top = `${this.pannablePanY}px`;
            this.windowEl.style.left = '50%';
            this.windowEl.style.transform = 'translateX(-50%)';
        };
        const clampAndSet = (deltaY) => {
            if (!this.windowEl)
                return;
            const vh = window.innerHeight || document.documentElement.clientHeight || 0;
            const h = this.windowEl.offsetHeight;
            const margin = marginFrac * vh;
            const minTop = Math.min(margin, vh - h - margin);
            const maxTop = margin;
            this.pannablePanY = (this.pannablePanY || margin) - deltaY;
            if (h + 2 * margin <= vh) {
                this.pannablePanY = (vh - h) / 2;
            }
            else {
                this.pannablePanY = Math.max(minTop, Math.min(maxTop, this.pannablePanY));
            }
            this.windowEl.style.top = `${this.pannablePanY}px`;
        };
        const onWheel = (e) => {
            e.preventDefault();
            clampAndSet(e.deltaY);
        };
        const pinchState = { startDist: 0, startWidth: 0 };
        const touchState = { active: false, lastY: 0 };
        const onTouchStart = (e) => {
            if (e.touches.length === 2) {
                e.preventDefault();
                pinchState.startDist = this.getTouchDistance(e.touches);
                pinchState.startWidth = this.windowEl?.offsetWidth || 0;
            }
            else if (e.touches.length === 1) {
                touchState.active = true;
                touchState.lastY = e.touches[0].clientY;
            }
        };
        const onTouchMove = (e) => {
            if (e.touches.length === 2 && pinchState.startDist > 0) {
                e.preventDefault();
                const dist = this.getTouchDistance(e.touches);
                if (dist > 0 && this.windowEl) {
                    const vw = window.innerWidth || document.documentElement.clientWidth || 0;
                    const minW = 0.9 * vw;
                    const maxW = 1.0 * vw;
                    const scale = dist / pinchState.startDist;
                    const newW = Math.max(minW, Math.min(maxW, pinchState.startWidth * scale));
                    this.windowEl.style.width = `${newW}px`;
                    requestAnimationFrame(measureAndClamp);
                }
            }
            else if (touchState.active && e.touches.length === 1) {
                e.preventDefault();
                const currentY = e.touches[0].clientY;
                const dy = touchState.lastY - currentY;
                touchState.lastY = currentY;
                clampAndSet(dy);
            }
        };
        const onTouchEnd = () => {
            touchState.active = false;
            pinchState.startDist = 0;
        };
        const onResize = () => measureAndClamp();
        const attach = (target, event, handler, opts) => {
            if (!target)
                return;
            target.addEventListener(event, handler, opts);
            this.pannableCleanup.push(() => target.removeEventListener(event, handler, opts));
        };
        attach(this.windowEl, 'wheel', onWheel, { passive: false });
        attach(window, 'wheel', onWheel, { passive: false });
        attach(this.windowEl, 'touchstart', onTouchStart, { passive: false });
        attach(this.windowEl, 'touchmove', onTouchMove, { passive: false });
        attach(this.windowEl, 'touchend', onTouchEnd, { passive: false });
        attach(window, 'touchstart', onTouchStart, { passive: false });
        attach(window, 'touchmove', onTouchMove, { passive: false });
        attach(window, 'touchend', onTouchEnd, { passive: false });
        const backdropEl = this.container?.querySelector('.overlay-backdrop') ?? null;
        attach(backdropEl, 'wheel', onWheel, { passive: false });
        attach(backdropEl, 'touchstart', onTouchStart, { passive: false });
        attach(backdropEl, 'touchmove', onTouchMove, { passive: false });
        attach(backdropEl, 'touchend', onTouchEnd, { passive: false });
        attach(window, 'resize', onResize);
        measureAndClamp();
    }
    cleanupPannable() {
        while (this.pannableCleanup.length) {
            const fn = this.pannableCleanup.pop();
            if (fn) {
                try {
                    fn();
                }
                catch {
                    // ignore
                }
            }
        }
    }
    getTouchDistance(touches) {
        if (touches.length < 2)
            return 0;
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.hypot(dx, dy);
    }
    /**
     * Show debug table in a separate overlay window (stacked on top).
     */
    showDebugTable(debugData, requestInfo) {
        // Import and delegate to shared function
        import('../rpc-client.js').then(({ showDebugOverlay }) => {
            showDebugOverlay(debugData, requestInfo);
        });
    }
    /**
     * Handle redirect after fade using standardized redirect patterns.
     * Supports: 'self' (refresh), 'parent' (redirect to parent), '/url' (specific URL), or null (no redirect).
     */
    handleRedirect(redirectAfterFade) {
        if (!redirectAfterFade) {
            return; // No redirect
        }
        if (redirectAfterFade === 'self') {
            // Refresh current page
            window.location.reload();
        }
        else if (redirectAfterFade === 'parent') {
            // Redirect to parent page
            const pageManager = PageManager.getInstance();
            const pageData = pageManager.getPageData();
            if (pageData) {
                const parentId = pageData.getField('parent');
                // Construct parent URL: /{parentId} or / for root
                window.location.href = parentId ? `/${parentId}` : '/';
            }
            else {
                // Fallback: try to get parent from seed data
                const seedData = getSeedData();
                if (seedData.page?.parent) {
                    // Construct parent URL (assuming numeric IDs)
                    const parentId = seedData.page.parent;
                    window.location.href = parentId ? `/${parentId}` : '/';
                }
                else {
                    // No parent found, just reload
                    window.location.reload();
                }
            }
        }
        else {
            // Treat as URL (backward compatible with existing code)
            window.location.href = redirectAfterFade;
        }
    }
    /**
     * Trap focus within the overlay window.
     */
    trapFocus(container) {
        const focusableElements = container.querySelectorAll('a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])');
        if (focusableElements.length === 0) {
            return;
        }
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        // Focus first element
        firstElement.focus();
        // Handle tab cycling
        container.addEventListener('keydown', (e) => {
            if (e.key !== 'Tab') {
                return;
            }
            if (e.shiftKey) {
                // Shift + Tab
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            }
            else {
                // Tab
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        });
    }
}

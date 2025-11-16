/**
 * Overlay - Base overlay component (modal window).
 * Handles lifecycle, rendering, and state management.
 */
import { OverlayManager } from './overlay-manager.js';
import { OverlayBackdrop } from './overlay-backdrop.js';
import { OverlayWindow } from './overlay-window.js';
import { OverlayHeader } from './overlay-header.js';
import { OverlayContent } from './overlay-content.js';
import { OverlayDebugTable } from './overlay-debug-table.js';
import { OverlayDebugOptions } from './overlay-debug-options.js';
export class Overlay {
    constructor(options, zIndex) {
        this.container = null;
        this.windowEl = null;
        this.headerEl = null;
        this.previousFocus = null;
        this.isClosing = false;
        this.debugOptions = null;
        this.storedDebugOptions = null; // Store debug options during loading
        this.props = { ...options };
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
            style: this.props.style
        });
        // Calculate button visibility (used in both constructor and mount)
        const willShowSubmit = this.props.showSubmit !== false && !!this.props.onSubmit;
        const willShowMiddle = willShowSubmit && !!this.props.middleButtonLabel && !!this.props.onMiddleButton;
        this.header = new OverlayHeader({
            title: this.props.header,
            showCancel: this.props.closable !== false,
            showSubmit: willShowSubmit,
            showMiddleButton: willShowMiddle,
            cancelLabel: this.props.cancelLabel || 'Cancel',
            submitLabel: this.props.submitLabel || 'Submit',
            middleButtonLabel: this.props.middleButtonLabel,
            onCancel: () => this.handleCancel(),
            onSubmit: () => this.handleSubmit(),
            onMiddleButton: this.props.onMiddleButton
        });
        this.content = new OverlayContent({
            children: this.props.content
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
        // Only add debug options if submit button will be shown (linked to submit button visibility)
        const willShowSubmit = this.props.showSubmit !== false && !!this.props.onSubmit;
        if (willShowSubmit) {
            // Automatically add debug options component to header (next to submit/cancel buttons)
            this.debugOptions = new OverlayDebugOptions();
            const debugEl = this.debugOptions.render();
            headerEl.appendChild(debugEl);
            // Add filter container after header, before content (hidden by default, shown when debug is checked)
            const filterContainer = this.debugOptions.getFilterContainer();
            windowEl.insertBefore(filterContainer, headerEl.nextSibling);
        }
        const contentEl = this.content.render();
        windowEl.appendChild(contentEl);
        // Show overlay
        this.setState({ isVisible: true });
        // Focus management
        this.trapFocus(windowEl);
        // Call onMount callback
        if (this.props.onMount) {
            this.props.onMount();
        }
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
            // Hide debug options during loading (submit button is hidden, so debug should be too)
            // Note: storedDebugOptions was already saved before setState, so getDebugOptions() will return stored state
            if (this.debugOptions) {
                this.debugOptions.hideForLoading();
                this.debugOptions.hide(); // Hide the entire debug options component
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
                const willShowMiddle = !!this.props.middleButtonLabel && !!this.props.onMiddleButton;
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
                // Show debug options again on error (checkboxes remain unchecked, filters visible)
                // Debug options should be visible when submit button is present
                if (this.debugOptions) {
                    this.debugOptions.show();
                    this.debugOptions.showForError();
                }
                // Don't clear stored debug options yet - async RPC calls might still be in progress
                // They'll be cleared when the overlay actually closes or on next submit
            }
            else {
                // On success, don't clear stored debug options immediately either
                // They'll be cleared when overlay closes or on next submit
                // Hide debug options when submit button is gone (success case)
                if (this.debugOptions && !submitBtn) {
                    this.debugOptions.hide();
                }
            }
        }
        // Remove existing messages
        const existingMessages = this.windowEl.querySelectorAll('.overlaySuccess, .overlayError, .overlayWarning');
        existingMessages.forEach(msg => msg.remove());
        // Add messages in order (from messages array, or fallback to error/success for backward compatibility)
        if (this.state.messages && this.state.messages.length > 0) {
            // Insert messages after header, in order
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
        // Clear stored debug options when closing
        this.storedDebugOptions = null;
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
        // Clear stored debug options when removing
        this.storedDebugOptions = null;
        this.unmount();
    }
    /**
     * Handle submit action.
     */
    async handleSubmit() {
        if (!this.props.onSubmit) {
            return;
        }
        // Read and store debug options BEFORE hiding them (so RPC call can read the checked state)
        // The RPC call happens inside onSubmit(), so we need to preserve the state
        // Store options even if they're empty (so we know to clear them later)
        if (this.debugOptions) {
            this.storedDebugOptions = this.debugOptions.getOptionsBeforeHide();
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
            const requestInfo = result?.requestInfo;
            if (debugData) {
                this.showDebugTable(debugData, requestInfo);
            }
            // Auto-close after success: wait 1-2 seconds, then slow fade out
            // Only auto-close if explicitly requested (autoFade flag) AND we have success with no error AND no debug data
            // Debug data disables auto-fade so user can see warnings/debug info
            if (autoFade && (this.state.success && !this.state.error && !debugData)) {
                setTimeout(() => {
                    this.closeWithFade(1500); // 1.5 second slow fade
                    // If redirect is requested, do it after fade completes
                    if (redirectAfterFade) {
                        setTimeout(() => {
                            window.location.href = redirectAfterFade;
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
                const requestInfo = error?.requestInfo;
                if (debugData) {
                    this.showDebugTable(debugData, requestInfo);
                }
            }
            else {
                const errorMessage = error instanceof Error ? error.message : String(error);
                this.setState({ isLoading: false, error: errorMessage, messages: [] });
                // Show debug table in separate overlay window if present
                const requestInfo = error?.requestInfo;
                if (debugData) {
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
     * Also returns stored options if they exist (even if not loading) to handle async RPC calls.
     */
    getDebugOptions() {
        if (!this.debugOptions) {
            return null;
        }
        // If we have stored options (from a submit that's in progress), return those
        // This handles the case where async RPC calls happen after onSubmit completes
        if (this.storedDebugOptions) {
            return this.storedDebugOptions;
        }
        // Otherwise read from DOM
        return this.debugOptions.getOptions();
    }
    /**
     * Show debug table in a separate overlay window (stacked on top).
     */
    showDebugTable(debugData, requestInfo) {
        // Create debug table
        const debugTable = new OverlayDebugTable();
        const debugElement = debugTable.render(debugData);
        // Build request info display
        let requestInfoHtml = '';
        if (requestInfo) {
            requestInfoHtml = `
        <div class="overlay-form-section">
          <h3 class="overlay-section-title">Request:</h3>
          <div class="overlay-form-group">
            <label><strong>Tool:</strong></label>
            <div>${this.escapeHtml(requestInfo.method)}</div>
          </div>
          <div class="overlay-form-group">
            <label><strong>Arguments:</strong></label>
            <pre class="overlay-debug-request-params">${this.escapeHtml(JSON.stringify(requestInfo.params, null, 2))}</pre>
          </div>
        </div>
      `;
        }
        // Combine request info and debug table
        const contentHtml = requestInfoHtml + debugElement.outerHTML;
        // Create new overlay window for debug info
        const overlayManager = OverlayManager.getInstance();
        overlayManager.show({
            header: 'Debug Information',
            content: contentHtml,
            closable: true,
            cancelLabel: 'Close',
            showSubmit: false,
            className: 'overlay-debug-window'
        });
    }
    /**
     * Escape HTML to prevent XSS.
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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

/**
 * Overlay - Base overlay component (modal window).
 * Handles lifecycle, rendering, and state management.
 */
import { OverlayBackdrop } from './overlay-backdrop.js';
import { OverlayWindow } from './overlay-window.js';
import { OverlayHeader } from './overlay-header.js';
import { OverlayContent } from './overlay-content.js';
export class Overlay {
    constructor(options, zIndex) {
        this.container = null;
        this.windowEl = null;
        this.headerEl = null;
        this.previousFocus = null;
        this.isClosing = false;
        this.props = { ...options };
        this.state = {
            isVisible: false,
            isLoading: false,
            error: null,
            success: null,
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
        this.header = new OverlayHeader({
            title: this.props.header,
            showCancel: this.props.closable !== false,
            showSubmit: !!this.props.onSubmit,
            cancelLabel: this.props.cancelLabel || 'Cancel',
            submitLabel: this.props.submitLabel || 'Submit',
            onCancel: () => this.handleCancel(),
            onSubmit: () => this.handleSubmit()
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
            if (!loadingImg) {
                const img = document.createElement('img');
                img.src = '/site/ajaxloading.gif';
                img.className = 'ajaxloading';
                img.alt = 'Loading...';
                this.headerEl.appendChild(img);
            }
        }
        else {
            // Show submit button, hide loading spinner
            if (loadingImg) {
                loadingImg.remove();
            }
            if (!submitBtn && this.props.onSubmit) {
                const newSubmitBtn = document.createElement('a');
                newSubmitBtn.id = 'submitOverlayWindow';
                newSubmitBtn.className = 'submitButton';
                newSubmitBtn.textContent = this.props.submitLabel || 'Submit';
                newSubmitBtn.href = '#';
                newSubmitBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.handleSubmit();
                });
                this.headerEl.appendChild(newSubmitBtn);
            }
        }
        // Remove existing messages
        const existingMessages = this.windowEl.querySelectorAll('.overlaySuccess, .overlayError, .overlayWarning');
        existingMessages.forEach(msg => msg.remove());
        // Add error message if present
        if (this.state.error) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'overlayError';
            errorDiv.textContent = this.state.error;
            this.headerEl.insertAdjacentElement('afterend', errorDiv);
        }
        // Add success message if present
        if (this.state.success) {
            const successDiv = document.createElement('div');
            successDiv.className = 'overlaySuccess';
            successDiv.textContent = this.state.success;
            this.headerEl.insertAdjacentElement('afterend', successDiv);
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
            if (showMessage) {
                // Use custom message from onSubmit handler
                this.setState({ isLoading: false, success: showMessage });
            }
            else {
                // Default success message
                this.setState({ isLoading: false, success: 'Success!' });
            }
            // Auto-close after success: wait 1-2 seconds, then slow fade out
            // Only auto-close if explicitly requested (autoFade flag) or if we have success
            if (autoFade || (this.state.success && !this.state.error)) {
                setTimeout(() => {
                    this.closeWithFade(1500); // 1.5 second slow fade
                }, 1500); // 1.5 second delay before fade starts
            }
        }
        catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.setState({ isLoading: false, error: errorMessage });
            if (this.props.onError) {
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

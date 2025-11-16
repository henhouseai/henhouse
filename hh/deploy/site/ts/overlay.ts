/**
 * Overlay - Base overlay component (modal window).
 * Handles lifecycle, rendering, and state management.
 */

import { OverlayOptions } from './overlay-manager.js';
import { OverlayBackdrop } from './overlay-backdrop.js';
import { OverlayWindow } from './overlay-window.js';
import { OverlayHeader } from './overlay-header.js';
import { OverlayContent } from './overlay-content.js';
import { OverlayDebugTable, DebugData } from './overlay-debug-table.js';
import { OverlayDebugOptions, DebugOptions } from './overlay-debug-options.js';

export interface OverlayState {
  isVisible: boolean;
  isLoading: boolean;
  error: string | null;
  success: string | null;
  messages: Array<{ type: 'success' | 'error'; text: string }>; // Array of messages in order received
  zIndex: number;
}

export class Overlay {
  private props: OverlayOptions;
  private state: OverlayState;
  private backdrop: OverlayBackdrop;
  private window: OverlayWindow;
  private header: OverlayHeader;
  private content: OverlayContent;
  private container: HTMLElement | null = null;
  private windowEl: HTMLElement | null = null;
  private headerEl: HTMLElement | null = null;
  private previousFocus: HTMLElement | null = null;
  private isClosing: boolean = false;
  private debugOptions: OverlayDebugOptions | null = null;

  constructor(options: OverlayOptions, zIndex: number) {
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
  mount(): void {
    if (this.container) {
      return; // Already mounted
    }

    // Store previous focus
    this.previousFocus = document.activeElement as HTMLElement;

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

    // Automatically add debug options component to header (next to submit/cancel buttons)
    this.debugOptions = new OverlayDebugOptions();
    const debugEl = this.debugOptions.render();
    headerEl.appendChild(debugEl);

    const contentEl = this.content.render();
    windowEl.appendChild(contentEl);

    // Add filter container as sibling to content area (hidden by default, shown when debug is checked)
    const filterContainer = this.debugOptions.getFilterContainer();
    windowEl.appendChild(filterContainer);

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
  unmount(): void {
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
  update(props: Partial<OverlayOptions>): void {
    this.props = { ...this.props, ...props };
    // Re-render would go here in a more sophisticated implementation
  }

  /**
   * Update overlay state.
   */
  setState(updates: Partial<OverlayState>): void {
    this.state = { ...this.state, ...updates };
    this.updateUI();
  }

  /**
   * Update UI based on current state.
   */
  private updateUI(): void {
    if (!this.windowEl || !this.headerEl) return;

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
    } else {
      // Show submit button, hide loading spinner
      if (loadingImg) {
        loadingImg.remove();
      }
      if (!submitBtn && this.props.onSubmit) {
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
    } else {
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
  show(): void {
    this.setState({ isVisible: true });
    if (this.container) {
      this.container.style.display = '';
    }
  }

  /**
   * Hide the overlay.
   */
  hide(): void {
    this.setState({ isVisible: false });
    if (this.container) {
      this.container.style.display = 'none';
    }
  }

  /**
   * Close the overlay with a fade-out animation.
   * @param fadeDurationMs Duration of the fade-out in milliseconds (default: 200ms for fast fade)
   */
  closeWithFade(fadeDurationMs: number = 200): void {
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
  remove(): void {
    this.unmount();
  }

  /**
   * Handle submit action.
   */
  async handleSubmit(): Promise<void> {
    if (!this.props.onSubmit) {
      return;
    }

    this.setState({ isLoading: true, error: null, success: null });

    try {
      const result = await this.props.onSubmit();
      
      // Check if result has custom message and auto-fade flag
      const showMessage = (result as any)?._showMessage;
      const autoFade = (result as any)?._autoFade === true;
      const redirectAfterFade = (result as any)?._redirectAfterFade;
      const debugData = (result as any)?.debug as DebugData | undefined;
      
      if (showMessage) {
        // Use custom message from onSubmit handler
        this.setState({ isLoading: false, success: showMessage });
      } else {
        // Default success message
        this.setState({ isLoading: false, success: 'Success!' });
      }
      
      // Show debug table if present
      if (debugData) {
        this.showDebugTable(debugData);
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
    } catch (error) {
      // Check for debug data in error (from RPCError or result)
      let debugData: DebugData | undefined;
      if (error && typeof error === 'object' && 'debug' in error) {
        debugData = (error as any).debug;
      }
      
      // Check if it's an RPCError with multiple errors
      if (error && typeof error === 'object' && 'errors' in error && Array.isArray((error as any).errors) && (error as any).errors.length > 0) {
        const rpcError = error as any;
        // Add each error as a separate message
        const errorMessages = rpcError.errors.map((err: { type: string; content: string }) => ({
          type: 'error' as const,
          text: `${err.type}: ${err.content}`
        }));
        // Also add the main error message
        const mainError = {
          type: 'error' as const,
          text: rpcError.message || 'RPC error'
        };
        this.setState({ 
          isLoading: false, 
          messages: [mainError, ...errorMessages],
          error: null,
          success: null
        });
        
        // Show debug table if present
        if (debugData) {
          this.showDebugTable(debugData);
        }
      } else {
        const errorMessage = error instanceof Error ? error.message : String(error);
        this.setState({ isLoading: false, error: errorMessage, messages: [] });
        
        // Show debug table if present
        if (debugData) {
          this.showDebugTable(debugData);
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
  handleCancel(): void {
    if (this.props.onCancel) {
      this.props.onCancel();
    }
    // Fast fade for manual close
    this.closeWithFade(200);
  }

  /**
   * Get current debug options from the debug options component.
   */
  getDebugOptions(): DebugOptions | null {
    if (!this.debugOptions) {
      return null;
    }
    return this.debugOptions.getOptions();
  }

  /**
   * Show debug table in the overlay content area.
   */
  showDebugTable(debugData: DebugData): void {
    if (!this.windowEl) {
      return;
    }

    // Remove existing debug table if present
    const existingDebug = this.windowEl.querySelector('.overlay-debug-table-container');
    if (existingDebug) {
      existingDebug.remove();
    }

    // Create and render debug table
    const debugTable = new OverlayDebugTable();
    const debugElement = debugTable.render(debugData);

    // Append to content area (after all other content)
    const contentEl = this.windowEl.querySelector('.overlayContent');
    if (contentEl) {
      contentEl.appendChild(debugElement);
    } else {
      // Fallback: append to window
      this.windowEl.appendChild(debugElement);
    }
  }

  /**
   * Trap focus within the overlay window.
   */
  private trapFocus(container: HTMLElement): void {
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) {
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus first element
    firstElement.focus();

    // Handle tab cycling
    container.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key !== 'Tab') {
        return;
      }

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    });
  }
}


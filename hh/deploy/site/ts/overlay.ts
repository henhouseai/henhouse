/**
 * Overlay - Base overlay component (modal window).
 * Handles lifecycle, rendering, and state management.
 */

import { OverlayOptions } from './overlay-manager.js';
import { OverlayBackdrop } from './overlay-backdrop.js';
import { OverlayWindow } from './overlay-window.js';
import { OverlayHeader } from './overlay-header.js';
import { OverlayContent } from './overlay-content.js';

export interface OverlayState {
  isVisible: boolean;
  isLoading: boolean;
  error: string | null;
  success: string | null;
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
  private previousFocus: HTMLElement | null = null;

  constructor(options: OverlayOptions, zIndex: number) {
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
  mount(): void {
    if (this.container) {
      return; // Already mounted
    }

    // Store previous focus
    this.previousFocus = document.activeElement as HTMLElement;

    // Create container
    this.container = document.createElement('div');
    this.container.className = 'overlay-container';
    document.body.appendChild(this.container);

    // Render components
    const backdropEl = this.backdrop.render();
    backdropEl.style.zIndex = String(this.state.zIndex);
    this.container.appendChild(backdropEl);

    const windowEl = this.window.render();
    windowEl.style.zIndex = String(this.state.zIndex + 1);
    this.container.appendChild(windowEl);

    const headerEl = this.header.render();
    windowEl.appendChild(headerEl);

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
  unmount(): void {
    if (!this.container) {
      return; // Already unmounted
    }

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
    // State updates would trigger re-renders in a more sophisticated implementation
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
   * Remove the overlay completely.
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

    this.setState({ isLoading: true, error: null });

    try {
      const result = await this.props.onSubmit();
      this.setState({ isLoading: false, success: 'Success!' });
      // Could auto-close here or wait for user action
    } catch (error) {
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
  handleCancel(): void {
    if (this.props.onCancel) {
      this.props.onCancel();
    }
    this.remove();
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


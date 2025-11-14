/**
 * OverlayBackdrop - Modal backdrop (dark overlay behind window).
 */

export interface OverlayBackdropProps {
  onClick?: () => void;
  opacity?: number;
}

export class OverlayBackdrop {
  private props: OverlayBackdropProps;

  constructor(props: OverlayBackdropProps) {
    this.props = {
      opacity: 0.7,
      ...props
    };
  }

  /**
   * Render the backdrop element.
   */
  render(): HTMLElement {
    const backdrop = document.createElement('div');
    backdrop.id = 'overlay';
    backdrop.className = 'overlay-backdrop';

    // Styling
    backdrop.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: #000;
      opacity: ${this.props.opacity || 0.7};
      z-index: 100;
    `;

    // Click handler
    if (this.props.onClick) {
      backdrop.addEventListener('click', (e) => {
        e.stopPropagation();
        this.props.onClick!();
      });
    }

    return backdrop;
  }
}


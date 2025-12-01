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

    // Only set dynamic opacity (base styles are in CSS)
    backdrop.style.opacity = String(this.props.opacity || 0.7);

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


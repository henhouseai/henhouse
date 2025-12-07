/**
 * OverlayWindow - Modal window container.
 */

export interface OverlayWindowProps {
  width?: string | number;
  height?: string | number;
  position?: 'center' | 'top' | 'custom';
  className?: string;
  mode?: 'fixed' | 'pannable' | 'zoomable';
  style?: Partial<CSSStyleDeclaration>;
}

export class OverlayWindow {
  private props: OverlayWindowProps;

  constructor(props: OverlayWindowProps) {
    this.props = {
      width: 'auto',
      height: 'auto',
      position: 'center',
      ...props
    };
  }

  /**
   * Render the window element.
   */
  render(): HTMLElement {
    const window = document.createElement('div');
    window.className = 'overlay-window';
    if (this.props.mode) {
      window.className += ` overlay-window-${this.props.mode}`;
    }
    if (this.props.className) {
      window.className += ` ${this.props.className}`;
    }

    // Base styles are in CSS, only set dynamic properties

    // Apply custom width/height
    if (this.props.width !== 'auto' && this.props.width !== undefined) {
      window.style.width = typeof this.props.width === 'number' 
        ? `${this.props.width}px` 
        : this.props.width;
    }

    if (this.props.height !== 'auto' && this.props.height !== undefined) {
      window.style.height = typeof this.props.height === 'number' 
        ? `${this.props.height}px` 
        : this.props.height;
    }

    // Position
    if (this.props.position === 'center') {
      window.style.top = '50%';
      window.style.left = '50%';
      window.style.transform = 'translate(-50%, -50%)';
    } else if (this.props.position === 'top') {
      window.style.top = '10%';
      window.style.left = '50%';
      window.style.transform = 'translateX(-50%)';
    }

    // Apply custom styles
    if (this.props.style) {
      Object.assign(window.style, this.props.style);
    }

    return window;
  }
}


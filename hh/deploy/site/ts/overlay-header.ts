/**
 * OverlayHeader - Header bar with title and action buttons.
 */

export interface OverlayHeaderProps {
  title?: string | HTMLElement;
  showCancel?: boolean;
  showSubmit?: boolean;
  showMiddleButton?: boolean;
  cancelLabel?: string;
  submitLabel?: string;
  middleButtonLabel?: string;
  onCancel?: () => void;
  onSubmit?: () => void;
  onMiddleButton?: () => void;
}

export class OverlayHeader {
  private props: OverlayHeaderProps;

  constructor(props: OverlayHeaderProps) {
    this.props = {
      showCancel: true,
      showSubmit: true,
      cancelLabel: 'Cancel',
      submitLabel: 'Submit',
      ...props
    };
  }

  /**
   * Render the header element.
   */
  render(): HTMLElement {
    const header = document.createElement('div');
    header.className = 'overlayHeader';

    // Title
    if (this.props.title) {
      if (typeof this.props.title === 'string') {
        header.textContent = this.props.title;
      } else {
        header.appendChild(this.props.title);
      }
    }

    // Cancel button
    if (this.props.showCancel) {
      const cancelBtn = document.createElement('a');
      cancelBtn.id = 'cancelOverlayWindow';
      cancelBtn.className = 'overlay-button overlay-button-cancel cancelButton';
      cancelBtn.textContent = this.props.cancelLabel || 'Cancel';
      cancelBtn.href = '#';
      cancelBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (this.props.onCancel) {
          this.props.onCancel();
        }
      });
      header.appendChild(cancelBtn);
    }

    // Middle button (only shown when submit button is also shown)
    if (this.props.showMiddleButton && this.props.showSubmit) {
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
      header.appendChild(middleBtn);
    }

    // Submit button
    if (this.props.showSubmit) {
      const submitBtn = document.createElement('a');
      submitBtn.id = 'submitOverlayWindow';
      submitBtn.className = 'overlay-button overlay-button-submit submitButton';
      submitBtn.textContent = this.props.submitLabel || 'Submit';
      submitBtn.href = '#';
      submitBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (this.props.onSubmit) {
          this.props.onSubmit();
        }
      });
      header.appendChild(submitBtn);
    }

    return header;
  }
}


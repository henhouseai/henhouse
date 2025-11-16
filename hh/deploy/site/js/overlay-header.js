/**
 * OverlayHeader - Header bar with title and action buttons.
 */
export class OverlayHeader {
    constructor(props) {
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
    render() {
        const header = document.createElement('div');
        header.className = 'overlayHeader';
        // Title
        if (this.props.title) {
            if (typeof this.props.title === 'string') {
                header.textContent = this.props.title;
            }
            else {
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

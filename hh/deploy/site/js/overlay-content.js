/**
 * OverlayContent - Container for pluggable content components.
 */
export class OverlayContent {
    constructor(props) {
        this.props = props;
    }
    /**
     * Render the content element.
     */
    render() {
        const content = document.createElement('div');
        content.className = 'overlayContent';
        if (this.props.className) {
            content.className += ` ${this.props.className}`;
        }
        // Handle children
        if (this.props.children) {
            if (typeof this.props.children === 'string') {
                content.innerHTML = this.props.children;
            }
            else {
                content.appendChild(this.props.children);
            }
        }
        return content;
    }
}

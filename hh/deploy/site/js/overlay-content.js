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
        // If children is an array, wrap each item in its own overlayContent div
        if (Array.isArray(this.props.children)) {
            const container = document.createElement('div');
            // Don't add overlayContent class to container - each child gets its own
            this.props.children.forEach(child => {
                const childDiv = document.createElement('div');
                childDiv.className = 'overlayContent';
                if (this.props.className) {
                    childDiv.className += ` ${this.props.className}`;
                }
                if (typeof child === 'string') {
                    childDiv.innerHTML = child;
                }
                else {
                    childDiv.appendChild(child);
                }
                container.appendChild(childDiv);
            });
            return container;
        }
        // Single child - wrap in overlayContent div (original behavior)
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

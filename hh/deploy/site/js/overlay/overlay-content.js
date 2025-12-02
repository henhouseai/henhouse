/**
 * OverlayContent - Container for pluggable content components.
 */
export class OverlayContent {
    constructor(props) {
        this.props = props;
    }
    /**
     * Render the content element.
     * Uses array-based content structure with optional headers for each section.
     */
    render() {
        const container = document.createElement('div');
        const headers = this.props.headers || [];
        const contentItems = this.props.children || [];
        // Determine max length to iterate through both arrays
        const maxLength = Math.max(headers.length, contentItems.length);
        for (let i = 0; i < maxLength; i++) {
            const headerText = headers[i];
            const contentItem = contentItems[i];
            // Skip if no content item
            if (!contentItem) {
                continue;
            }
            // Create header if header text exists and is not blank
            if (headerText !== undefined && headerText !== '') {
                const headerDiv = document.createElement('div');
                headerDiv.className = 'contentHeader overlay';
                // Create expand/collapse button
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'overlay-content-toggle';
                toggleBtn.textContent = '▼'; // Expanded state (down arrow)
                toggleBtn.type = 'button';
                // Create header text span
                const headerTextSpan = document.createElement('span');
                headerTextSpan.className = 'overlay-content-header-text';
                headerTextSpan.textContent = headerText;
                headerDiv.appendChild(toggleBtn);
                headerDiv.appendChild(headerTextSpan);
                // Create content div
                const contentDiv = document.createElement('div');
                contentDiv.className = 'content overlay';
                if (this.props.className) {
                    contentDiv.className += ` ${this.props.className}`;
                }
                if (typeof contentItem === 'string') {
                    contentDiv.innerHTML = contentItem;
                }
                else {
                    contentDiv.appendChild(contentItem);
                }
                // Set initial collapsed state based on header text
                // Request: expanded, Response: collapsed
                const isCollapsed = headerText.toLowerCase() === 'response';
                if (isCollapsed) {
                    contentDiv.style.display = 'none';
                    toggleBtn.textContent = '▶'; // Collapsed state (right arrow)
                }
                // Add click handler for expand/collapse
                toggleBtn.addEventListener('click', () => {
                    const isCurrentlyCollapsed = contentDiv.style.display === 'none';
                    if (isCurrentlyCollapsed) {
                        contentDiv.style.display = '';
                        toggleBtn.textContent = '▼';
                    }
                    else {
                        contentDiv.style.display = 'none';
                        toggleBtn.textContent = '▶';
                    }
                });
                container.appendChild(headerDiv);
                container.appendChild(contentDiv);
            }
            else {
                // No header - just create content div
                const contentDiv = document.createElement('div');
                contentDiv.className = 'content overlay';
                if (this.props.className) {
                    contentDiv.className += ` ${this.props.className}`;
                }
                if (typeof contentItem === 'string') {
                    contentDiv.innerHTML = contentItem;
                }
                else {
                    contentDiv.appendChild(contentItem);
                }
                container.appendChild(contentDiv);
            }
        }
        return container;
    }
}

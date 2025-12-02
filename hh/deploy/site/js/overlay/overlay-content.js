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
        container.className = 'contentWrapper overlay';
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
            // Helper function to check if HTML string already has wrapper divs
            const hasWrapperDiv = (html) => {
                if (typeof html !== 'string')
                    return false;
                const trimmed = html.trim();
                // Check if it starts with <div and contains both "content" and "overlay" classes
                // (may have other classes like "tableViewDiv" in between)
                if (!trimmed.startsWith('<div'))
                    return false;
                // Match class="..." or class='...' containing both "content" and "overlay"
                const classPattern = /class=["']([^"']+)["']/;
                const match = trimmed.match(classPattern);
                if (!match)
                    return false;
                const classes = match[1];
                return classes.includes('content') && classes.includes('overlay');
            };
            // Helper function to parse HTML and append nodes directly
            const appendHTMLContent = (html, target) => {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                // Move all children from tempDiv to target
                while (tempDiv.firstChild) {
                    target.appendChild(tempDiv.firstChild);
                }
            };
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
                // Handle content item
                if (typeof contentItem === 'string') {
                    if (hasWrapperDiv(contentItem)) {
                        // HTML already has wrapper divs - parse and append directly
                        appendHTMLContent(contentItem, container);
                        // Find the content div we just added to attach collapse handler
                        const addedContentDiv = container.lastElementChild;
                        if (addedContentDiv && addedContentDiv.classList.contains('content')) {
                            // Set initial collapsed state based on header text
                            const isCollapsed = headerText.toLowerCase() === 'response';
                            if (isCollapsed) {
                                addedContentDiv.style.display = 'none';
                                toggleBtn.textContent = '▶';
                            }
                            // Add click handler for expand/collapse
                            toggleBtn.addEventListener('click', () => {
                                const isCurrentlyCollapsed = addedContentDiv.style.display === 'none';
                                if (isCurrentlyCollapsed) {
                                    addedContentDiv.style.display = '';
                                    toggleBtn.textContent = '▼';
                                }
                                else {
                                    addedContentDiv.style.display = 'none';
                                    toggleBtn.textContent = '▶';
                                }
                            });
                        }
                        // Insert header before the content we just added
                        container.insertBefore(headerDiv, container.lastElementChild);
                    }
                    else {
                        // No wrapper - create content div and wrap
                        const contentDiv = document.createElement('div');
                        contentDiv.className = 'content overlay';
                        if (this.props.className) {
                            contentDiv.className += ` ${this.props.className}`;
                        }
                        contentDiv.innerHTML = contentItem;
                        // Set initial collapsed state based on header text
                        const isCollapsed = headerText.toLowerCase() === 'response';
                        if (isCollapsed) {
                            contentDiv.style.display = 'none';
                            toggleBtn.textContent = '▶';
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
                }
                else {
                    // HTMLElement - wrap in content div
                    const contentDiv = document.createElement('div');
                    contentDiv.className = 'content overlay';
                    if (this.props.className) {
                        contentDiv.className += ` ${this.props.className}`;
                    }
                    contentDiv.appendChild(contentItem);
                    // Set initial collapsed state
                    const isCollapsed = headerText.toLowerCase() === 'response';
                    if (isCollapsed) {
                        contentDiv.style.display = 'none';
                        toggleBtn.textContent = '▶';
                    }
                    // Add click handler
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
            }
            else {
                // No header - just handle content
                if (typeof contentItem === 'string') {
                    if (hasWrapperDiv(contentItem)) {
                        // HTML already has wrapper divs - parse and append directly
                        appendHTMLContent(contentItem, container);
                    }
                    else {
                        // No wrapper - create content div and wrap
                        const contentDiv = document.createElement('div');
                        contentDiv.className = 'content overlay';
                        if (this.props.className) {
                            contentDiv.className += ` ${this.props.className}`;
                        }
                        contentDiv.innerHTML = contentItem;
                        container.appendChild(contentDiv);
                    }
                }
                else {
                    // HTMLElement - wrap in content div
                    const contentDiv = document.createElement('div');
                    contentDiv.className = 'content overlay';
                    if (this.props.className) {
                        contentDiv.className += ` ${this.props.className}`;
                    }
                    contentDiv.appendChild(contentItem);
                    container.appendChild(contentDiv);
                }
            }
        }
        return container;
    }
}

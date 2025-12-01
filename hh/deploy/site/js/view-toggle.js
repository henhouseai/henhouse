/**
 * View Toggle System - handles hot-swapping between table and tile views for page sections.
 * Listens for clicks on toggle links and replaces DOM chunks via MCP calls.
 */
import { RPCClient } from './rpc-client.js';
class ViewToggle {
    constructor() {
        this.rpc = new RPCClient();
        this.initialize();
    }
    /**
     * Initialize the view toggle system by setting up event listeners.
     */
    initialize() {
        // Use event delegation to handle clicks on toggle links
        document.addEventListener('click', (e) => {
            const target = e.target;
            // Check if clicked element is a toggle link or inside one
            const toggleLink = target.closest('a[class*="updatePageView_"]');
            if (!toggleLink) {
                return;
            }
            e.preventDefault();
            this.handleToggleClick(toggleLink);
        });
    }
    /**
     * Handle click on a toggle link.
     * @param linkElement - The clicked toggle link element
     */
    async handleToggleClick(linkElement) {
        try {
            // Extract page_id from class name (e.g., "updatePageView_635" -> "635")
            const classList = Array.from(linkElement.classList);
            const updateClass = classList.find(cls => cls.startsWith('updatePageView_'));
            if (!updateClass) {
                console.warn('Could not find updatePageView class in toggle link');
                return;
            }
            const pageId = updateClass.replace('updatePageView_', '');
            if (!pageId) {
                console.warn('Could not extract page ID from toggle link');
                return;
            }
            // Extract section from data attributes
            const section = linkElement.getAttribute('data-section');
            const className = linkElement.getAttribute('data-class-name'); // For children sections
            if (!section) {
                console.warn('Toggle link missing data-section attribute');
                return;
            }
            // For children sections, class_name is required
            if (section === 'children' && !className) {
                console.warn('Toggle link missing data-class-name attribute for children section');
                return;
            }
            // Auto-detect current view type by checking next sibling
            const headerElement = linkElement.closest('.contentHeader');
            if (!headerElement) {
                console.warn('Could not find header element');
                return;
            }
            const nextSibling = headerElement.nextElementSibling;
            if (!nextSibling) {
                console.warn('Could not find next sibling element to detect current view');
                return;
            }
            // Detect current view: if next sibling contains a table, current view is 'table', otherwise 'tile'
            const hasTable = nextSibling.querySelector('table') !== null;
            const viewType = hasTable ? 'tile' : 'table'; // Request opposite of current view
            // Auto-detect if we're in an overlay by checking for overlay_ ID prefix
            const isInOverlay = headerElement.id.startsWith('overlay_') ||
                nextSibling.id?.startsWith('overlay_') ||
                linkElement.closest('#overlayWindow') !== null;
            // Build MCP call parameters
            const params = {
                id: parseInt(pageId, 10),
                section: section,
                view_type: viewType
            };
            // Add overlay flag if in overlay
            if (isInOverlay) {
                params.overlay = 1;
            }
            // Add class_name for children sections
            if (section === 'children' && className) {
                params.class_name = className;
            }
            // Make MCP call to get_page_section
            const result = await this.rpc.call('get_page_section', params);
            // Extract dom_content from response
            const domContent = result.data?.dom_content;
            if (!domContent || typeof domContent !== 'string') {
                console.warn('get_page_section did not return dom_content');
                return;
            }
            // Replace DOM chunks - pass linkElement to check if in overlay
            this.replaceSectionContent(pageId, section, domContent, className, linkElement);
        }
        catch (error) {
            console.error('Error handling view toggle:', error);
            // Could show error to user via overlay or console
        }
    }
    /**
     * Replace the section content in the DOM.
     * @param pageId - Page ID string
     * @param section - Section name (e.g., 'images', 'children')
     * @param htmlContent - HTML content to insert
     * @param className - Optional class name for children sections
     * @param linkElement - The toggle link element (to check if in overlay)
     */
    replaceSectionContent(pageId, section, htmlContent, className, linkElement) {
        // Create a temporary container to parse the HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlContent;
        // Determine content element ID based on section type
        // Check if we're in an overlay (has overlay_ prefix)
        const isInOverlay = linkElement.closest('#overlayWindow') !== null;
        const prefix = isInOverlay ? 'overlay_' : '';
        let contentId;
        if (section === 'images') {
            contentId = `${prefix}pageImageGroup_${pageId}`;
        }
        else if (section === 'children') {
            if (!className) {
                console.warn('Class name required for children section');
                return;
            }
            // Convert class_name to safe format (replace underscores with hyphens)
            const classNameSafe = className.replace(/_/g, '-');
            contentId = `${prefix}child_pages_${classNameSafe}_${pageId}`;
        }
        else {
            console.warn(`Section ${section} not yet supported for view toggle`);
            return;
        }
        // Find content element in the parsed HTML (header is not in returned HTML)
        const contentElement = tempDiv.querySelector(`#${contentId}`);
        if (!contentElement) {
            console.warn(`Could not find content element in HTML for page ${pageId}, section ${section}`);
            return;
        }
        // Find existing content element in the DOM
        const existingContent = document.getElementById(contentId);
        if (!existingContent) {
            console.warn(`Could not find existing content element for page ${pageId}, section ${section}`);
            return;
        }
        // Replace the entire element with the new one (including wrapper div with correct class)
        // The new element already includes clearboth if needed, so just replace the whole thing
        const newElement = contentElement.cloneNode(true);
        existingContent.parentNode?.replaceChild(newElement, existingContent);
    }
}
// Initialize view toggle system when DOM is ready
let viewToggleInstance = null;
export function initializeViewToggle() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            viewToggleInstance = new ViewToggle();
        });
    }
    else {
        viewToggleInstance = new ViewToggle();
    }
}

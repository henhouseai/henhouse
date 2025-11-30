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
            // Extract section and view_type from data attributes
            const section = linkElement.getAttribute('data-section');
            const viewType = linkElement.getAttribute('data-view-type');
            const className = linkElement.getAttribute('data-class-name'); // For children sections
            if (!section) {
                console.warn('Toggle link missing data-section attribute');
                return;
            }
            if (!viewType) {
                console.warn('Toggle link missing data-view-type attribute');
                return;
            }
            // For children sections, class_name is required
            if (section === 'children' && !className) {
                console.warn('Toggle link missing data-class-name attribute for children section');
                return;
            }
            // Build MCP call parameters
            const params = {
                id: parseInt(pageId, 10),
                section: section,
                view_type: viewType
            };
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
            // Replace DOM chunks
            this.replaceSectionContent(pageId, section, domContent, className);
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
     */
    replaceSectionContent(pageId, section, htmlContent, className) {
        // Create a temporary container to parse the HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlContent;
        // Determine element IDs based on section type
        let headerId;
        let contentId;
        if (section === 'images') {
            headerId = `pageImageGroupHeader_${pageId}`;
            contentId = `pageImageGroup_${pageId}`;
        }
        else if (section === 'children') {
            if (!className) {
                console.warn('Class name required for children section');
                return;
            }
            // Convert class_name to safe format (replace underscores with hyphens)
            const classNameSafe = className.replace(/_/g, '-');
            headerId = `child_pages_${classNameSafe}_header_${pageId}`;
            contentId = `child_pages_${classNameSafe}_${pageId}`;
        }
        else {
            console.warn(`Section ${section} not yet supported for view toggle`);
            return;
        }
        // Find header and content elements in the parsed HTML
        const headerElement = tempDiv.querySelector(`#${headerId}`);
        const contentElement = tempDiv.querySelector(`#${contentId}`);
        if (!headerElement || !contentElement) {
            console.warn(`Could not find header or content elements in HTML for page ${pageId}, section ${section}`);
            return;
        }
        // Find existing elements in the DOM
        const existingHeader = document.getElementById(headerId);
        const existingContent = document.getElementById(contentId);
        if (!existingHeader || !existingContent) {
            console.warn(`Could not find existing header or content elements for page ${pageId}, section ${section}`);
            return;
        }
        // Replace header (preserve the element, just update its content)
        existingHeader.innerHTML = headerElement.innerHTML;
        // Replace content (preserve the element, just update its content)
        existingContent.innerHTML = contentElement.innerHTML;
        // Handle clearboth div if present in new HTML
        const clearboth = tempDiv.querySelector('.clearboth');
        if (clearboth) {
            // Check if clearboth already exists after content
            const existingClearboth = existingContent.nextElementSibling;
            if (existingClearboth && existingClearboth.classList.contains('clearboth')) {
                // Already exists, do nothing
            }
            else {
                // Insert clearboth after content
                const clearbothDiv = document.createElement('div');
                clearbothDiv.className = 'clearboth';
                existingContent.parentNode?.insertBefore(clearbothDiv, existingContent.nextSibling);
            }
        }
        else {
            // If new HTML doesn't have clearboth, remove existing one if present
            const existingClearboth = existingContent.nextElementSibling;
            if (existingClearboth && existingClearboth.classList.contains('clearboth')) {
                existingClearboth.remove();
            }
        }
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

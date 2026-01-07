/**
 * View Toggle System - handles hot-swapping between table and tile views for page sections.
 * Listens for clicks on toggle links and replaces DOM chunks via MCP calls.
 * Supports callbacks for pre/post-processing of swapped content.
 */
import { RPCClient, RPCError } from './rpc-client.js';
import { interceptLinks } from './overlay/overlay-link-helpers.js';
import { getSeedData } from './seed.js';
class ViewToggle {
    constructor(callbacks) {
        this.rpc = new RPCClient();
        this.callbacks = callbacks || {};
        this.initialize();
    }
    /**
     * Update callbacks for this instance.
     */
    setCallbacks(callbacks) {
        this.callbacks = { ...this.callbacks, ...callbacks };
    }
    /**
     * Initialize the view toggle system by setting up event listeners.
     */
    initialize() {
        // Use event delegation to handle clicks on toggle links
        document.addEventListener('click', (e) => {
            const target = e.target;
            // Check if clicked element is a toggle link (supports updatePageView_ and update*View_ patterns)
            const toggleLink = target.closest('a[class*="update"][class*="View_"]');
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
            // Extract page_id and class name from class name (e.g., "updatePageView_635" -> ("635", "Page") or "updateInvoiceView_635" -> ("635", "Invoice"))
            const classList = Array.from(linkElement.classList);
            const updateClass = classList.find(cls => cls.includes('update') && cls.includes('View_'));
            if (!updateClass) {
                console.warn('Could not find update*View_ class in toggle link');
                return;
            }
            // Extract class name and page ID (e.g., "updateInvoiceView_635" -> class="Invoice", pageId="635")
            const match = updateClass.match(/^update([A-Za-z]+)View_(\d+)$/);
            if (!match || !match[1] || !match[2]) {
                console.warn('Could not parse update*View_ class name');
                return;
            }
            const viewClass = match[1]; // e.g., "Invoice" or "Page"
            const pageId = match[2];
            // Extract section from data attributes (for generic updatePageView_) or infer from class name
            let section = linkElement.getAttribute('data-section');
            let className = linkElement.getAttribute('data-class-name'); // For children sections
            if (!section) {
                console.warn('Toggle link missing data-section attribute');
                return;
            }
            // For children sections, class_name is required
            if (section === 'children' && !className) {
                console.warn('Toggle link missing data-class-name attribute for children section');
                return;
            }
            // Check if this is the first link in the header
            const headerElement = linkElement.closest('.contentHeader');
            if (!headerElement) {
                console.warn('Could not find header element');
                return;
            }
            const allLinks = headerElement.querySelectorAll('a');
            const firstLink = allLinks[0];
            const isFirstLink = firstLink === linkElement;
            const hasMultipleLinks = allLinks.length > 1;
            // Extract view type from link text content (fallback to text if no attribute)
            let viewType;
            if (isFirstLink && hasMultipleLinks) {
                // First link in multi-link headers: toggle behavior (detect current view and swap)
                const nextSibling = headerElement.nextElementSibling;
                if (!nextSibling) {
                    console.warn('Could not find next sibling element to detect current view');
                    return;
                }
                // Detect current view: if next sibling contains tiles, current view is 'tile', otherwise 'table'
                const hasTiles = nextSibling.querySelector('.pageTile') !== null;
                const hasTables = nextSibling.querySelector('table') !== null;
                if (hasTiles) {
                    // Currently showing tiles, swap to ungrouped table (view_type 'd')
                    viewType = 'd';
                }
                else if (hasTables) {
                    // Currently showing tables (grouped or ungrouped), swap to tiles
                    viewType = 'tile';
                }
                else {
                    // Default to 'd' if can't detect
                    viewType = 'd';
                }
            }
            else {
                // Other links: extract view type from link text content
                viewType = (linkElement.textContent || linkElement.innerText || '').trim();
                if (!viewType) {
                    console.warn('Could not extract view type from link text');
                    return;
                }
                // For non-first links when there are multiple links, use the link text as view_type
                // For single-link sections, toggle between table and tile based on current view
                if (!hasMultipleLinks) {
                    // Generic page view: toggle between table and tile
                    const nextSibling = headerElement.nextElementSibling;
                    if (!nextSibling) {
                        console.warn('Could not find next sibling element to detect current view');
                        return;
                    }
                    const hasTable = nextSibling.querySelector('table') !== null;
                    viewType = hasTable ? 'tile' : 'table';
                }
            }
            // Auto-detect if we're in an overlay by checking for overlay_ ID prefix
            const nextSibling = headerElement.nextElementSibling;
            const isInOverlay = headerElement.id.startsWith('overlay_') ||
                nextSibling?.id?.startsWith('overlay_') ||
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
            // Create context for callbacks
            const context = {
                pageId,
                section,
                className,
                viewType: viewType, // Type assertion for compatibility
                isInOverlay,
                linkElement
            };
            // Replace DOM chunks with callbacks
            this.replaceSectionContent(pageId, section, domContent, className, linkElement, context);
        }
        catch (error) {
            if (error instanceof RPCError) {
                this.rpc.showError('get_page_section', error);
            }
            else {
                console.error('Error handling view toggle:', error);
            }
        }
    }
    /**
     * Replace the section content in the DOM.
     * @param pageId - Page ID string
     * @param section - Section name (e.g., 'images', 'children')
     * @param htmlContent - HTML content to insert
     * @param className - Optional class name for children sections
     * @param linkElement - The toggle link element (to check if in overlay)
     * @param context - Context for callbacks
     */
    replaceSectionContent(pageId, section, htmlContent, className, linkElement, context) {
        // Call onBeforeSwap callback if provided (allows HTML modification)
        let processedHtml = htmlContent;
        if (this.callbacks.onBeforeSwap) {
            processedHtml = this.callbacks.onBeforeSwap(htmlContent, context);
        }
        // Create a temporary container to parse the HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = processedHtml;
        // Determine content element ID based on section type
        // Check if we're in an overlay (has overlay_ prefix)
        const isInOverlay = linkElement.closest('#overlayWindow') !== null;
        const prefix = isInOverlay ? 'overlay_' : '';
        let contentId;
        if (section === 'images') {
            contentId = `${prefix}pageImageGroup_${pageId}`;
        }
        else if (section === 'audio') {
            contentId = `${prefix}pageAudioGroup_${pageId}`;
        }
        else if (section === 'video') {
            contentId = `${prefix}pageVideoGroup_${pageId}`;
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
        // Find content element in the parsed HTML
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
        // Set up image viewer link interception for image sections (only on main page, not in overlays)
        if (section === 'images' && !isInOverlay) {
            this.setupImageViewerLinks(newElement, pageId);
        }
        // Set up audio viewer link interception for audio sections (only on main page, not in overlays)
        if (section === 'audio' && !isInOverlay) {
            this.setupAudioViewerLinks(newElement, pageId);
        }
        // Set up video viewer link interception for video sections (only on main page, not in overlays)
        if (section === 'video' && !isInOverlay) {
            this.setupVideoViewerLinks(newElement, pageId);
        }
        // Call onAfterSwap callback if provided (allows DOM manipulation after swap)
        if (this.callbacks.onAfterSwap) {
            // Find the container - use the parent of the replaced element or the element itself
            const container = newElement.parentElement || newElement;
            this.callbacks.onAfterSwap(container, context);
        }
    }
    /**
     * Set up image viewer link interception for image group links.
     */
    setupImageViewerLinks(container, pageId) {
        interceptLinks(container, {
            onImageLink: async (imageId, link) => {
                // Open image viewer with this image
                const { ImageViewer } = await import('./image-viewer.js');
                await ImageViewer.openFromImageLink(parseInt(pageId, 10), imageId);
            },
            markerProperty: '__imageViewerIntercepted'
        });
    }
    /**
     * Set up audio viewer link interception for audio group links.
     */
    setupAudioViewerLinks(container, pageId) {
        interceptLinks(container, {
            onAudioLink: async (audioId, link) => {
                // Open audio viewer with this audio file
                const { AudioViewer } = await import('./audio-viewer.js');
                await AudioViewer.openFromAudioLink(parseInt(pageId, 10), audioId);
            },
            markerProperty: '__audioViewerIntercepted'
        });
    }
    /**
     * Set up video viewer link interception for video group links.
     */
    setupVideoViewerLinks(container, pageId) {
        interceptLinks(container, {
            onVideoLink: async (videoId, link) => {
                // Open video viewer with this video file
                const { VideoViewer } = await import('./video-viewer.js');
                await VideoViewer.openFromVideoLink(parseInt(pageId, 10), videoId);
            },
            markerProperty: '__videoViewerIntercepted'
        });
    }
}
// Global view toggle instance (for main page)
let viewToggleInstance = null;
/**
 * Initialize the global view toggle system.
 * @param callbacks - Optional callbacks for the global instance
 */
export function initializeViewToggle(callbacks) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            viewToggleInstance = new ViewToggle(callbacks);
            setupInitialImageViewerLinks();
        });
    }
    else {
        viewToggleInstance = new ViewToggle(callbacks);
        setupInitialImageViewerLinks();
    }
}
/**
 * Set up image viewer links on initial page load.
 */
function setupInitialImageViewerLinks() {
    setTimeout(() => {
        const seedData = getSeedData();
        if (seedData && seedData.page && seedData.page.id && viewToggleInstance) {
            const pageId = seedData.page.id.toString();
            const imageGroup = document.getElementById(`pageImageGroup_${pageId}`);
            if (imageGroup) {
                viewToggleInstance.setupImageViewerLinks(imageGroup, pageId);
            }
            const audioGroup = document.getElementById(`pageAudioGroup_${pageId}`);
            if (audioGroup) {
                viewToggleInstance.setupAudioViewerLinks(audioGroup, pageId);
            }
            const videoGroup = document.getElementById(`pageVideoGroup_${pageId}`);
            if (videoGroup) {
                viewToggleInstance.setupVideoViewerLinks(videoGroup, pageId);
            }
        }
        else {
            console.warn('Could not set up viewer links - missing seed data or view toggle instance');
        }
    }, 100);
}
/**
 * Get the global view toggle instance.
 */
export function getViewToggleInstance() {
    return viewToggleInstance;
}
/**
 * Create a new view toggle instance with callbacks (useful for overlays).
 */
export function createViewToggle(callbacks) {
    return new ViewToggle(callbacks);
}

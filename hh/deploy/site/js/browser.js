/**
 * Browser - Hierarchical page/image/file selection overlay.
 * Allows users to navigate pages and select a single page or multiple images/files.
 */
import { OverlayManager } from './overlay/overlay-manager.js';
import { RPCClient } from './rpc-client.js';
import { getSeedData } from './seed.js';
import { getViewToggleInstance } from './view-toggle.js';
export class Browser {
    constructor(options) {
        this.overlay = null;
        this.selectedImageIds = [];
        this.selectedFileIds = [];
        this.viewToggle = null; // ViewToggle instance for this browser
        this.rpc = new RPCClient();
        this.mode = options.mode;
        this.onSubmit = options.onSubmit;
        this.onCancel = options.onCancel;
        // Determine initial page ID
        if (options.initialPageId) {
            this.currentPageId = options.initialPageId;
        }
        else {
            const seedData = getSeedData();
            const seedPageId = seedData.page?.id;
            this.currentPageId = (typeof seedPageId === 'number' ? seedPageId : 1);
        }
    }
    /**
     * Show the browser overlay.
     */
    async show() {
        await this.loadAndRender();
    }
    /**
     * Load browser content and render overlay.
     */
    async loadAndRender() {
        try {
            // Call get_browser MCP tool
            const result = await this.rpc.call('get_browser', { id: this.currentPageId });
            const browserData = result.data;
            if (!browserData) {
                throw new Error('get_browser did not return data');
            }
            const sections = browserData.sections || {};
            // Build content HTML
            const contentParts = [];
            // Add image buffer if in image mode
            if (this.mode === 'image' && this.selectedImageIds.length > 0) {
                contentParts.push(this.renderImageBuffer());
            }
            // Add file buffer if in file mode
            if (this.mode === 'file' && this.selectedFileIds.length > 0) {
                contentParts.push(this.renderFileBuffer());
            }
            // Add page sections (hide image groups in page mode)
            if (sections.path)
                contentParts.push(sections.path);
            if (sections.badges)
                contentParts.push(sections.badges);
            if (sections.text)
                contentParts.push(sections.text);
            if (sections.children)
                contentParts.push(sections.children);
            // Only show images section if not in page mode
            if (this.mode !== 'page' && sections.images) {
                contentParts.push(sections.images);
            }
            // Check if overlay already exists - if so, update it instead of creating new one
            if (this.overlay) {
                // Update existing overlay content
                this.updateOverlayContent(contentParts);
            }
            else {
                // Create new overlay
                const overlayManager = OverlayManager.getInstance();
                this.overlay = overlayManager.show({
                    header: this.getBrowserTitle(),
                    content: contentParts,
                    contentHeaders: contentParts.map(() => ''),
                    closable: true,
                    showSubmit: true,
                    submitLabel: this.getSubmitLabel(),
                    cancelLabel: 'Cancel',
                    onCancel: () => {
                        if (this.onCancel) {
                            this.onCancel();
                        }
                    },
                    onSubmit: async () => {
                        return await this.handleSubmit();
                    }
                });
            }
            // Set up view toggle with callbacks for this browser instance
            this.setupViewToggle();
            // Set up link interception after a short delay to ensure DOM is ready
            setTimeout(() => {
                this.injectAndIntercept();
            }, 50);
        }
        catch (error) {
            console.error('Error loading browser:', error);
            this.rpc.showError('browser', error);
        }
    }
    /**
     * Update existing overlay content without creating a new overlay.
     */
    updateOverlayContent(contentParts) {
        if (!this.overlay)
            return;
        const windowEl = document.getElementById('overlayWindow');
        if (!windowEl) {
            // Overlay was closed, create a new one
            this.overlay = null;
            this.loadAndRender();
            return;
        }
        // Find and clear the contentWrapper.overlay div (but keep the wrapper itself)
        let contentWrapper = windowEl.querySelector('.contentWrapper.overlay');
        // If contentWrapper doesn't exist, create it (shouldn't happen, but safety check)
        if (!contentWrapper) {
            const headerEl = windowEl.querySelector('.contentWrapperHeader.overlay');
            contentWrapper = document.createElement('div');
            contentWrapper.className = 'contentWrapper overlay';
            if (headerEl) {
                headerEl.insertAdjacentElement('afterend', contentWrapper);
            }
            else {
                windowEl.appendChild(contentWrapper);
            }
        }
        else {
            // Clear all children of the contentWrapper
            contentWrapper.innerHTML = '';
        }
        // Add new content - combine all parts into one HTML string
        const contentHTML = contentParts.join('');
        // Create a temporary container to parse the HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = contentHTML;
        // Insert each content element into the contentWrapper
        const elementsToInsert = Array.from(tempDiv.children);
        elementsToInsert.forEach(element => {
            contentWrapper.appendChild(element);
        });
        // Update submit button label
        const submitBtn = windowEl.querySelector('#submitOverlayWindow');
        if (submitBtn) {
            submitBtn.textContent = this.getSubmitLabel();
        }
        // Re-intercept links after content update
        this.interceptLinks(windowEl);
    }
    /**
     * Inject HTML content and set up link interception.
     */
    injectAndIntercept() {
        if (!this.overlay)
            return;
        const windowEl = document.getElementById('overlayWindow');
        if (!windowEl) {
            // Retry after a short delay if overlay not ready yet
            setTimeout(() => this.injectAndIntercept(), 100);
            return;
        }
        // Intercept all links
        this.interceptLinks(windowEl);
    }
    /**
     * Set up view toggle with callbacks to re-intercept links after content swaps.
     */
    setupViewToggle() {
        if (!this.overlay)
            return;
        const windowEl = document.getElementById('overlayWindow');
        if (!windowEl)
            return;
        // Get the global view toggle instance
        // Since view-toggle uses event delegation, we register callbacks with the global instance
        const globalViewToggle = getViewToggleInstance();
        if (globalViewToggle) {
            // Register callbacks that only run when swap is in this browser's overlay
            const callbacks = {
                onAfterSwap: (container, context) => {
                    // Only re-intercept if the swap happened in this browser's overlay
                    if (context.isInOverlay && windowEl.contains(container)) {
                        this.interceptLinks(windowEl);
                    }
                }
            };
            globalViewToggle.setCallbacks(callbacks);
            this.viewToggle = globalViewToggle;
        }
    }
    /**
     * Intercept all links in the browser content.
     */
    interceptLinks(container) {
        // Find all links
        const links = container.querySelectorAll('a[href]');
        links.forEach(link => {
            // Skip toggle links - let view-toggle.ts handle them
            if (link.classList.toString().includes('updatePageView_')) {
                return;
            }
            // Skip links that already have our click handler (avoid duplicate listeners)
            if (link.__browserIntercepted) {
                return;
            }
            const href = link.getAttribute('href');
            if (!href)
                return;
            // Check if it's a page link (starts with / and is numeric)
            const pageMatch = href.match(/^\/(\d+)$/);
            if (pageMatch) {
                const pageId = parseInt(pageMatch[1], 10);
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.retargetBrowser(pageId);
                });
                link.__browserIntercepted = true;
                return;
            }
            // Check if it's an image link (starts with /img/)
            const imageMatch = href.match(/^\/img\/(\d+)$/);
            if (imageMatch && (this.mode === 'image' || this.mode === 'file')) {
                const imageId = parseInt(imageMatch[1], 10);
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.handleImageClick(imageId);
                });
                link.__browserIntercepted = true;
                return;
            }
            // Check if it's a file link (starts with /file/)
            const fileMatch = href.match(/^\/file\/(.+)$/);
            if (fileMatch && this.mode === 'file') {
                // For now, we'll handle file selection later
                // Just prevent default navigation
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                });
                link.__browserIntercepted = true;
                return;
            }
        });
    }
    /**
     * Retarget browser to a new page.
     */
    async retargetBrowser(pageId) {
        this.currentPageId = pageId;
        await this.loadAndRender();
    }
    /**
     * Handle image click (add to buffer or remove from buffer).
     */
    handleImageClick(imageId) {
        if (this.mode !== 'image')
            return;
        const index = this.selectedImageIds.indexOf(imageId);
        if (index === -1) {
            // Add to buffer
            this.selectedImageIds.push(imageId);
        }
        else {
            // Remove from buffer
            this.selectedImageIds.splice(index, 1);
        }
        // Re-render to update buffer
        this.loadAndRender();
    }
    /**
     * Handle submit - call callback with result.
     */
    async handleSubmit() {
        let result;
        let message;
        if (this.mode === 'page') {
            result = this.currentPageId;
            message = `Page ${result} selected successfully`;
        }
        else if (this.mode === 'image') {
            if (this.selectedImageIds.length === 0) {
                throw new Error('Please select at least one image');
            }
            result = [...this.selectedImageIds];
            message = `${result.length} image${result.length !== 1 ? 's' : ''} selected: ${result.join(', ')}`;
        }
        else {
            if (this.selectedFileIds.length === 0) {
                throw new Error('Please select at least one file');
            }
            result = [...this.selectedFileIds];
            message = `${result.length} file${result.length !== 1 ? 's' : ''} selected: ${result.join(', ')}`;
        }
        try {
            await this.onSubmit(result);
            // Show success with ID information and auto-close after delay
            return {
                _showMessage: message,
                _autoFade: true
            };
        }
        catch (error) {
            throw error;
        }
    }
    /**
     * Render image buffer (tiles + table).
     */
    renderImageBuffer() {
        if (this.selectedImageIds.length === 0) {
            return '';
        }
        // TODO: Fetch image data for selected IDs and render tiles + table
        // For now, just show a simple list
        const imageList = this.selectedImageIds.map(id => `Image ${id}`).join(', ');
        return `<div class="browser-buffer"><strong>Selected Images:</strong> ${imageList}</div>`;
    }
    /**
     * Render file buffer (tiles + table).
     */
    renderFileBuffer() {
        if (this.selectedFileIds.length === 0) {
            return '';
        }
        // TODO: Implement file buffer rendering
        return '';
    }
    /**
     * Get browser title based on mode.
     */
    getBrowserTitle() {
        switch (this.mode) {
            case 'page':
                return 'Select Page';
            case 'image':
                return 'Select Images';
            case 'file':
                return 'Select Files';
            default:
                return 'Browser';
        }
    }
    /**
     * Get submit button label based on mode and selection.
     */
    getSubmitLabel() {
        if (this.mode === 'page') {
            return 'Select Page';
        }
        else if (this.mode === 'image') {
            const count = this.selectedImageIds.length;
            return count > 0 ? `Submit ${count} Image${count !== 1 ? 's' : ''}` : 'Submit';
        }
        else {
            const count = this.selectedFileIds.length;
            return count > 0 ? `Submit ${count} File${count !== 1 ? 's' : ''}` : 'Submit';
        }
    }
}

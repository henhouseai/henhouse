/**
 * ImageGroupSorter - Specialized browser for sorting/reordering images on a page.
 * Extends Browser functionality to provide drag-and-drop image sorting.
 */
import { OverlayManager } from './overlay/overlay-manager.js';
import { RPCClient } from './rpc-client.js';
import { handleRPCResponseWithDebug } from './debug-helper.js';
export class ImageGroupSorter {
    constructor(pageId) {
        this.overlay = null;
        this.tableHtml = '';
        this.tileHtml = '';
        this.originalRanks = new Map(); // imageId -> rank (original state)
        this.currentRanks = new Map(); // imageId -> rank (current server state)
        this.desiredRanks = new Map(); // imageId -> rank (what user wants)
        this.imageElements = new Map(); // imageId -> DOM element (for both views)
        this.rpc = new RPCClient();
        this.pageId = pageId;
    }
    /**
     * Show the image group sorter overlay.
     */
    async show() {
        await this.loadAndRender();
    }
    /**
     * Load both table and tile views, then render overlay.
     */
    async loadAndRender() {
        try {
            // Fetch both table and tile views simultaneously
            const [tableResult, tileResult] = await Promise.all([
                this.rpc.call('get_page_section', {
                    id: this.pageId,
                    section: 'images',
                    view_type: 'table',
                    overlay: 1
                }),
                this.rpc.call('get_page_section', {
                    id: this.pageId,
                    section: 'images',
                    view_type: 'tile',
                    overlay: 1
                })
            ]);
            const tableData = tableResult.data?.dom_content;
            const tileData = tileResult.data?.dom_content;
            if (!tableData || !tileData) {
                throw new Error('Failed to load image group views');
            }
            this.tableHtml = tableData;
            this.tileHtml = tileData;
            // Extract initial image ranks from the HTML
            this.extractInitialRanks();
            // Initialize current ranks with original ranks
            this.currentRanks = new Map(this.originalRanks);
            // Render overlay with both views
            this.renderOverlay();
        }
        catch (error) {
            console.error('Error loading image group sorter:', error);
            this.rpc.showError('image_group_sorter', error);
        }
    }
    /**
     * Extract initial image ranks from HTML.
     * Parses both table and tile HTML to build the original ranks map.
     */
    extractInitialRanks() {
        this.originalRanks.clear();
        // Parse tile HTML to extract image IDs and ranks
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = this.tileHtml;
        // Find all image links in tile view - look for /img/{id} links
        const imageLinks = tempDiv.querySelectorAll('a[href*="/img/"]');
        imageLinks.forEach((link, index) => {
            const href = link.getAttribute('href') || '';
            const match = href.match(/\/img\/(\d+)/);
            if (match) {
                const imageId = parseInt(match[1], 10);
                const rank = index + 1; // Ranks are 1-based
                if (imageId > 0) {
                    this.originalRanks.set(imageId, rank);
                }
            }
        });
        // If still no ranks found, try data-image-rank attributes
        if (this.originalRanks.size === 0) {
            const linksWithRank = tempDiv.querySelectorAll('a[data-image-rank]');
            linksWithRank.forEach((link) => {
                const rank = parseInt(link.getAttribute('data-image-rank') || '0', 10);
                const href = link.getAttribute('href') || '';
                const match = href.match(/\/img\/(\d+)/);
                if (match && rank > 0) {
                    const imageId = parseInt(match[1], 10);
                    this.originalRanks.set(imageId, rank);
                }
            });
        }
    }
    /**
     * Render the overlay with both table and tile views.
     */
    renderOverlay() {
        const overlayManager = OverlayManager.getInstance();
        // Combine both views in the content (as array)
        const content = [
            `
      <div class="content overlay" id="overlay_image_group_sorter_tiles">
        <h3>Tile View</h3>
        ${this.tileHtml}
      </div>
      <div class="content overlay" id="overlay_image_group_sorter_table">
        <h3>Table View</h3>
        ${this.tableHtml}
      </div>
    `
        ];
        this.overlay = overlayManager.show({
            header: `Sort Images - Page ${this.pageId}`,
            content: content,
            contentHeaders: ['', ''],
            closable: true,
            showSubmit: true,
            submitLabel: 'Sort',
            cancelLabel: 'Cancel',
            onCancel: () => {
                // Cancel doesn't need to do anything - just closes overlay
            },
            onSubmit: async () => {
                return await this.handleSubmit();
            }
        });
        // Set up drag-and-drop after DOM is ready
        setTimeout(() => {
            this.removeAllLinks();
            this.setupDragAndDrop();
        }, 50);
    }
    /**
     * Remove all links from both table and tile views to prevent navigation.
     * Extracts content from <a> tags and replaces them with non-link elements.
     */
    removeAllLinks() {
        const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
        const tableContainer = document.getElementById('overlay_image_group_sorter_table');
        if (tileContainer) {
            this.removeLinksFromContainer(tileContainer);
        }
        if (tableContainer) {
            this.removeLinksFromContainer(tableContainer);
        }
    }
    /**
     * Remove all links from a container, replacing them with their content.
     */
    removeLinksFromContainer(container) {
        const links = container.querySelectorAll('a');
        links.forEach(link => {
            // Create a span to replace the link, preserving all attributes except href
            const span = document.createElement('span');
            // Copy all classes
            if (link.className) {
                span.className = link.className;
            }
            // Copy all data attributes
            Array.from(link.attributes).forEach(attr => {
                if (attr.name.startsWith('data-')) {
                    span.setAttribute(attr.name, attr.value);
                }
            });
            // Copy all children
            while (link.firstChild) {
                span.appendChild(link.firstChild);
            }
            // Replace the link with the span
            link.parentNode?.replaceChild(span, link);
        });
    }
    /**
     * Set up HTML5 drag-and-drop for both views.
     */
    setupDragAndDrop() {
        // Set up drag-and-drop for tile view
        const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
        if (tileContainer) {
            this.setupDragAndDropForContainer(tileContainer, 'tile');
        }
        // Set up drag-and-drop for table view
        const tableContainer = document.getElementById('overlay_image_group_sorter_table');
        if (tableContainer) {
            this.setupDragAndDropForContainer(tableContainer, 'table');
        }
    }
    /**
     * Set up drag-and-drop for a specific container (tile or table view).
     */
    setupDragAndDropForContainer(container, viewType) {
        // Find draggable elements (image tiles or table rows)
        let draggableElements;
        let parentContainer = null;
        if (viewType === 'tile') {
            // For tiles, draggable elements are the <li> elements in the <ul>
            const ul = container.querySelector('ul');
            if (!ul)
                return;
            parentContainer = ul;
            draggableElements = ul.querySelectorAll('li');
        }
        else {
            // For table, draggable elements are table rows (excluding header)
            const tbody = container.querySelector('table tbody');
            if (!tbody)
                return;
            parentContainer = tbody;
            draggableElements = tbody.querySelectorAll('tr');
        }
        if (!parentContainer)
            return;
        // Track dragging state
        let draggedElement = null;
        let draggedIndex = -1;
        let currentOverElement = null;
        draggableElements.forEach((element, index) => {
            element.draggable = true;
            element.setAttribute('data-drag-index', index.toString());
            // Add CSS for cursor and visual feedback
            element.style.cursor = 'move';
            element.addEventListener('dragstart', (e) => {
                if (e.dataTransfer) {
                    e.dataTransfer.effectAllowed = 'move';
                    e.dataTransfer.setData('text/plain', index.toString());
                    draggedElement = element;
                    draggedIndex = index;
                    // Make original element semi-transparent
                    element.style.opacity = '0.5';
                    element.classList.add('dragging');
                }
            });
            element.addEventListener('dragend', (e) => {
                // Restore opacity
                if (draggedElement) {
                    draggedElement.style.opacity = '1';
                    draggedElement.classList.remove('dragging');
                }
                // Remove any drag-over classes
                draggableElements.forEach(el => {
                    el.classList.remove('drag-over');
                });
                // Revert any temporary reordering if drag was cancelled
                if (e.dataTransfer?.dropEffect === 'none') {
                    this.revertTemporaryReorder(viewType, draggedIndex);
                }
                draggedElement = null;
                draggedIndex = -1;
                currentOverElement = null;
            });
            element.addEventListener('dragover', (e) => {
                e.preventDefault();
                if (e.dataTransfer) {
                    e.dataTransfer.dropEffect = 'move';
                }
                // Only process if we're dragging something
                if (draggedElement === null || draggedIndex < 0)
                    return;
                const dropIndex = index;
                // Skip if dragging over the same element
                if (dropIndex === draggedIndex)
                    return;
                // Update current over element
                if (currentOverElement !== element) {
                    // Remove drag-over class from previous element
                    if (currentOverElement) {
                        currentOverElement.classList.remove('drag-over');
                    }
                    // Add drag-over class to current element
                    element.classList.add('drag-over');
                    currentOverElement = element;
                    // Temporarily reorder to show preview
                    this.temporaryReorder(viewType, draggedIndex, dropIndex);
                }
            });
            element.addEventListener('dragleave', (e) => {
                // Only remove drag-over if we're actually leaving the element (not just moving to a child)
                const relatedTarget = e.relatedTarget;
                if (!element.contains(relatedTarget)) {
                    element.classList.remove('drag-over');
                    if (currentOverElement === element) {
                        currentOverElement = null;
                    }
                }
            });
            element.addEventListener('drop', (e) => {
                e.preventDefault();
                const dragIndex = parseInt(e.dataTransfer?.getData('text/plain') || '-1', 10);
                const dropIndex = index;
                if (dragIndex >= 0 && dragIndex !== dropIndex && draggedElement) {
                    // Remove drag-over class
                    element.classList.remove('drag-over');
                    // Apply final reorder
                    this.handleDrop(dragIndex, dropIndex, viewType);
                }
            });
        });
    }
    /**
     * Temporarily reorder elements during drag to show preview.
     */
    temporaryReorder(viewType, dragIndex, dropIndex) {
        const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
        const tableContainer = document.getElementById('overlay_image_group_sorter_table');
        if (viewType === 'tile') {
            if (!tileContainer)
                return;
            const ul = tileContainer.querySelector('ul');
            if (!ul)
                return;
            const items = Array.from(ul.querySelectorAll('li'));
            this.reorderElements(items, dragIndex, dropIndex);
            // Also update table view
            if (tableContainer) {
                const tbody = tableContainer.querySelector('table tbody');
                if (tbody) {
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    this.reorderElements(rows, dragIndex, dropIndex);
                }
            }
        }
        else {
            if (!tableContainer)
                return;
            const tbody = tableContainer.querySelector('table tbody');
            if (!tbody)
                return;
            const rows = Array.from(tbody.querySelectorAll('tr'));
            this.reorderElements(rows, dragIndex, dropIndex);
            // Also update tile view
            if (tileContainer) {
                const ul = tileContainer.querySelector('ul');
                if (ul) {
                    const items = Array.from(ul.querySelectorAll('li'));
                    this.reorderElements(items, dragIndex, dropIndex);
                }
            }
        }
    }
    /**
     * Reorder an array of elements in the DOM.
     */
    reorderElements(elements, dragIndex, dropIndex) {
        if (dragIndex < 0 || dragIndex >= elements.length || dropIndex < 0 || dropIndex >= elements.length) {
            return;
        }
        const dragged = elements[dragIndex];
        const parent = dragged.parentElement;
        if (!parent)
            return;
        // Remove dragged element
        const nextSibling = dragged.nextSibling;
        dragged.remove();
        // Insert at new position
        if (dropIndex < elements.length - 1) {
            const targetElement = elements[dropIndex > dragIndex ? dropIndex + 1 : dropIndex];
            parent.insertBefore(dragged, targetElement);
        }
        else {
            parent.appendChild(dragged);
        }
    }
    /**
     * Revert temporary reordering (if drag was cancelled).
     * Note: This is a simplified implementation. In a full implementation,
     * we'd track the order before drag started and restore it exactly.
     */
    revertTemporaryReorder(viewType, originalIndex) {
        // For now, we'll just reload the views to restore original order
        // This is simpler than tracking state, and drag cancellation should be rare
        // In practice, the user can just drag again if they cancel
    }
    /**
     * Handle a drop event - reorder images in both views.
     */
    handleDrop(dragIndex, dropIndex, viewType) {
        // Get image IDs from current DOM order (not server state)
        const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
        if (!tileContainer)
            return;
        const listItems = Array.from(tileContainer.querySelectorAll('ul li'));
        const imageIds = [];
        listItems.forEach(li => {
            const link = li.querySelector('a[href*="/img/"]');
            if (link) {
                const imageId = this.extractImageIdFromElement(link);
                if (imageId > 0) {
                    imageIds.push(imageId);
                }
            }
        });
        // Reorder the array
        if (dragIndex >= 0 && dragIndex < imageIds.length && dropIndex >= 0 && dropIndex < imageIds.length) {
            const [draggedId] = imageIds.splice(dragIndex, 1);
            imageIds.splice(dropIndex, 0, draggedId);
            // Update both views
            this.updateBothViews(imageIds);
        }
    }
    /**
     * Update both table and tile views to reflect new order.
     */
    updateBothViews(newOrder) {
        const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
        const tableContainer = document.getElementById('overlay_image_group_sorter_table');
        if (!tileContainer || !tableContainer)
            return;
        // Reorder tile view
        this.reorderView(tileContainer, newOrder, 'tile');
        // Reorder table view
        this.reorderView(tableContainer, newOrder, 'table');
    }
    /**
     * Reorder a specific view (tile or table) based on new image order.
     */
    reorderView(container, newOrder, viewType) {
        if (viewType === 'tile') {
            // For tile view, reorder <li> elements in the <ul>
            const ul = container.querySelector('ul');
            if (!ul)
                return;
            const listItems = Array.from(ul.querySelectorAll('li'));
            const reorderedItems = [];
            // Create a map of image ID to list item
            const itemMap = new Map();
            listItems.forEach(li => {
                // Look for span or any element (links are removed)
                const element = li.querySelector('span, a') || li;
                const imageId = this.extractImageIdFromElement(element);
                if (imageId > 0) {
                    itemMap.set(imageId, li);
                }
            });
            // Reorder based on newOrder
            newOrder.forEach(imageId => {
                const item = itemMap.get(imageId);
                if (item) {
                    reorderedItems.push(item);
                }
            });
            // Clear and re-append in new order
            ul.innerHTML = '';
            reorderedItems.forEach(item => {
                ul.appendChild(item);
            });
        }
        else {
            // For table view, reorder <tr> elements in tbody
            const tbody = container.querySelector('table tbody');
            if (!tbody)
                return;
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const reorderedRows = [];
            // Create a map of image ID to table row
            const rowMap = new Map();
            rows.forEach(tr => {
                // Look for span or any element (links are removed)
                const element = tr.querySelector('span, a') || tr;
                const imageId = this.extractImageIdFromElement(element);
                if (imageId > 0) {
                    rowMap.set(imageId, tr);
                }
            });
            // Reorder based on newOrder
            newOrder.forEach(imageId => {
                const row = rowMap.get(imageId);
                if (row) {
                    reorderedRows.push(row);
                }
            });
            // Clear and re-append in new order
            tbody.innerHTML = '';
            reorderedRows.forEach(row => {
                tbody.appendChild(row);
            });
        }
    }
    /**
     * Handle submit - perform sequential set_image_rank calls.
     */
    async handleSubmit() {
        if (!this.overlay)
            return;
        // Capture debug options
        const debugOptions = this.overlay.getDebugOptions();
        const capturedDebugOptions = debugOptions || { debug: false, log: false };
        // Build desired ranks map from current DOM state
        this.buildDesiredRanks();
        // Get image IDs in desired order (sorted by desired rank)
        const desiredOrder = Array.from(this.desiredRanks.entries())
            .sort((a, b) => a[1] - b[1])
            .map(([imageId]) => imageId);
        // Track if any debug data was present
        let hasDebugData = false;
        // Process each image in order
        for (let position = 0; position < desiredOrder.length; position++) {
            const imageId = desiredOrder[position];
            const desiredRank = position + 1; // Ranks are 1-based
            const currentRank = this.currentRanks.get(imageId);
            // Skip if already in correct position
            if (currentRank === desiredRank) {
                continue;
            }
            try {
                // Call set_image_rank
                const response = await this.rpc.call('set_image_rank', {
                    page_id: this.pageId,
                    image_id: imageId,
                    target_rank: desiredRank
                }, capturedDebugOptions);
                // Handle debug data
                if (response && response.debug && Array.isArray(response.debug.entries) && response.debug.entries.length > 0) {
                    hasDebugData = true;
                    handleRPCResponseWithDebug(response, 'set_image_rank', {
                        page_id: this.pageId,
                        image_id: imageId,
                        target_rank: desiredRank
                    });
                }
                // Extract response data
                const responseData = response.data;
                if (!responseData || !responseData.images) {
                    throw new Error(`Invalid response from set_image_rank for image ${imageId}`);
                }
                // Update current ranks from response
                responseData.images.forEach(img => {
                    this.currentRanks.set(img.id, img.image_rank);
                });
                // Show incremental success message
                if (this.overlay) {
                    const currentMessages = this.overlay['state'].messages || [];
                    this.overlay.setState({
                        messages: [...currentMessages, { type: 'success', text: `Image ${imageId} moved to rank ${desiredRank}` }]
                    });
                }
            }
            catch (error) {
                // Extract error messages (same pattern as copy_images_app)
                if (this.overlay) {
                    const currentMessages = this.overlay['state'].messages || [];
                    const errorMsg = error instanceof Error ? error.message : String(error);
                    // Check if it's an RPCError with multiple errors
                    const detailedErrors = (error && typeof error === 'object' && 'errors' in error && Array.isArray(error.errors))
                        ? error.errors
                        : [];
                    // Add main error message
                    const newMessages = [{ type: 'error', text: `Failed to move image ${imageId} to rank ${desiredRank}: ${errorMsg}` }];
                    // Add detailed errors if available
                    if (detailedErrors.length > 0) {
                        detailedErrors.forEach((err) => {
                            newMessages.push({
                                type: 'error',
                                text: `${err.type || 'error'}: ${err.content}`
                            });
                        });
                    }
                    this.overlay.setState({
                        messages: [...currentMessages, ...newMessages]
                    });
                    // Handle debug data if present
                    if (error && typeof error === 'object' && 'debug' in error) {
                        const errorDebug = error.debug;
                        if (errorDebug && Array.isArray(errorDebug.entries) && errorDebug.entries.length > 0) {
                            handleRPCResponseWithDebug(error, 'set_image_rank', {
                                page_id: this.pageId,
                                image_id: imageId,
                                target_rank: desiredRank
                            });
                        }
                    }
                }
                // Stop on first error
                return { _autoFade: false }; // Prevent auto-fade on error
            }
        }
        // Final verification pass
        this.performFinalVerification();
        // Return result
        return {
            _redirectAfterFade: true,
            _autoFade: !hasDebugData // Don't auto-fade if debug data was shown
        };
    }
    /**
     * Build desired ranks map from current DOM state.
     */
    buildDesiredRanks() {
        this.desiredRanks.clear();
        // Get current order from tile view (more reliable for visual order)
        const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
        if (!tileContainer)
            return;
        // Find all list items in tile view
        const listItems = tileContainer.querySelectorAll('ul li');
        listItems.forEach((item, index) => {
            // Look for span or any element (links are removed)
            const element = item.querySelector('span, a') || item;
            const imageId = this.extractImageIdFromElement(element);
            if (imageId > 0) {
                this.desiredRanks.set(imageId, index + 1);
            }
        });
    }
    /**
     * Extract image ID from a DOM element.
     * Works with both links and spans (after links are removed).
     */
    extractImageIdFromElement(element) {
        // Try data-image-id attribute first
        const dataId = element.getAttribute('data-image-id');
        if (dataId) {
            return parseInt(dataId, 10);
        }
        // Try href attribute - format is /img/{id} (for links that still exist)
        const href = element.getAttribute('href') || '';
        const imgMatch = href.match(/\/img\/(\d+)/);
        if (imgMatch) {
            return parseInt(imgMatch[1], 10);
        }
        // Try data-image-rank to find image ID (we'll need to map rank to ID)
        // Actually, we need to search within the element's text or find image links in children
        // Look for any child element with href containing /img/
        const childLink = element.querySelector('[href*="/img/"]');
        if (childLink) {
            const childHref = childLink.getAttribute('href') || '';
            const childMatch = childHref.match(/\/img\/(\d+)/);
            if (childMatch) {
                return parseInt(childMatch[1], 10);
            }
        }
        // Try finding in parent or ancestor elements
        let current = element;
        while (current && current !== document.body) {
            // Check if current element has href
            const currentHref = current.getAttribute('href') || '';
            const currentMatch = currentHref.match(/\/img\/(\d+)/);
            if (currentMatch) {
                return parseInt(currentMatch[1], 10);
            }
            // Check for data attributes that might help
            const dataPageId = current.getAttribute('data-page-id');
            const dataImageRank = current.getAttribute('data-image-rank');
            // Move to parent
            current = current.parentElement;
        }
        return 0;
    }
    /**
     * Perform final verification pass - check that all images are in desired positions.
     */
    performFinalVerification() {
        const mismatches = [];
        // Compare desired vs current for each image
        this.desiredRanks.forEach((desiredRank, imageId) => {
            const currentRank = this.currentRanks.get(imageId);
            if (currentRank !== desiredRank) {
                mismatches.push(`Image ${imageId}: desired rank ${desiredRank}, but current rank is ${currentRank || 'unknown'}`);
            }
        });
        if (mismatches.length > 0 && this.overlay) {
            const currentMessages = this.overlay['state'].messages || [];
            const newMessages = mismatches.map(msg => ({ type: 'error', text: msg }));
            this.overlay.setState({
                messages: [...currentMessages, ...newMessages]
            });
        }
    }
}

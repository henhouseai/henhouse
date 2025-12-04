/**
 * ImageGroupSorter - Specialized browser for sorting/reordering images on a page.
 * Uses SortableJS for drag-and-drop functionality.
 */
import { OverlayManager } from './overlay/overlay-manager.js';
import { RPCClient } from './rpc-client.js';
import { handleRPCResponseWithDebug } from './debug-helper.js';
// Import SortableJS as a side-effect (it will be available as window.Sortable)
import './sortable.min.js';
const Sortable = window.Sortable;
export class ImageGroupSorter {
    constructor(pageId) {
        this.overlay = null;
        this.tableHtml = '';
        this.tileHtml = '';
        this.originalRanks = new Map(); // imageId -> rank (original state)
        this.currentRanks = new Map(); // imageId -> rank (current server state)
        this.desiredRanks = new Map(); // imageId -> rank (what user wants)
        this.sortableTile = null; // Sortable instance for tiles
        this.sortableTable = null; // Sortable instance for table
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
            this.setupSortable();
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
     * Set up SortableJS for both tile and table views.
     */
    setupSortable() {
        const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
        const tableContainer = document.getElementById('overlay_image_group_sorter_table');
        // Set up Sortable for tile view (<ul> with <li> elements)
        if (tileContainer) {
            const ul = tileContainer.querySelector('ul');
            if (ul) {
                // Add data-id attributes to list items for SortableJS sort() method
                const listItems = ul.querySelectorAll('li');
                listItems.forEach((li, index) => {
                    const element = li.querySelector('span, a') || li;
                    const imageId = this.extractImageIdFromElement(element);
                    if (imageId > 0) {
                        li.setAttribute('data-id', imageId.toString());
                    }
                });
                this.sortableTile = Sortable.create(ul, {
                    animation: 150,
                    dataIdAttr: 'data-id',
                    onEnd: (evt) => {
                        // Use setTimeout to let SortableJS finish its internal cleanup
                        setTimeout(() => {
                            this.syncTableToTile();
                        }, 100);
                    }
                });
            }
        }
        // Set up Sortable for table view (<tbody> with <tr> elements)
        if (tableContainer) {
            const tbody = tableContainer.querySelector('table tbody');
            if (tbody) {
                // Add data-id attributes to table rows for SortableJS sort() method
                const rows = tbody.querySelectorAll('tr');
                rows.forEach((tr) => {
                    const element = tr.querySelector('span, a') || tr;
                    const imageId = this.extractImageIdFromElement(element);
                    if (imageId > 0) {
                        tr.setAttribute('data-id', imageId.toString());
                    }
                });
                this.sortableTable = Sortable.create(tbody, {
                    animation: 150,
                    dataIdAttr: 'data-id',
                    onEnd: (evt) => {
                        // Use setTimeout to let SortableJS finish its internal cleanup
                        setTimeout(() => {
                            this.syncTileToTable();
                            this.recalculateZebraStripes(tbody);
                        }, 100);
                    }
                });
            }
        }
    }
    /**
     * Sync table view to match tile view order.
     */
    syncTableToTile() {
        const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
        const tableContainer = document.getElementById('overlay_image_group_sorter_table');
        if (!tileContainer || !tableContainer)
            return;
        const tileListItems = Array.from(tileContainer.querySelectorAll('ul li'));
        const imageIds = [];
        // Extract image IDs from tile view in current order using data-id attributes
        tileListItems.forEach(li => {
            const dataId = li.getAttribute('data-id');
            if (dataId) {
                const imageId = parseInt(dataId, 10);
                if (imageId > 0) {
                    imageIds.push(imageId);
                }
            }
            else {
                // Fallback to extraction if data-id not found
                const element = li.querySelector('span, a') || li;
                const imageId = this.extractImageIdFromElement(element);
                if (imageId > 0) {
                    imageIds.push(imageId);
                }
            }
        });
        // Reorder table rows to match
        this.reorderTableRows(imageIds);
    }
    /**
     * Sync tile view to match table view order.
     */
    syncTileToTable() {
        const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
        const tableContainer = document.getElementById('overlay_image_group_sorter_table');
        if (!tileContainer || !tableContainer)
            return;
        const tableRows = Array.from(tableContainer.querySelectorAll('table tbody tr'));
        const imageIds = [];
        // Extract image IDs from table view in current order using data-id attributes
        tableRows.forEach(tr => {
            const dataId = tr.getAttribute('data-id');
            if (dataId) {
                const imageId = parseInt(dataId, 10);
                if (imageId > 0) {
                    imageIds.push(imageId);
                }
            }
            else {
                // Fallback to extraction if data-id not found
                const element = tr.querySelector('span, a') || tr;
                const imageId = this.extractImageIdFromElement(element);
                if (imageId > 0) {
                    imageIds.push(imageId);
                }
            }
        });
        // Reorder tile list items to match
        this.reorderTileItems(imageIds);
    }
    /**
     * Reorder table rows based on image ID order using SortableJS sort() method.
     */
    reorderTableRows(imageIds) {
        if (!this.sortableTable)
            return;
        // Convert image IDs to strings (SortableJS sort() expects string array)
        const idStrings = imageIds.map(id => id.toString());
        // Temporarily disable to prevent triggering onEnd
        this.sortableTable.option('disabled', true);
        // Use SortableJS's sort() method to reorder programmatically
        this.sortableTable.sort(idStrings);
        // Recalculate zebra striping
        const tableContainer = document.getElementById('overlay_image_group_sorter_table');
        if (tableContainer) {
            const tbody = tableContainer.querySelector('table tbody');
            if (tbody) {
                this.recalculateZebraStripes(tbody);
            }
        }
        // Re-enable Sortable
        this.sortableTable.option('disabled', false);
    }
    /**
     * Reorder tile list items based on image ID order using SortableJS sort() method.
     */
    reorderTileItems(imageIds) {
        if (!this.sortableTile)
            return;
        // Convert image IDs to strings (SortableJS sort() expects string array)
        const idStrings = imageIds.map(id => id.toString());
        // Temporarily disable to prevent triggering onEnd
        this.sortableTile.option('disabled', true);
        // Use SortableJS's sort() method to reorder programmatically
        this.sortableTile.sort(idStrings);
        // Re-enable Sortable
        this.sortableTile.option('disabled', false);
    }
    /**
     * Recalculate zebra striping for table rows.
     * Only counts data rows in tbody (header row in thead is separate).
     * Header is even (index 0), so first tbody row should be odd (index 0), second even (index 1), etc.
     */
    recalculateZebraStripes(tbody) {
        const rows = Array.from(tbody.querySelectorAll('tr'));
        rows.forEach((row, index) => {
            // Remove existing even/odd classes
            row.classList.remove('even', 'odd');
            // Flip the logic: first tbody row (index 0) should be odd (since header is even)
            if (index % 2 === 0) {
                row.classList.add('odd');
            }
            else {
                row.classList.add('even');
            }
        });
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

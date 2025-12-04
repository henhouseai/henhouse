/**
 * ImageGroupSorter - Specialized browser for sorting/reordering images on a page.
 * Extends Browser functionality to provide drag-and-drop image sorting.
 */

import { OverlayManager } from './overlay/overlay-manager.js';
import { Overlay } from './overlay/overlay.js';
import { RPCClient } from './rpc-client.js';
import { getSeedData } from './seed.js';
import { handleRPCResponseWithDebug } from './debug-helper.js';

interface ImageRank {
  imageId: number;
  rank: number;
  caption: string;
}

interface SetImageRankResponse {
  page_id: number;
  image_id: number;
  source_rank: number;
  target_rank: number;
  images: Array<{
    id: number;
    image_rank: number;
    caption: string;
  }>;
}

export class ImageGroupSorter {
  private rpc: RPCClient;
  private overlay: Overlay | null = null;
  private pageId: number;
  private tableHtml: string = '';
  private tileHtml: string = '';
  private originalRanks: Map<number, number> = new Map(); // imageId -> rank (original state)
  private currentRanks: Map<number, number> = new Map(); // imageId -> rank (current server state)
  private desiredRanks: Map<number, number> = new Map(); // imageId -> rank (what user wants)
  private imageElements: Map<number, HTMLElement> = new Map(); // imageId -> DOM element (for both views)

  constructor(pageId: number) {
    this.rpc = new RPCClient();
    this.pageId = pageId;
  }

  /**
   * Show the image group sorter overlay.
   */
  async show(): Promise<void> {
    await this.loadAndRender();
  }

  /**
   * Load both table and tile views, then render overlay.
   */
  private async loadAndRender(): Promise<void> {
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

    } catch (error) {
      console.error('Error loading image group sorter:', error);
      this.rpc.showError('image_group_sorter', error);
    }
  }

  /**
   * Extract initial image ranks from HTML.
   * Parses both table and tile HTML to build the original ranks map.
   */
  private extractInitialRanks(): void {
    this.originalRanks.clear();
    
    // Parse tile HTML to extract image IDs and ranks
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = this.tileHtml;
    
    // Find all image links in tile view - look for /img/{id} links
    const imageLinks = tempDiv.querySelectorAll('a[href*="/img/"]');
    imageLinks.forEach((link, index) => {
      const href = (link as HTMLElement).getAttribute('href') || '';
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
        const rank = parseInt((link as HTMLElement).getAttribute('data-image-rank') || '0', 10);
        const href = (link as HTMLElement).getAttribute('href') || '';
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
  private renderOverlay(): void {
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
      this.setupDragAndDrop();
    }, 50);
  }

  /**
   * Set up HTML5 drag-and-drop for both views.
   */
  private setupDragAndDrop(): void {
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
  private setupDragAndDropForContainer(container: HTMLElement, viewType: 'tile' | 'table'): void {
    // Find draggable elements (image tiles or table rows)
    let draggableElements: NodeListOf<HTMLElement>;
    
    if (viewType === 'tile') {
      // For tiles, draggable elements are the image links or their parent containers
      draggableElements = container.querySelectorAll('a[href*="image"], .tile, .imageTile') as NodeListOf<HTMLElement>;
    } else {
      // For table, draggable elements are table rows (excluding header)
      draggableElements = container.querySelectorAll('table tbody tr') as NodeListOf<HTMLElement>;
    }

    draggableElements.forEach((element, index) => {
      element.draggable = true;
      element.setAttribute('data-drag-index', index.toString());
      
      element.addEventListener('dragstart', (e) => {
        if (e.dataTransfer) {
          e.dataTransfer.effectAllowed = 'move';
          e.dataTransfer.setData('text/plain', index.toString());
          element.classList.add('dragging');
        }
      });

      element.addEventListener('dragend', () => {
        element.classList.remove('dragging');
      });

      element.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (e.dataTransfer) {
          e.dataTransfer.dropEffect = 'move';
        }
      });

      element.addEventListener('drop', (e) => {
        e.preventDefault();
        const dragIndex = parseInt(e.dataTransfer?.getData('text/plain') || '-1', 10);
        const dropIndex = index;
        
        if (dragIndex >= 0 && dragIndex !== dropIndex) {
          this.handleDrop(dragIndex, dropIndex, viewType);
        }
      });
    });
  }

  /**
   * Handle a drop event - reorder images in both views.
   */
  private handleDrop(dragIndex: number, dropIndex: number, viewType: 'tile' | 'table'): void {
    // Get image IDs from current DOM order (not server state)
    const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
    if (!tileContainer) return;

    const listItems = Array.from(tileContainer.querySelectorAll('ul li'));
    const imageIds: number[] = [];

    listItems.forEach(li => {
      const link = li.querySelector('a[href*="/img/"]');
      if (link) {
        const imageId = this.extractImageIdFromElement(link as HTMLElement);
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
  private updateBothViews(newOrder: number[]): void {
    const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
    const tableContainer = document.getElementById('overlay_image_group_sorter_table');

    if (!tileContainer || !tableContainer) return;

    // Reorder tile view
    this.reorderView(tileContainer, newOrder, 'tile');
    
    // Reorder table view
    this.reorderView(tableContainer, newOrder, 'table');
  }

  /**
   * Reorder a specific view (tile or table) based on new image order.
   */
  private reorderView(container: HTMLElement, newOrder: number[], viewType: 'tile' | 'table'): void {
    if (viewType === 'tile') {
      // For tile view, reorder <li> elements in the <ul>
      const ul = container.querySelector('ul');
      if (!ul) return;

      const listItems = Array.from(ul.querySelectorAll('li'));
      const reorderedItems: HTMLElement[] = [];

      // Create a map of image ID to list item
      const itemMap = new Map<number, HTMLElement>();
      listItems.forEach(li => {
        const link = li.querySelector('a[href*="/img/"]');
        if (link) {
          const href = link.getAttribute('href') || '';
          const match = href.match(/\/img\/(\d+)/);
          if (match) {
            const imageId = parseInt(match[1], 10);
            itemMap.set(imageId, li as HTMLElement);
          }
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
    } else {
      // For table view, reorder <tr> elements in tbody
      const tbody = container.querySelector('table tbody');
      if (!tbody) return;

      const rows = Array.from(tbody.querySelectorAll('tr'));
      const reorderedRows: HTMLElement[] = [];

      // Create a map of image ID to table row
      const rowMap = new Map<number, HTMLElement>();
      rows.forEach(tr => {
        const link = tr.querySelector('a[href*="/img/"]');
        if (link) {
          const href = link.getAttribute('href') || '';
          const match = href.match(/\/img\/(\d+)/);
          if (match) {
            const imageId = parseInt(match[1], 10);
            rowMap.set(imageId, tr as HTMLElement);
          }
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
  private async handleSubmit(): Promise<any> {
    if (!this.overlay) return;

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
        const responseData: SetImageRankResponse = response.data;
        if (!responseData || !responseData.images) {
          throw new Error(`Invalid response from set_image_rank for image ${imageId}`);
        }

        // Update current ranks from response
        responseData.images.forEach(img => {
          this.currentRanks.set(img.id, img.image_rank);
        });

        // Show incremental success message
        if (this.overlay) {
          const currentMessages = (this.overlay as any)['state'].messages || [];
          this.overlay.setState({
            messages: [...currentMessages, { type: 'success' as const, text: `Image ${imageId} moved to rank ${desiredRank}` }]
          });
        }

      } catch (error: any) {
        // Extract error messages (same pattern as copy_images_app)
        if (this.overlay) {
          const currentMessages = (this.overlay as any)['state'].messages || [];
          const errorMsg = error instanceof Error ? error.message : String(error);
          
          // Check if it's an RPCError with multiple errors
          const detailedErrors = (error && typeof error === 'object' && 'errors' in error && Array.isArray((error as any).errors))
            ? (error as any).errors
            : [];
          
          // Add main error message
          const newMessages = [{ type: 'error' as const, text: `Failed to move image ${imageId} to rank ${desiredRank}: ${errorMsg}` }];
          
          // Add detailed errors if available
          if (detailedErrors.length > 0) {
            detailedErrors.forEach((err: { type?: string; content: string }) => {
              newMessages.push({
                type: 'error' as const,
                text: `${err.type || 'error'}: ${err.content}`
              });
            });
          }
          
          this.overlay.setState({
            messages: [...currentMessages, ...newMessages]
          });
          
          // Handle debug data if present
          if (error && typeof error === 'object' && 'debug' in error) {
            const errorDebug = (error as any).debug;
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
  private buildDesiredRanks(): void {
    this.desiredRanks.clear();

    // Get current order from tile view (more reliable for visual order)
    const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
    if (!tileContainer) return;

    // Find all list items in tile view
    const listItems = tileContainer.querySelectorAll('ul li');
    listItems.forEach((item, index) => {
      const link = item.querySelector('a[href*="/img/"]');
      if (link) {
        const imageId = this.extractImageIdFromElement(link as HTMLElement);
        if (imageId > 0) {
          this.desiredRanks.set(imageId, index + 1);
        }
      }
    });
  }

  /**
   * Extract image ID from a DOM element.
   */
  private extractImageIdFromElement(element: HTMLElement): number {
    // Try data-image-id attribute first
    const dataId = element.getAttribute('data-image-id');
    if (dataId) {
      return parseInt(dataId, 10);
    }

    // Try href attribute - format is /img/{id}
    const href = element.getAttribute('href') || '';
    const imgMatch = href.match(/\/img\/(\d+)/);
    if (imgMatch) {
      return parseInt(imgMatch[1], 10);
    }

    // Try parent element's href if this is an image or text element
    const parent = element.parentElement;
    if (parent) {
      const parentHref = parent.getAttribute('href') || '';
      const parentMatch = parentHref.match(/\/img\/(\d+)/);
      if (parentMatch) {
        return parseInt(parentMatch[1], 10);
      }
    }

    // Try finding a link ancestor
    const linkAncestor = element.closest('a[href*="/img/"]');
    if (linkAncestor) {
      const ancestorHref = linkAncestor.getAttribute('href') || '';
      const ancestorMatch = ancestorHref.match(/\/img\/(\d+)/);
      if (ancestorMatch) {
        return parseInt(ancestorMatch[1], 10);
      }
    }

    return 0;
  }

  /**
   * Perform final verification pass - check that all images are in desired positions.
   */
  private performFinalVerification(): void {
    const mismatches: string[] = [];

    // Compare desired vs current for each image
    this.desiredRanks.forEach((desiredRank, imageId) => {
      const currentRank = this.currentRanks.get(imageId);
      if (currentRank !== desiredRank) {
        mismatches.push(`Image ${imageId}: desired rank ${desiredRank}, but current rank is ${currentRank || 'unknown'}`);
      }
    });

    if (mismatches.length > 0 && this.overlay) {
      const currentMessages = (this.overlay as any)['state'].messages || [];
      const newMessages = mismatches.map(msg => ({ type: 'error' as const, text: msg }));
      this.overlay.setState({
        messages: [...currentMessages, ...newMessages]
      });
    }
  }
}


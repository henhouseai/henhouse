/**
 * ImageGroupSorter - Specialized browser for sorting/reordering images on a page.
 * Uses SortableJS for drag-and-drop functionality.
 */

import { OverlayManager } from './overlay/overlay-manager.js';
import { Overlay } from './overlay/overlay.js';
import { RPCClient } from './rpc-client.js';
import { handleRPCResponseWithDebug } from './debug-helper.js';
// Import SortableJS as a side-effect (it will be available as window.Sortable)
import './sortable.min.js';

// Get Sortable from global scope
declare global {
  interface Window {
    Sortable: any;
  }
}
const Sortable = (window as any).Sortable;

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
  private tileHtml: string = '';
  private originalRanks: Map<number, number> = new Map(); // imageId -> rank (original state)
  private currentRanks: Map<number, number> = new Map(); // imageId -> rank (current server state)
  private desiredRanks: Map<number, number> = new Map(); // imageId -> rank (what user wants)
  private sortableTile: any = null; // Sortable instance for tiles

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
   * Load tile view, then render overlay.
   */
  private async loadAndRender(): Promise<void> {
    try {
      // Fetch tile view
      const tileResult = await this.rpc.call('get_page_section', {
        id: this.pageId,
        section: 'images',
        view_type: 'tile',
        overlay: 1
      });

      const tileData = tileResult.data?.dom_content;

      if (!tileData) {
        throw new Error('Failed to load image group view');
      }

      this.tileHtml = tileData;

      // Extract initial image ranks from the HTML
      this.extractInitialRanks();

      // Initialize current ranks with original ranks
      this.currentRanks = new Map(this.originalRanks);

      // Render overlay
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
   * Render the overlay with tile view.
   */
  private renderOverlay(): void {
    const overlayManager = OverlayManager.getInstance();
    
    const content = [
      `
      <div class="content overlay" id="overlay_image_group_sorter_tiles">
        ${this.tileHtml}
      </div>
    `
    ];

    this.overlay = overlayManager.show({
      header: `Sort Images - Page ${this.pageId}`,
      content: content,
      contentHeaders: [''],
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
      this.prepareForSorting();
      this.removeAllLinks();
      this.setupSortable();
    }, 50);
  }

  /**
   * Prepare for sorting by extracting image IDs and setting data-id on <li> elements.
   * This must be done before removing links so we can extract IDs from href attributes.
   */
  private prepareForSorting(): void {
    const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');
    if (!tileContainer) return;

    const ul = tileContainer.querySelector('ul');
    if (!ul) return;

    const listItems = ul.querySelectorAll('li');
    listItems.forEach((li) => {
      // Try to find image ID from links before they're removed
      const link = li.querySelector('a[href*="/img/"]');
      if (link) {
        const href = link.getAttribute('href') || '';
        const match = href.match(/\/img\/(\d+)/);
        if (match) {
          const imageId = parseInt(match[1], 10);
          if (imageId > 0) {
            (li as HTMLElement).setAttribute('data-id', imageId.toString());
          }
        }
      } else {
        // Fallback: try data-image-id or data-image-rank attributes
        const dataImageId = li.querySelector('[data-image-id]');
        if (dataImageId) {
          const imageId = parseInt((dataImageId as HTMLElement).getAttribute('data-image-id') || '0', 10);
          if (imageId > 0) {
            (li as HTMLElement).setAttribute('data-id', imageId.toString());
          }
        }
      }
    });
  }

  /**
   * Remove all links from tile view to prevent navigation.
   * Extracts content from <a> tags and replaces them with non-link elements.
   */
  private removeAllLinks(): void {
    const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');

    if (tileContainer) {
      this.removeLinksFromContainer(tileContainer);
    }
  }

  /**
   * Remove all links from a container, replacing them with their content.
   */
  private removeLinksFromContainer(container: HTMLElement): void {
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
   * Set up SortableJS for tile view.
   * Note: data-id attributes should already be set by prepareForSorting().
   */
  private setupSortable(): void {
    const tileContainer = document.getElementById('overlay_image_group_sorter_tiles');

    // Set up Sortable for tile view (<ul> with <li> elements)
    if (tileContainer) {
      const ul = tileContainer.querySelector('ul');
      if (ul) {
        // Verify data-id attributes are set (they should be from prepareForSorting)
        const listItems = ul.querySelectorAll('li');
        listItems.forEach((li) => {
          if (!(li as HTMLElement).hasAttribute('data-id')) {
            // Fallback: try to extract from current DOM state
            const element = li.querySelector('span, a') || li;
            const imageId = this.extractImageIdFromElement(element as HTMLElement);
            if (imageId > 0) {
              (li as HTMLElement).setAttribute('data-id', imageId.toString());
            }
          }
        });

        this.sortableTile = Sortable.create(ul as HTMLElement, {
          animation: 150,
          dataIdAttr: 'data-id'
        });
      }
    }
  }


  /**
   * Handle submit - perform sequential set_image_rank calls.
   */
  private async handleSubmit(): Promise<any> {
    if (!this.overlay) return;

    // Capture debug options from the overlay (where user sets them)
    let capturedDebugOptions = this.overlay.getDebugOptions();
    // If no debug options in overlay, use empty object
    if (!capturedDebugOptions) {
      capturedDebugOptions = { debug: false, log: false };
    }

    // Build desired ranks map from current DOM state
    this.buildDesiredRanks();

    // Get image IDs in desired order (sorted by desired rank)
    const desiredOrder = Array.from(this.desiredRanks.entries())
      .sort((a, b) => a[1] - b[1])
      .map(([imageId]) => imageId);

    // Check if we found any images to process
    if (desiredOrder.length === 0) {
      const currentMessages = (this.overlay as any)['state'].messages || [];
      this.overlay.setState({
        messages: [...currentMessages, { type: 'error' as const, text: 'No images found to sort' }]
      });
      return { _autoFade: false }; // Don't auto-fade on error
    }

    // Track if any debug data was present
    let hasDebugData = false;

    // Failsafe: maximum iterations equals number of images
    const maxIterations = desiredOrder.length;
    let iterationCount = 0;

    // Optimized algorithm: always move the image with the largest distance first
    // This minimizes the number of operations needed
    while (true) {
      // Check failsafe: prevent infinite loops
      iterationCount++;
      if (iterationCount > maxIterations) {
        const currentMessages = (this.overlay as any)['state'].messages || [];
        this.overlay.setState({
          messages: [...currentMessages, { type: 'error' as const, text: `Sorting mechanism failed: exceeded maximum iterations (${maxIterations}). Could not find optimal sort.` }]
        });
        return { _autoFade: false }; // Prevent auto-fade on error
      }

      // Calculate distance each image needs to move
      let maxDistance = 0;
      let imageToMove: { imageId: number; desiredRank: number; distance: number } | null = null;

      for (const [imageId, desiredRank] of this.desiredRanks.entries()) {
        const currentRank = this.currentRanks.get(imageId);
        if (currentRank === undefined) continue;

        // Skip if already in correct position
        if (currentRank === desiredRank) continue;

        // Calculate distance (absolute difference)
        const distance = Math.abs(currentRank - desiredRank);
        
        // Track the image with the maximum distance
        if (distance > maxDistance) {
          maxDistance = distance;
          imageToMove = { imageId, desiredRank, distance };
        }
      }

      // If no image needs to move, we're done
      if (!imageToMove || maxDistance === 0) {
        break;
      }

      try {
        // Call set_image_rank with captured debug options
        const response = await this.rpc.call('set_image_rank', {
          page_id: this.pageId,
          image_id: imageToMove.imageId,
          target_rank: imageToMove.desiredRank
        }, capturedDebugOptions);

        // Handle debug data if present
        if (response && response.debug && Array.isArray(response.debug.entries) && response.debug.entries.length > 0) {
          hasDebugData = true;
          handleRPCResponseWithDebug(response, 'set_image_rank', {
            page_id: this.pageId,
            image_id: imageToMove.imageId,
            target_rank: imageToMove.desiredRank
          });
        }

        // Extract response data
        const responseData: SetImageRankResponse = response.data;
        if (!responseData || !responseData.images) {
          throw new Error(`Invalid response from set_image_rank for image ${imageToMove.imageId}`);
        }

        // Update current ranks from response
        responseData.images.forEach(img => {
          this.currentRanks.set(img.id, img.image_rank);
        });

        // Add success message for this image
        const currentMessages = (this.overlay as any)['state'].messages || [];
        this.overlay.setState({
          messages: [...currentMessages, { type: 'success' as const, text: `Successfully moved image ${imageToMove.imageId} to rank ${imageToMove.desiredRank}` }]
        });

      } catch (error) {
        // Add error message for this image
        const currentMessages = (this.overlay as any)['state'].messages || [];
        const errorMsg = error instanceof Error ? error.message : String(error);
        
        // Check if it's an RPCError with multiple errors
        const detailedErrors = (error && typeof error === 'object' && 'errors' in error && Array.isArray((error as any).errors))
          ? (error as any).errors
          : [];
        
        // Add main error message
        const newMessages = [{ type: 'error' as const, text: `Failed to move image ${imageToMove.imageId} to rank ${imageToMove.desiredRank}: ${errorMsg}` }];
        
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
            hasDebugData = true;
            handleRPCResponseWithDebug(error, 'set_image_rank', {
              page_id: this.pageId,
              image_id: imageToMove.imageId,
              target_rank: imageToMove.desiredRank
            });
          }
        }

        // Stop on first error
        return { _autoFade: false }; // Prevent auto-fade on error
      }
    }

    // Return success with redirect flag (reload page after fade, unless debug data present)
    return {
      _showMessage: `Completed sorting ${desiredOrder.length} image(s)`,
      _autoFade: !hasDebugData,
      _redirectAfterFade: hasDebugData ? null : 'self'
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
      // First try data-id on the <li> itself (set by setupSortable)
      const liDataId = (item as HTMLElement).getAttribute('data-id');
      if (liDataId) {
        const imageId = parseInt(liDataId, 10);
        if (imageId > 0) {
          this.desiredRanks.set(imageId, index + 1);
          return; // Found it, move to next item
        }
      }

      // Fallback: Look for span or any element (links are removed)
      const element = item.querySelector('span, a') || item;
      const imageId = this.extractImageIdFromElement(element as HTMLElement);
      if (imageId > 0) {
        this.desiredRanks.set(imageId, index + 1);
      }
    });
  }

  /**
   * Extract image ID from a DOM element.
   * Works with both links and spans (after links are removed).
   * Prioritizes data-id (set by SortableJS setup) and data-image-id attributes.
   */
  private extractImageIdFromElement(element: HTMLElement): number {
    // Try data-id attribute first (set by setupSortable on <li> elements)
    const dataId = element.getAttribute('data-id');
    if (dataId) {
      const id = parseInt(dataId, 10);
      if (id > 0) return id;
    }

    // Try data-image-id attribute
    const dataImageId = element.getAttribute('data-image-id');
    if (dataImageId) {
      const id = parseInt(dataImageId, 10);
      if (id > 0) return id;
    }

    // Try data-image-rank attribute (contains image ID in some cases)
    const dataImageRank = element.getAttribute('data-image-rank');
    if (dataImageRank) {
      // This might contain rank, not ID, but check parent for ID
      const parent = element.parentElement;
      if (parent) {
        const parentDataId = parent.getAttribute('data-id');
        if (parentDataId) {
          const id = parseInt(parentDataId, 10);
          if (id > 0) return id;
        }
      }
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

    // Try finding in parent or ancestor elements (check for data-id on parent <li>)
    let current: HTMLElement | null = element;
    while (current && current !== document.body) {
      // Check parent for data-id (set on <li> by setupSortable)
      const currentDataId = current.getAttribute('data-id');
      if (currentDataId) {
        const id = parseInt(currentDataId, 10);
        if (id > 0) return id;
      }

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
   * Note: With the optimized algorithm, this should rarely find mismatches since
   * we continue until no more moves are needed. But we keep it as a safety check.
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

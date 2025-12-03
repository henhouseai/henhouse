/**
 * Browser - Hierarchical page/image/file selection overlay.
 * Allows users to navigate pages and select a single page or multiple images/files.
 */

import { OverlayManager, OverlayOptions } from './overlay/overlay-manager.js';
import { Overlay } from './overlay/overlay.js';
import { RPCClient } from './rpc-client.js';
import { getSeedData } from './seed.js';
import { getViewToggleInstance, ViewToggleCallbacks } from './view-toggle.js';

export type BrowserMode = 'page' | 'image' | 'file';

export interface BrowserOptions {
  mode: BrowserMode;
  initialPageId?: number;
  onSubmit: (result: number | number[]) => void | Promise<void>;
  onCancel?: () => void;
}

interface SelectedImage {
  imageId: number;
  tileHtml: string; // Cloned tile HTML
  bufferIndex: number; // Index in buffer (for unique IDs)
}

export class Browser {
  private rpc: RPCClient;
  private overlay: Overlay | null = null;
  private currentPageId: number;
  private selectedImages: SelectedImage[] = []; // Store image data with cloned HTML
  private selectedFileIds: number[] = [];
  private mode: BrowserMode;
  private onSubmit: (result: number | number[]) => void | Promise<void>;
  private onCancel?: () => void;
  private viewToggle: any = null; // ViewToggle instance for this browser

  constructor(options: BrowserOptions) {
    this.rpc = new RPCClient();
    this.mode = options.mode;
    this.onSubmit = options.onSubmit;
    this.onCancel = options.onCancel;
    
    // Determine initial page ID
    if (options.initialPageId) {
      this.currentPageId = options.initialPageId;
    } else {
      const seedData = getSeedData();
      const seedPageId = seedData.page?.id;
      this.currentPageId = (typeof seedPageId === 'number' ? seedPageId : 1);
    }
  }

  /**
   * Show the browser overlay.
   */
  async show(): Promise<void> {
    await this.loadAndRender();
  }

  /**
   * Load browser content and render overlay.
   */
  private async loadAndRender(): Promise<void> {
    try {
      // Call get_browser MCP tool
      const result = await this.rpc.call('get_browser', { id: this.currentPageId });
      const browserData = result.data;

      if (!browserData) {
        throw new Error('get_browser did not return data');
      }

      const sections = browserData.sections || {};
      
      // Build content HTML
      const contentParts: string[] = [];
      
      // Add image buffer if in image mode
      if (this.mode === 'image' && this.selectedImages.length > 0) {
        contentParts.push(this.renderImageBuffer());
      }
      
      // Add file buffer if in file mode
      if (this.mode === 'file' && this.selectedFileIds.length > 0) {
        contentParts.push(this.renderFileBuffer());
      }

      // Add page sections (hide image groups in page mode)
      if (sections.path) contentParts.push(sections.path);
      if (sections.badges) contentParts.push(sections.badges);
      if (sections.text) contentParts.push(sections.text);
      if (sections.children) contentParts.push(sections.children);
      
      // Only show images section if not in page mode
      if (this.mode !== 'page' && sections.images) {
        contentParts.push(sections.images);
      }

      // Check if overlay already exists - if so, update it instead of creating new one
      if (this.overlay) {
        // Update existing overlay content
        this.updateOverlayContent(contentParts);
      } else {
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
      // Set up buffer click handlers if in image mode
      if (this.mode === 'image') {
        const windowEl = document.getElementById('overlayWindow');
        if (windowEl) {
          this.setupBufferClickHandlers(windowEl);
        }
      }
    }, 50);

    } catch (error) {
      console.error('Error loading browser:', error);
      this.rpc.showError('browser', error);
    }
  }

  /**
   * Update existing overlay content without creating a new overlay.
   */
  private updateOverlayContent(contentParts: string[]): void {
    if (!this.overlay) return;

    const windowEl = document.getElementById('overlayWindow');
    if (!windowEl) {
      // Overlay was closed, create a new one
      this.overlay = null;
      this.loadAndRender();
      return;
    }

    // Find and clear the contentWrapper.overlay div (but keep the wrapper itself)
    let contentWrapper = windowEl.querySelector('.contentWrapper.overlay') as HTMLElement;
    
    // If contentWrapper doesn't exist, create it (shouldn't happen, but safety check)
    if (!contentWrapper) {
      const headerEl = windowEl.querySelector('.contentWrapperHeader.overlay') as HTMLElement;
      contentWrapper = document.createElement('div');
      contentWrapper.className = 'contentWrapper overlay';
      if (headerEl) {
        headerEl.insertAdjacentElement('afterend', contentWrapper);
      } else {
        windowEl.appendChild(contentWrapper);
      }
    } else {
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
      contentWrapper.appendChild(element as HTMLElement);
    });

    // Update submit button label
    const submitBtn = windowEl.querySelector('#submitOverlayWindow') as HTMLElement;
    if (submitBtn) {
      submitBtn.textContent = this.getSubmitLabel();
    }

    // Re-intercept links after content update
    this.interceptLinks(windowEl);
    
    // Set up buffer tile click handlers
    if (this.mode === 'image') {
      this.setupBufferClickHandlers(windowEl);
    }
  }

  /**
   * Inject HTML content and set up link interception.
   */
  private injectAndIntercept(): void {
    if (!this.overlay) return;

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
  private setupViewToggle(): void {
    if (!this.overlay) return;

    const windowEl = document.getElementById('overlayWindow');
    if (!windowEl) return;

    // Get the global view toggle instance
    // Since view-toggle uses event delegation, we register callbacks with the global instance
    const globalViewToggle = getViewToggleInstance();
    
    if (globalViewToggle) {
      // Register callbacks that only run when swap is in this browser's overlay
      const callbacks: ViewToggleCallbacks = {
        onAfterSwap: (container: HTMLElement, context: any) => {
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
  private interceptLinks(container: HTMLElement): void {
    // Find all links
    const links = container.querySelectorAll<HTMLAnchorElement>('a[href]');
    
    links.forEach(link => {
      // Skip toggle links - let view-toggle.ts handle them
      if (link.classList.toString().includes('updatePageView_')) {
        return;
      }

      // Skip links that already have our click handler (avoid duplicate listeners)
      if ((link as any).__browserIntercepted) {
        return;
      }

      const href = link.getAttribute('href');
      if (!href) return;

      // Check if it's a page link (starts with / and is numeric)
      const pageMatch = href.match(/^\/(\d+)$/);
      if (pageMatch) {
        const pageId = parseInt(pageMatch[1], 10);
        link.addEventListener('click', (e) => {
          e.preventDefault();
          this.retargetBrowser(pageId);
        });
        (link as any).__browserIntercepted = true;
        return;
      }

      // Check if it's an image link (starts with /img/)
      const imageMatch = href.match(/^\/img\/(\d+)$/);
      if (imageMatch && (this.mode === 'image' || this.mode === 'file')) {
        const imageId = parseInt(imageMatch[1], 10);
        link.addEventListener('click', (e) => {
          e.preventDefault();
          // Find the tile element (parent <a> contains the tile)
          const tileLink = link.closest('a.tileLink');
          if (tileLink) {
            this.handleImageClick(imageId, tileLink as HTMLElement);
          }
        });
        (link as any).__browserIntercepted = true;
        return;
      }
      
      // Check if it's a buffer tile click (starts with selected_image_)
      if (link.id && link.id.startsWith('selected_image_') && this.mode === 'image') {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const bufferIndex = parseInt(link.id.replace('selected_image_', ''), 10);
          this.handleBufferImageClick(bufferIndex);
        });
        (link as any).__browserIntercepted = true;
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
        (link as any).__browserIntercepted = true;
        return;
      }
    });
  }

  /**
   * Retarget browser to a new page.
   */
  private async retargetBrowser(pageId: number): Promise<void> {
    this.currentPageId = pageId;
    await this.loadAndRender();
  }

  /**
   * Handle image click (always add to buffer - allows duplicates).
   */
  private handleImageClick(imageId: number, tileElement: HTMLElement): void {
    if (this.mode !== 'image') return;

    // Clone the tile DOM structure
    const clonedTile = tileElement.cloneNode(true) as HTMLElement;
    const bufferIndex = this.selectedImages.length;
    
    // Update the link ID to be unique for buffer
    const linkElement = clonedTile.querySelector('a.tileLink');
    if (linkElement) {
      linkElement.id = `selected_image_${bufferIndex}`;
      // Remove href to prevent navigation
      linkElement.removeAttribute('href');
    }

    // Store the cloned HTML
    const tileHtml = clonedTile.outerHTML;
    
    // Add to buffer (always add, never remove - allows duplicates)
    this.selectedImages.push({
      imageId,
      tileHtml,
      bufferIndex
    });

    // Re-render to update buffer
    this.loadAndRender();
  }

  /**
   * Handle buffer tile click (remove from buffer).
   */
  private handleBufferImageClick(bufferIndex: number): void {
    if (this.mode !== 'image') return;

    // Find and remove the image at this buffer index
    const index = this.selectedImages.findIndex(img => img.bufferIndex === bufferIndex);
    if (index !== -1) {
      this.selectedImages.splice(index, 1);
      
      // Re-index remaining items
      this.selectedImages.forEach((img, idx) => {
        img.bufferIndex = idx;
      });
      
      // Re-render to update buffer
      this.loadAndRender();
    }
  }

  /**
   * Handle submit - call callback with result.
   */
  private async handleSubmit(): Promise<any> {
    let result: number | number[];
    let message: string;
    
    if (this.mode === 'page') {
      result = this.currentPageId;
      message = `Page ${result} selected successfully`;
    } else if (this.mode === 'image') {
      if (this.selectedImages.length === 0) {
        throw new Error('Please select at least one image');
      }
      result = this.selectedImages.map(img => img.imageId);
      message = `${result.length} image${result.length !== 1 ? 's' : ''} selected: ${result.join(', ')}`;
    } else {
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
    } catch (error) {
      throw error;
    }
  }

  /**
   * Render image buffer (tiles + table).
   */
  private renderImageBuffer(): string {
    if (this.selectedImages.length === 0) {
      return '';
    }

    // Build tiles HTML - wrap each tile in <li>
    const tilesHtml = this.selectedImages.map(img => {
      // Create a temporary container to parse and update the cloned HTML
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = img.tileHtml;
      
      // Find and update the link element
      const linkEl = tempDiv.querySelector('a.tileLink');
      if (linkEl) {
        linkEl.id = `selected_image_${img.bufferIndex}`;
        linkEl.removeAttribute('href');
      }
      
      // Get the updated HTML
      const updatedHtml = tempDiv.innerHTML;
      return `    <li>${updatedHtml}</li>`;
    }).join('\n');

    // Build table rows HTML (simple table with ID and caption)
    const tableRowsHtml = this.selectedImages.map((img, idx) => {
      // Extract caption from tile HTML
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = img.tileHtml;
      const captionEl = tempDiv.querySelector('.tileText');
      const caption = captionEl ? (captionEl.textContent || '').trim() : '';
      
      return `      <tr>
        <td>${idx + 1}</td>
        <td><a id="selected_image_${img.bufferIndex}" class="bufferTableLink">${img.imageId}</a></td>
        <td>${caption}</td>
      </tr>`;
    }).join('\n');

    return `<div id="browserImageBuffer" class="content browserImageBuffer overlay">
  <div id="browserImageBufferHeader" class="contentHeader overlay">
    <h3>Selected Images (${this.selectedImages.length})</h3>
  </div>
  <div id="browserImageBufferTiles" class="content pageImageGroup overlay">
    <ul class="tileList">
${tilesHtml}
    </ul>
  </div>
  <div id="browserImageBufferTable" class="content overlay">
    <table class="dataTable">
      <thead>
        <tr>
          <th>#</th>
          <th>ID</th>
          <th>Caption</th>
        </tr>
      </thead>
      <tbody>
${tableRowsHtml}
      </tbody>
    </table>
  </div>
</div>`;
  }

  /**
   * Render file buffer (tiles + table).
   */
  private renderFileBuffer(): string {
    if (this.selectedFileIds.length === 0) {
      return '';
    }

    // TODO: Implement file buffer rendering
    return '';
  }

  /**
   * Get browser title based on mode.
   */
  private getBrowserTitle(): string {
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
   * Set up click handlers for buffer tiles and table rows.
   */
  private setupBufferClickHandlers(container: HTMLElement): void {
    // Handle buffer tile clicks
    const bufferTiles = container.querySelectorAll('#browserImageBuffer a.tileLink[id^="selected_image_"]');
    bufferTiles.forEach(tile => {
      if ((tile as any).__bufferIntercepted) return;
      const bufferIndex = parseInt(tile.id.replace('selected_image_', ''), 10);
      tile.addEventListener('click', (e) => {
        e.preventDefault();
        this.handleBufferImageClick(bufferIndex);
      });
      (tile as any).__bufferIntercepted = true;
    });

    // Handle buffer table row clicks
    const bufferTableLinks = container.querySelectorAll('#browserImageBufferTable a.bufferTableLink[id^="selected_image_"]');
    bufferTableLinks.forEach(link => {
      if ((link as any).__bufferIntercepted) return;
      const bufferIndex = parseInt(link.id.replace('selected_image_', ''), 10);
      link.addEventListener('click', (e) => {
        e.preventDefault();
        this.handleBufferImageClick(bufferIndex);
      });
      (link as any).__bufferIntercepted = true;
    });
  }

  /**
   * Get submit button label based on mode and selection.
   */
  private getSubmitLabel(): string {
    if (this.mode === 'page') {
      return 'Select Page';
    } else if (this.mode === 'image') {
      const count = this.selectedImages.length;
      return count > 0 ? `Submit ${count} Image${count !== 1 ? 's' : ''}` : 'Submit';
    } else {
      const count = this.selectedFileIds.length;
      return count > 0 ? `Submit ${count} File${count !== 1 ? 's' : ''}` : 'Submit';
    }
  }
}


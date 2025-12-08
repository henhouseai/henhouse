/**
 * Browser - Hierarchical page/image/file selection overlay.
 * Allows users to navigate pages and select a single page or multiple images/files.
 */

import { OverlayManager, OverlayOptions } from './overlay/overlay-manager.js';
import { Overlay } from './overlay/overlay.js';
import { RPCClient } from './rpc-client.js';
import { getSeedData } from './seed.js';
import { getViewToggleInstance, ViewToggleCallbacks } from './view-toggle.js';
import { interceptLinks as interceptLinksHelper } from './overlay/overlay-link-helpers.js';

export type BrowserMode = 'page' | 'image' | 'file';

export interface ImageSelectionResult {
  imageIds: number[];
  imageInstances: Array<{
    image_id: number;
    source_page_id: number;
    source_rank: number;
  }>;
}

export interface FileSelectionResult {
  fileIds: number[];
  fileInstances: Array<{
    file_id: number;
    source_page_id: number;
    source_rank: number;
  }>;
}

export interface BrowserOptions {
  mode: BrowserMode;
  initialPageId?: number;
  onSubmit: (result: number | number[] | ImageSelectionResult | FileSelectionResult) => void | Promise<void> | Promise<any> | any;
  onCancel?: () => void;
  overlayMode?: 'fixed' | 'pannable' | 'zoomable';
}

interface SelectedImage {
  imageId: number;
  sourcePageId: number; // Page ID where image was selected from
  sourceRank: number; // Rank in the source page's image group
  tileHtml: string; // Cloned tile HTML
  bufferIndex: number; // Index in buffer (for unique IDs)
}

export class Browser {
  private rpc: RPCClient;
  private overlay: Overlay | null = null;
  private currentPageId: number;
  private selectedImages: SelectedImage[] = []; // Store image data with cloned HTML
  private selectedFiles: Array<{ fileId: number; sourcePageId: number; sourceRank: number }> = [];
  private mode: BrowserMode;
  private onSubmit: (result: number | number[] | ImageSelectionResult | FileSelectionResult) => void | Promise<void> | Promise<any> | any;
  private onCancel?: () => void;
  private viewToggle: any = null; // ViewToggle instance for this browser
  private overlayMode: 'fixed' | 'pannable' | 'zoomable';

  constructor(options: BrowserOptions) {
    this.rpc = new RPCClient();
    this.mode = options.mode;
    this.onSubmit = options.onSubmit;
    this.onCancel = options.onCancel;
    this.overlayMode = options.overlayMode || 'fixed';
    
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
      if (this.mode === 'file' && this.selectedFiles.length > 0) {
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
          mode: this.overlayMode,
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

    const windowEl = this.getBrowserWindowElement();
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

    // Re-intercept links after content update (includes buffer tiles via custom matcher)
    this.interceptLinks(windowEl);
  }

  /**
   * Inject HTML content and set up link interception.
   */
  private injectAndIntercept(): void {
    if (!this.overlay) return;

    // Get the window element from this specific overlay instance
    // Use querySelector on the overlay's container to find its window
    const windowEl = this.getBrowserWindowElement();
    if (!windowEl) {
      // Retry after a short delay if overlay not ready yet
      setTimeout(() => this.injectAndIntercept(), 100);
      return;
    }

    // Intercept all links
    this.interceptLinks(windowEl);
  }

  /**
   * Get the browser's overlay window element.
   * Uses the overlay's container to find the correct window (handles Z-stack).
   */
  private getBrowserWindowElement(): HTMLElement | null {
    if (!this.overlay) return null;
    
    // Access the overlay's internal windowEl property
    // The overlay stores its windowEl in a private property
    const windowEl = (this.overlay as any).windowEl;
    if (windowEl) return windowEl;
    
    // Fallback: find via container if windowEl not available yet
    const overlayContainer = (this.overlay as any).container;
    if (overlayContainer) {
      return overlayContainer.querySelector('#overlayWindow') as HTMLElement;
    }
    
    return null;
  }

  /**
   * Set up view toggle with callbacks to re-intercept links after content swaps.
   */
  private setupViewToggle(): void {
    if (!this.overlay) return;

    const windowEl = this.getBrowserWindowElement();
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
    interceptLinksHelper(container, {
      // Page links: retarget browser to new page
      onPageLink: (pageId: number, link: HTMLAnchorElement) => {
        this.retargetBrowser(pageId);
      },

      // Image links: handle image selection (only in image/file mode)
      onImageLink: (imageId: number, link: HTMLAnchorElement) => {
        if (this.mode === 'image' || this.mode === 'file') {
          // Find the tile element (parent <a> contains the tile)
          const tileLink = link.closest('a.tileLink');
          if (tileLink) {
            // Extract data attributes for source page and rank
            const sourcePageId = parseInt(tileLink.getAttribute('data-page-id') || '0', 10);
            const sourceRank = parseInt(tileLink.getAttribute('data-image-rank') || '0', 10);
            this.handleImageClick(imageId, sourcePageId, sourceRank, tileLink as HTMLElement);
          }
        }
      },

      // File links: handle file selection (only in file mode)
      onFileLink: (fileId: number, link: HTMLAnchorElement) => {
        if (this.mode === 'file') {
          const row = link.closest('tr');
          let sourceRank = 0;
          if (row) {
            const rankCell = row.querySelector('td');
            if (rankCell) {
              const parsedRank = parseInt((rankCell.textContent || '').trim(), 10);
              if (!Number.isNaN(parsedRank)) {
                sourceRank = parsedRank;
              }
            }
          }
          this.handleFileClick(fileId, this.currentPageId, sourceRank);
        }
      },

      // Custom matcher for buffer tile clicks (ID-based, not href-based)
      customMatcher: (href: string, link: HTMLAnchorElement) => {
        // Buffer tiles have IDs starting with "selected_image_" or "selected_file_" and no href
        if (link.id && this.mode === 'image' && link.id.startsWith('selected_image_')) {
          return true;
        }
        if (link.id && this.mode === 'file' && link.id.startsWith('selected_file_')) {
          return true;
        }
        return false;
      },

      // Custom handler for buffer tile clicks
      customHandler: (href: string, link: HTMLAnchorElement) => {
        if (link.id && link.id.startsWith('selected_image_')) {
          const bufferIndex = parseInt(link.id.replace('selected_image_', ''), 10);
          this.handleBufferImageClick(bufferIndex);
        }
        if (link.id && link.id.startsWith('selected_file_')) {
          const bufferIndex = parseInt(link.id.replace('selected_file_', ''), 10);
          this.handleBufferFileClick(bufferIndex);
        }
      },

      // Use browser-specific marker to avoid conflicts
      markerProperty: '__browserIntercepted'
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
  private handleImageClick(imageId: number, sourcePageId: number, sourceRank: number, tileElement: HTMLElement): void {
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
      sourcePageId,
      sourceRank,
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
    let result: number | number[] | ImageSelectionResult | FileSelectionResult;
    let message: string;
    
    if (this.mode === 'page') {
      result = this.currentPageId;
      message = `Page ${result} selected successfully`;
    } else if (this.mode === 'image') {
      if (this.selectedImages.length === 0) {
        throw new Error('Please select at least one image');
      }
      // For image mode, return full selection data including source page and rank
      const imageResult: ImageSelectionResult = {
        imageIds: this.selectedImages.map(img => img.imageId),
        imageInstances: this.selectedImages.map(img => ({
          image_id: img.imageId,
          source_page_id: img.sourcePageId,
          source_rank: img.sourceRank
        }))
      };
      result = imageResult;
      message = `${this.selectedImages.length} image${this.selectedImages.length !== 1 ? 's' : ''} selected: ${imageResult.imageIds.join(', ')}`;
    } else {
      if (this.selectedFiles.length === 0) {
        throw new Error('Please select at least one file');
      }
      const fileIds = this.selectedFiles.map(f => f.fileId);
      result = {
        fileIds,
        fileInstances: this.selectedFiles.map(f => ({
          file_id: f.fileId,
          source_page_id: f.sourcePageId,
          source_rank: f.sourceRank
        }))
      };
      message = `${fileIds.length} file${fileIds.length !== 1 ? 's' : ''} selected: ${fileIds.join(', ')}`;
    }

    try {
      const submitResult = await this.onSubmit(result);
      
      // If onSubmit returns a result object (with _showMessage, etc.), use it
      // Otherwise, use default success message
      if (submitResult && typeof submitResult === 'object' && ('_showMessage' in submitResult || '_autoFade' in submitResult || '_redirectAfterFade' in submitResult)) {
        return submitResult;
      }
      
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
    if (this.selectedFiles.length === 0) {
      return '';
    }

    const tableRowsHtml = this.selectedFiles.map((file, idx) => {
      return `      <tr>
        <td>${idx + 1}</td>
        <td><a id="selected_file_${idx}" class="bufferTableLink">${file.fileId}</a></td>
        <td>${file.sourcePageId}</td>
        <td>${file.sourceRank || ''}</td>
      </tr>`;
    }).join('\n');

    return `<div id="browserFileBuffer" class="content browserFileBuffer overlay">
  <div id="browserFileBufferHeader" class="contentHeader overlay">
    <h3>Selected Files (${this.selectedFiles.length})</h3>
  </div>
  <div id="browserFileBufferTable" class="content overlay">
    <table class="dataTable">
      <thead>
        <tr>
          <th>#</th>
          <th>ID</th>
          <th>Source Page</th>
          <th>Rank</th>
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
   * Get submit button label based on mode and selection.
   */
  private getSubmitLabel(): string {
    if (this.mode === 'page') {
      return 'Select Page';
    } else if (this.mode === 'image') {
      const count = this.selectedImages.length;
      return count > 0 ? `Submit ${count} Image${count !== 1 ? 's' : ''}` : 'Submit';
    } else {
      const count = this.selectedFiles.length;
      return count > 0 ? `Submit ${count} File${count !== 1 ? 's' : ''}` : 'Submit';
    }
  }

  /**
   * Handle file click (adds to buffer, allows duplicates).
   */
  private handleFileClick(fileId: number, sourcePageId: number, sourceRank: number): void {
    if (this.mode !== 'file') return;
    this.selectedFiles.push({
      fileId,
      sourcePageId,
      sourceRank
    });
    this.loadAndRender();
  }

  /**
   * Handle buffer file click (remove from buffer).
   */
  private handleBufferFileClick(bufferIndex: number): void {
    if (this.mode !== 'file') return;
    if (bufferIndex < 0 || bufferIndex >= this.selectedFiles.length) return;
    this.selectedFiles.splice(bufferIndex, 1);
    this.loadAndRender();
  }
}


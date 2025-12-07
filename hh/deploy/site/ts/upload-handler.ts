/**
 * Upload handler for image uploads
 */

import { RPCClient } from './rpc-client.js';
import { SeedData } from './seed.js';
import { OverlayManager } from './overlay/overlay-manager.js';
import { DebugOptions } from './overlay/overlay-debug-options.js';
import { handleRPCResponseWithDebug } from './debug-helper.js';

interface FileUploadStatus {
  fileId: string; // Unique ID based on file path
  file: File;
  uploaded: boolean;
  uploadResult: { temp_path: string; original_name: string } | null;
  processing: boolean;
  processed: boolean;
  error: string | null;
  div: HTMLElement;
  debugOptions: DebugOptions | null; // Debug options captured when submit was clicked
}

export class UploadHandler {
  private rpc: RPCClient;
  private seedData: SeedData;
  private fileInput: HTMLInputElement;
  private uploadStatuses: FileUploadStatus[] = [];
  private chooseFilesBtn: HTMLAnchorElement | null = null;
  private uploadBtn: HTMLAnchorElement | null = null;
  private overlay: any = null;
  private placeholderDiv: HTMLElement | null = null;
  private overlayWindow: HTMLElement | null = null;

  constructor(rpc: RPCClient, seedData: SeedData) {
    this.rpc = rpc;
    this.seedData = seedData;
    this.fileInput = document.createElement('input');
    this.fileInput.type = 'file';
    this.fileInput.multiple = true;
    this.fileInput.accept = 'image/*';
    this.fileInput.style.display = 'none';
  }

  /**
   * Convert file path to a safe ID format (snake_case with underscores)
   */
  private filePathToId(filePath: string): string {
    // Replace slashes, backslashes, and other problematic characters with underscores
    return filePath
      .replace(/[\/\\]/g, '_')
      .replace(/[^a-zA-Z0-9_\-\.]/g, '_')
      .replace(/_{2,}/g, '_') // Replace multiple underscores with single
      .replace(/^_+|_+$/g, ''); // Remove leading/trailing underscores
  }

  /**
   * Handle Upload: Upload images to current page
   */
  async handle(): Promise<void> {
    const overlayManager = OverlayManager.getInstance();
    
    // Get current page ID (backend will auto-convert string to int if needed)
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      this.rpc.showError('Upload', new Error('No page ID available'));
      return;
    }

    // Create placeholder content (just the inner wrapper, overlay system will wrap it)
    const placeholderText = document.createTextNode('No files selected. Click "Choose Files" to add images.');
    const placeholderWrapper = document.createElement('div');
    placeholderWrapper.className = 'upload-placeholder';
    placeholderWrapper.appendChild(placeholderText);
    
    // Handle file selection
    this.fileInput.addEventListener('change', (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (!files || files.length === 0) return;
      
      // Get overlay window if not already stored
      if (!this.overlayWindow && this.overlay && typeof this.overlay.getWindowElement === 'function') {
        this.overlayWindow = this.overlay.getWindowElement();
      }
      if (!this.overlayWindow) {
        this.overlayWindow = document.querySelector('.overlay-window') as HTMLElement;
      }
      
      if (!this.overlayWindow) {
        console.error('Overlay window not found');
        return;
      }
      
      // Find and remove the placeholder div by its specific class
      const placeholderContentDiv = this.overlayWindow.querySelector('.content.overlay:has(.upload-placeholder)') ||
                                     this.overlayWindow.querySelector('.content.overlay.upload-placeholder');
      if (placeholderContentDiv && placeholderContentDiv.parentNode) {
        placeholderContentDiv.remove();
        this.placeholderDiv = null;
      }
      
      // Add all selected files directly to overlayWindow (skip duplicates)
      for (let i = 0; i < files.length; i++) {
        const fileId = this.filePathToId(files[i].name);
        // Check if file already exists
        if (this.uploadStatuses.find(s => s.fileId === fileId)) {
          // File already added, skip silently
          continue;
        }
        this.addFile(files[i]);
      }
      
      // Reset input so same file can be selected again
      this.fileInput.value = '';
    });
    
    // Show overlay with custom header buttons
    this.overlay = overlayManager.show({
      header: 'Upload Images',
      content: [placeholderWrapper],
      contentHeaders: [''],
      closable: true, // Allow closing by clicking backdrop
      submitLabel: 'Upload',
      cancelLabel: 'Cancel',
      middleButtonLabel: 'Choose Files',
      onMiddleButton: () => {
        this.fileInput.click();
      },
      onMount: () => {
        // Add upload-placeholder class immediately when overlay mounts (before it's visible)
        // This prevents flicker by ensuring correct styling from the start
        const win = this.overlay?.getWindowElement() || document.querySelector('.overlay-window');
        const placeholderContentDiv = win?.querySelector('.content.overlay .upload-placeholder') as HTMLElement;
        if (placeholderContentDiv) {
          placeholderContentDiv.classList.add('upload-placeholder');
          this.placeholderDiv = placeholderContentDiv;
        }
      },
      onSubmit: async () => {
        if (this.uploadStatuses.length === 0) {
          return { _showMessage: 'Please select at least one file', _autoFade: false };
        }
        
        // Capture debug options from overlay before starting upload
        const overlayManager = OverlayManager.getInstance();
        const topOverlay = overlayManager.getTopOverlay();
        let capturedDebugOptions: DebugOptions | null = null;
        if (topOverlay) {
          capturedDebugOptions = topOverlay.getDebugOptions();
        }
        
        // Store debug options in each file status
        for (const status of this.uploadStatuses) {
          status.debugOptions = capturedDebugOptions;
        }
        
        // Disable choose files and upload buttons
        if (this.chooseFilesBtn) {
          this.chooseFilesBtn.style.pointerEvents = 'none';
          this.chooseFilesBtn.style.opacity = '0.5';
        }
        if (this.uploadBtn) {
          this.uploadBtn.style.pointerEvents = 'none';
          this.uploadBtn.style.opacity = '0.5';
        }
        
        // Upload all files in parallel
        const uploadPromises = this.uploadStatuses.map((status) => this.uploadFile(status, pageId));
        await Promise.allSettled(uploadPromises);
        
        // Process files sequentially in order
        let nextIndexToProcess = 0;
        let hasDebugData = false; // Track if any debug data was present
        
        const processNext = async (): Promise<void> => {
          while (nextIndexToProcess < this.uploadStatuses.length) {
            const status = this.uploadStatuses[nextIndexToProcess];
            
            if (status.error) {
              nextIndexToProcess++;
              continue;
            }
            
            if (status.uploaded && status.uploadResult && !status.processed && !status.processing) {
              status.processing = true;
              
              try {
                // Build params with debug options from this file's stored metadata
                const params: any = {
                  page_id: pageId,
                  file0_path: status.uploadResult.temp_path,
                  file0_name: status.uploadResult.original_name
                };
                
                // Add debug options if they were captured for this file
                if (status.debugOptions) {
                  if (status.debugOptions.debug) {
                    params.debug = 1;
                  }
                  if (status.debugOptions.log) {
                    params.log = 1;
                  }
                  if (status.debugOptions.white) {
                    params.white = status.debugOptions.white;
                  }
                  if (status.debugOptions.gray) {
                    params.gray = status.debugOptions.gray;
                  }
                  if (status.debugOptions.black) {
                    params.black = status.debugOptions.black;
                  }
                  if (status.debugOptions.debugLimit) {
                    params['debug-limit'] = status.debugOptions.debugLimit;
                  }
                }
                
                const rpcResult = await this.rpc.call('upload_images', params);
                
                // Track if debug data was present (prevents auto-fade)
                if (rpcResult.debug && Array.isArray(rpcResult.debug.entries) && rpcResult.debug.entries.length > 0) {
                  hasDebugData = true;
                  // Handle debug data immediately - create overlay for each response with debug
                  handleRPCResponseWithDebug(rpcResult, 'upload_images', params);
                }
                
                status.processed = true;
                // Remove pending div and add success message
                this.removePendingDiv(status);
                this.addSuccessMessage(`Successfully processed ${status.file.name}`);
                
                nextIndexToProcess++;
                await processNext();
              } catch (error) {
                status.processing = false;
                status.error = error instanceof Error ? error.message : String(error);
                // Remove pending div and throw error up to overlay
                this.removePendingDiv(status);
                throw error;
              }
            } else if (!status.uploaded) {
              // Wait for upload to complete
              setTimeout(() => processNext(), 100);
              return;
            } else {
              nextIndexToProcess++;
            }
          }
        };
        
        await processNext();
        
        // Return success - disable auto-fade if debug data was present
        // Use standardized redirect pattern ('self' for refresh)
        return { 
          _showMessage: `Successfully uploaded ${this.uploadStatuses.length} image(s)`, 
          _autoFade: !hasDebugData, // Disable auto-fade if debug data was present
          _redirectAfterFade: hasDebugData ? null : 'self' // Only redirect if no debug data (standardized pattern)
        };
      },
      onCancel: () => {
        overlayManager.close(this.overlay);
      }
    });
    
    // Store references to buttons after overlay is shown (for disabling during upload)
      setTimeout(() => {
        const headerEl = (this.overlay?.getHeaderElement && this.overlay.getHeaderElement()) || document.querySelector('.overlay-window .contentWrapperHeader.overlay') as HTMLElement;
        if (!headerEl) {
          console.error('Could not find overlay header');
          return;
        }
        
        // Find buttons
        const cancelBtn = headerEl.querySelector('.cancelButton') as HTMLAnchorElement;
        const submitBtn = headerEl.querySelector('.submitButton') as HTMLAnchorElement;
        const middleBtn = headerEl.querySelector('.middleButton') as HTMLAnchorElement;
        
        // Store references
        this.uploadBtn = submitBtn;
        this.chooseFilesBtn = middleBtn;
      }, 100);
  }

  private addFile(file: File): void {
    // Get overlay window if not already stored
    if (!this.overlayWindow && this.overlay && typeof this.overlay.getWindowElement === 'function') {
      this.overlayWindow = this.overlay.getWindowElement();
    }
    if (!this.overlayWindow) {
      this.overlayWindow = document.querySelector('.overlay-window') as HTMLElement;
    }
    
    if (!this.overlayWindow) {
      console.error('Overlay window not found');
      return;
    }
    
    const fileId = this.filePathToId(file.name);
    
    // Double-check for duplicates (shouldn't happen due to check in change handler, but safety check)
    if (this.uploadStatuses.find(s => s.fileId === fileId)) {
      return; // Already exists, skip silently
    }
    
    const fileDiv = document.createElement('div');
    fileDiv.id = fileId;
    fileDiv.className = 'content overlay upload-file-item';
    
    // Remove button (X)
    const removeBtn = document.createElement('button');
    removeBtn.id = `remove_${fileId}`;
    removeBtn.className = 'upload-file-remove';
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', () => {
      this.removeFile(fileId);
    });
    fileDiv.appendChild(removeBtn);
    
    // File name
    const fileNameDiv = document.createElement('div');
    fileNameDiv.className = 'upload-file-name';
    fileNameDiv.textContent = file.name;
    fileDiv.appendChild(fileNameDiv);
    
    // Status message
    const statusDiv = document.createElement('div');
    statusDiv.id = `status_${fileId}`;
    statusDiv.className = 'upload-status pending';
    statusDiv.textContent = 'Pending';
    fileDiv.appendChild(statusDiv);
    
    // Progress bar container (initially hidden)
    const progressContainer = document.createElement('div');
    progressContainer.id = `upload-progress-container_${fileId}`;
    progressContainer.className = 'upload-progress-container';
    
    const progressBar = document.createElement('div');
    progressBar.className = 'upload-progress-bar';
    
    const progressFill = document.createElement('div');
    progressFill.id = `upload-progress-fill_${fileId}`;
    progressFill.className = 'upload-progress-fill';
    progressBar.appendChild(progressFill);
    
    progressContainer.appendChild(progressBar);
    fileDiv.appendChild(progressContainer);
    
    // Add directly to overlayWindow (after the last file item, or after header if no files exist)
    const existingFileItems = this.overlayWindow.querySelectorAll('.upload-file-item');
    if (existingFileItems.length > 0) {
      // Insert after the last file item
      const lastFileItem = existingFileItems[existingFileItems.length - 1];
      if (lastFileItem.nextSibling) {
        this.overlayWindow.insertBefore(fileDiv, lastFileItem.nextSibling);
      } else {
        this.overlayWindow.appendChild(fileDiv);
      }
    } else {
      // No files yet, insert after header
      const headerEl = this.overlayWindow.querySelector('.contentWrapperHeader.overlay');
      if (headerEl && headerEl.nextSibling) {
        this.overlayWindow.insertBefore(fileDiv, headerEl.nextSibling);
      } else {
        this.overlayWindow.appendChild(fileDiv);
      }
    }
    
    const status: FileUploadStatus = {
      fileId,
      file,
      uploaded: false,
      uploadResult: null,
      processing: false,
      processed: false,
      error: null,
      div: fileDiv,
      debugOptions: null // Will be set when submit is clicked
    };
    
    this.uploadStatuses.push(status);
  }

  private removeFile(fileId: string): void {
    // Find and remove the file status
    const statusIndex = this.uploadStatuses.findIndex(s => s.fileId === fileId);
    if (statusIndex === -1) return;
    
    const status = this.uploadStatuses[statusIndex];
    status.div.remove();
    this.uploadStatuses.splice(statusIndex, 1);
    
    // If no files left, show placeholder again
    if (this.uploadStatuses.length === 0) {
      if (!this.overlayWindow) {
        this.overlayWindow = document.querySelector('#overlayWindow') as HTMLElement;
      }
      
      if (this.overlayWindow) {
        const placeholderText = document.createTextNode('No files selected. Click "Choose Files" to add images.');
        const placeholderWrapper = document.createElement('div');
        placeholderWrapper.className = 'upload-placeholder';
        placeholderWrapper.appendChild(placeholderText);
        
        const placeholderContentDiv = document.createElement('div');
        placeholderContentDiv.className = 'content overlay upload-placeholder';
        placeholderContentDiv.appendChild(placeholderWrapper);
        
        // Insert placeholder after header
        const headerEl = this.overlayWindow.querySelector('.contentWrapperHeader.overlay');
        if (headerEl && headerEl.nextSibling) {
          this.overlayWindow.insertBefore(placeholderContentDiv, headerEl.nextSibling);
        } else {
          this.overlayWindow.appendChild(placeholderContentDiv);
        }
        this.placeholderDiv = placeholderContentDiv;
      }
      return;
    }
  }

  private updateFileStatus(status: FileUploadStatus, message: string, type: 'pending' | 'uploading' | 'uploaded' | 'processing' | 'success' | 'error'): void {
    const statusDiv = document.getElementById(`status_${status.fileId}`) as HTMLElement;
    if (!statusDiv) return;
    
    statusDiv.textContent = message;
    
    // Remove all status classes and add the appropriate one
    statusDiv.className = `upload-status ${type}`;
  }

  /**
   * Convert file item to pending processing div (remove X button, progress bar, change class)
   */
  private convertToPending(status: FileUploadStatus): void {
    const fileDiv = status.div;
    if (!fileDiv) return;
    
    // Get file name before removing everything
    const fileNameDiv = fileDiv.querySelector('.upload-file-name');
    const fileName = fileNameDiv ? fileNameDiv.textContent : status.file.name;
    
    // Remove all children
    fileDiv.innerHTML = '';
    
    // Change class
    fileDiv.className = 'content overlay pending-file-item';
    
    // Add file name
    const newFileNameDiv = document.createElement('div');
    newFileNameDiv.className = 'upload-file-name';
    newFileNameDiv.textContent = fileName;
    fileDiv.appendChild(newFileNameDiv);
    
    // Add pending status
    const pendingStatusDiv = document.createElement('div');
    pendingStatusDiv.className = 'pending-status';
    pendingStatusDiv.textContent = 'Upload done. Pending processing';
    fileDiv.appendChild(pendingStatusDiv);
  }

  /**
   * Remove pending div
   */
  private removePendingDiv(status: FileUploadStatus): void {
    if (status.div && status.div.parentNode) {
      status.div.remove();
    }
  }

  /**
   * Add success message to overlay messages array
   */
  private addSuccessMessage(message: string): void {
    if (!this.overlay) return;
    
    const currentMessages = (this.overlay as any)['state'].messages || [];
    (this.overlay as any).setState({
      messages: [...currentMessages, { type: 'success' as const, text: message }]
    });
  }

  private async uploadFile(status: FileUploadStatus, pageId: number | string): Promise<void> {
    const formData = new FormData();
    formData.append('file', status.file);
    
    const progressContainer = document.getElementById(`upload-progress-container_${status.fileId}`) as HTMLElement;
    const progressFill = document.getElementById(`upload-progress-fill_${status.fileId}`) as HTMLElement;
    
    if (progressContainer) {
      progressContainer.classList.add('show');
    }
    
    this.updateFileStatus(status, 'Uploading...', 'uploading');
    
    try {
      const xhr = new XMLHttpRequest();
      
      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && progressFill) {
          const percent = (e.loaded / e.total) * 100;
          progressFill.style.width = `${percent}%`;
        }
      });
      
      const uploadPromise = new Promise<{ temp_path: string; original_name: string }>((resolve, reject) => {
        xhr.addEventListener('load', () => {
          if (xhr.status === 200) {
            try {
              const result = JSON.parse(xhr.responseText);
              if (result.error) {
                reject(new Error(result.error));
              } else {
                const fileData = result.files ? result.files[0] : result;
                resolve({
                  temp_path: fileData.temp_path,
                  original_name: fileData.original_name
                });
              }
            } catch (e) {
              reject(new Error('Failed to parse response'));
            }
          } else {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        });
        
        xhr.addEventListener('error', () => {
          reject(new Error('Upload failed'));
        });
        
        xhr.open('POST', '/upload-file');
        xhr.send(formData);
      });
      
      const result = await uploadPromise;
      
      if (progressFill) {
        progressFill.style.width = '100%';
      }
      
      status.uploaded = true;
      status.uploadResult = result;
      // Convert file item to pending processing div
      this.convertToPending(status);
    } catch (error) {
      status.error = error instanceof Error ? error.message : String(error);
      if (progressFill) {
        progressFill.classList.add('error');
      }
      this.updateFileStatus(status, `Error: ${status.error}`, 'error');
      throw error;
    }
  }
}

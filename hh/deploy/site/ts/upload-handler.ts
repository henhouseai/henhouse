/**
 * Upload handler for image uploads
 */

import { RPCClient } from './rpc-client.js';
import { SeedData } from './seed.js';
import { OverlayManager } from './overlay-manager.js';

interface FileUploadStatus {
  index: number;
  file: File;
  uploaded: boolean;
  uploadResult: { temp_path: string; original_name: string } | null;
  processing: boolean;
  processed: boolean;
  error: string | null;
  div: HTMLElement;
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
   * Handle Upload: Upload images to current page
   */
  async handle(): Promise<void> {
    const overlayManager = OverlayManager.getInstance();
    
    // Get current page ID
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      this.rpc.showError('Upload', new Error('No page ID available'));
      return;
    }

    // Create placeholder content
    this.placeholderDiv = document.createElement('div');
    this.placeholderDiv.className = 'overlayContent upload-placeholder';
    this.placeholderDiv.textContent = 'No files selected. Click "Choose Files" to add images.';
    
    // Handle file selection
    this.fileInput.addEventListener('change', (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (!files || files.length === 0) return;
      
      // Get overlay window if not already stored
      if (!this.overlayWindow) {
        this.overlayWindow = document.querySelector('#overlayWindow') as HTMLElement;
      }
      
      if (!this.overlayWindow) {
        console.error('Overlay window not found');
        return;
      }
      
      // If this is the first file, remove placeholder
      if (this.placeholderDiv && this.placeholderDiv.parentNode) {
        this.placeholderDiv.remove();
        this.placeholderDiv = null;
      }
      
      // Add all selected files directly to overlayWindow
      for (let i = 0; i < files.length; i++) {
        this.addFile(files[i]);
      }
      
      // Reset input so same file can be selected again
      this.fileInput.value = '';
    });
    
    // Show overlay with custom header buttons
    this.overlay = overlayManager.show({
      header: 'Upload Images',
      content: this.placeholderDiv,
      closable: true, // Allow closing by clicking backdrop
      submitLabel: 'Upload',
      cancelLabel: 'Cancel',
      onSubmit: async () => {
        if (this.uploadStatuses.length === 0) {
          return { _showMessage: 'Please select at least one file', _autoFade: false };
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
        let hasErrors = false;
        let nextIndexToProcess = 0;
        
        const processNext = async (): Promise<void> => {
          while (nextIndexToProcess < this.uploadStatuses.length) {
            const status = this.uploadStatuses[nextIndexToProcess];
            
            if (status.error) {
              hasErrors = true;
              nextIndexToProcess++;
              continue;
            }
            
            if (status.uploaded && status.uploadResult && !status.processed && !status.processing) {
              status.processing = true;
              this.updateFileStatus(status, 'Processing...', 'processing');
              
              try {
                await this.rpc.call('upload_images', {
                  page_id: pageId,
                  file0_path: status.uploadResult.temp_path,
                  file0_name: status.uploadResult.original_name
                });
                
                status.processed = true;
                this.updateFileStatus(status, 'Complete', 'success');
                
                nextIndexToProcess++;
                await processNext();
              } catch (error) {
                status.processing = false;
                status.error = error instanceof Error ? error.message : String(error);
                hasErrors = true;
                this.updateFileStatus(status, `Error: ${status.error}`, 'error');
                // Stop processing on error
                return;
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
        
        // Reload page if all succeeded
        if (!hasErrors) {
          try {
            const { PageManager } = await import('./page-manager.js');
            const pageManager = PageManager.getInstance();
            const pageData = await this.rpc.getPage(pageId);
            pageManager.setPageData(pageData);
            
            // Return success with auto-fade flag
            return { _showMessage: `Successfully uploaded ${this.uploadStatuses.length} image(s)`, _autoFade: true };
          } catch (error) {
            return { _showMessage: `Uploaded images but failed to reload page: ${error instanceof Error ? error.message : String(error)}`, _autoFade: false };
          }
        } else {
          // Don't auto-fade on errors
          return { _showMessage: 'Some uploads failed. Please check errors below.', _autoFade: false };
        }
      },
      onCancel: () => {
        overlayManager.close(this.overlay);
      }
    });
    
    // After overlay is shown, modify the header to add Choose Files button
    setTimeout(() => {
      const headerEl = document.querySelector('#overlayWindow .overlayHeader') as HTMLElement;
      if (!headerEl) {
        console.error('Could not find overlay header');
        return;
      }
      
      // Find existing buttons
      const cancelBtn = headerEl.querySelector('.cancelButton') as HTMLAnchorElement;
      const submitBtn = headerEl.querySelector('.submitButton') as HTMLAnchorElement;
      
      if (!cancelBtn) {
        console.error('Could not find cancel button');
      }
      if (!submitBtn) {
        console.error('Could not find submit button');
      }
      if (!cancelBtn || !submitBtn) return;
      
      // Store reference to upload button
      this.uploadBtn = submitBtn;
      
      // Check if Choose Files button already exists
      if (headerEl.querySelector('.overlay-button-choose-files')) {
        this.chooseFilesBtn = headerEl.querySelector('.overlay-button-choose-files') as HTMLAnchorElement;
        return;
      }
      
      // Create Choose Files button
      this.chooseFilesBtn = document.createElement('a');
      this.chooseFilesBtn.className = 'overlay-button overlay-button-choose-files';
      this.chooseFilesBtn.textContent = 'Choose Files';
      this.chooseFilesBtn.href = '#';
      this.chooseFilesBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.fileInput.click();
      });
      
      // Insert Choose Files button between Cancel and Upload
      if (submitBtn.parentNode) {
        submitBtn.parentNode.insertBefore(this.chooseFilesBtn, submitBtn);
      }
    }, 100);
  }

  private addFile(file: File): void {
    // Get overlay window if not already stored
    if (!this.overlayWindow) {
      this.overlayWindow = document.querySelector('#overlayWindow') as HTMLElement;
    }
    
    if (!this.overlayWindow) {
      console.error('Overlay window not found');
      return;
    }
    
    const index = this.uploadStatuses.length;
    const fileDiv = document.createElement('div');
    fileDiv.className = 'overlayContent upload-file-item';
    
    // Remove button (X)
    const removeBtn = document.createElement('button');
    removeBtn.className = 'upload-file-remove';
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', () => {
      this.removeFile(index);
    });
    fileDiv.appendChild(removeBtn);
    
    // File name
    const fileNameDiv = document.createElement('div');
    fileNameDiv.className = 'upload-file-name';
    fileNameDiv.textContent = file.name;
    fileDiv.appendChild(fileNameDiv);
    
    // Status message
    const statusDiv = document.createElement('div');
    statusDiv.id = `upload-status-${index}`;
    statusDiv.className = 'upload-status pending';
    statusDiv.textContent = 'Pending';
    fileDiv.appendChild(statusDiv);
    
    // Progress bar container (initially hidden)
    const progressContainer = document.createElement('div');
    progressContainer.id = `upload-progress-container-${index}`;
    progressContainer.className = 'upload-progress-container';
    
    const progressBar = document.createElement('div');
    progressBar.className = 'upload-progress-bar';
    
    const progressFill = document.createElement('div');
    progressFill.id = `upload-progress-fill-${index}`;
    progressFill.className = 'upload-progress-fill';
    progressBar.appendChild(progressFill);
    
    progressContainer.appendChild(progressBar);
    fileDiv.appendChild(progressContainer);
    
    // Add directly to overlayWindow (after header, before any existing content)
    const headerEl = this.overlayWindow.querySelector('.overlayHeader');
    if (headerEl && headerEl.nextSibling) {
      this.overlayWindow.insertBefore(fileDiv, headerEl.nextSibling);
    } else {
      this.overlayWindow.appendChild(fileDiv);
    }
    
    const status: FileUploadStatus = {
      index,
      file,
      uploaded: false,
      uploadResult: null,
      processing: false,
      processed: false,
      error: null,
      div: fileDiv
    };
    
    this.uploadStatuses.push(status);
  }

  private removeFile(index: number): void {
    // Find and remove the file status
    const statusIndex = this.uploadStatuses.findIndex(s => s.index === index);
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
        this.placeholderDiv = document.createElement('div');
        this.placeholderDiv.className = 'overlayContent upload-placeholder';
        this.placeholderDiv.textContent = 'No files selected. Click "Choose Files" to add images.';
        
        // Insert placeholder after header
        const headerEl = this.overlayWindow.querySelector('.overlayHeader');
        if (headerEl && headerEl.nextSibling) {
          this.overlayWindow.insertBefore(this.placeholderDiv, headerEl.nextSibling);
        } else {
          this.overlayWindow.appendChild(this.placeholderDiv);
        }
      }
      return;
    }
    
    // Re-index remaining files
    this.uploadStatuses.forEach((s, i) => {
      s.index = i;
      const statusDiv = s.div.querySelector(`#upload-status-${s.index}`) as HTMLElement;
      const progressContainer = s.div.querySelector(`#upload-progress-container-${s.index}`) as HTMLElement;
      const progressBar = s.div.querySelector(`#upload-progress-bar-${s.index}`) as HTMLElement;
      const progressFill = s.div.querySelector(`#upload-progress-fill-${s.index}`) as HTMLElement;
      
      if (statusDiv) {
        statusDiv.id = `upload-status-${i}`;
      }
      if (progressContainer) {
        progressContainer.id = `upload-progress-container-${i}`;
      }
      if (progressBar) {
        progressBar.id = `upload-progress-bar-${i}`;
      }
      if (progressFill) {
        progressFill.id = `upload-progress-fill-${i}`;
      }
    });
  }

  private updateFileStatus(status: FileUploadStatus, message: string, type: 'pending' | 'uploading' | 'uploaded' | 'processing' | 'success' | 'error'): void {
    const statusDiv = status.div.querySelector(`#upload-status-${status.index}`) as HTMLElement;
    if (!statusDiv) return;
    
    statusDiv.textContent = message;
    
    // Remove all status classes and add the appropriate one
    statusDiv.className = `upload-status ${type}`;
  }

  private async uploadFile(status: FileUploadStatus, pageId: number | string): Promise<void> {
    const formData = new FormData();
    formData.append('file', status.file);
    
    const progressContainer = status.div.querySelector(`#upload-progress-container-${status.index}`) as HTMLElement;
    const progressFill = status.div.querySelector(`#upload-progress-fill-${status.index}`) as HTMLElement;
    
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
      this.updateFileStatus(status, 'Uploaded - Pending processing', 'uploaded');
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

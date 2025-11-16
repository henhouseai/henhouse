/**
 * Upload handler for image uploads
 */

import { RPCClient } from './rpc-client.js';
import { SeedData } from './seed.js';
import { OverlayManager } from './overlay-manager.js';

export class UploadHandler {
  private rpc: RPCClient;
  private seedData: SeedData;

  constructor(rpc: RPCClient, seedData: SeedData) {
    this.rpc = rpc;
    this.seedData = seedData;
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

    // Create file input element
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true;
    fileInput.accept = 'image/*';
    fileInput.style.display = 'none';
    
    // Create container for upload form
    const formContainer = document.createElement('div');
    formContainer.style.cssText = 'padding: 20px; min-width: 400px;';
    
    const fileInputLabel = document.createElement('label');
    fileInputLabel.textContent = 'Select Images:';
    fileInputLabel.style.cssText = 'display: block; margin-bottom: 10px; font-weight: bold;';
    formContainer.appendChild(fileInputLabel);
    
    const fileInputWrapper = document.createElement('div');
    fileInputWrapper.style.cssText = 'margin-bottom: 20px;';
    fileInputWrapper.appendChild(fileInput);
    formContainer.appendChild(fileInputWrapper);
    
    const fileListDiv = document.createElement('div');
    fileListDiv.id = 'upload-file-list';
    fileListDiv.style.cssText = 'margin-bottom: 20px; max-height: 200px; overflow-y: auto;';
    formContainer.appendChild(fileListDiv);
    
    const progressContainer = document.createElement('div');
    progressContainer.id = 'upload-progress-container';
    formContainer.appendChild(progressContainer);
    
    // Update file list when files are selected
    fileInput.addEventListener('change', (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (!files || files.length === 0) return;
      
      fileListDiv.innerHTML = '';
      for (let i = 0; i < files.length; i++) {
        const fileItem = document.createElement('div');
        fileItem.textContent = `${i + 1}. ${files[i].name}`;
        fileItem.style.cssText = 'padding: 5px; border-bottom: 1px solid #eee;';
        fileListDiv.appendChild(fileItem);
      }
    });
    
    // Create clickable area to trigger file input
    const clickArea = document.createElement('button');
    clickArea.type = 'button';
    clickArea.textContent = 'Choose Files...';
    clickArea.style.cssText = 'padding: 10px 20px; cursor: pointer;';
    clickArea.addEventListener('click', () => fileInput.click());
    fileInputWrapper.appendChild(clickArea);
    
    // Show overlay
    const overlay = overlayManager.show({
      header: 'Upload Images',
      content: formContainer,
      submitLabel: 'Upload',
      cancelLabel: 'Cancel',
      closable: true,
      onSubmit: async () => {
        const files = fileInput.files;
        if (!files || files.length === 0) {
          alert('Please select at least one file');
          return;
        }
        
        // Disable submit button (find it in the overlay content)
        const submitBtn = document.querySelector('.overlay-submit') as HTMLButtonElement;
        if (submitBtn) submitBtn.disabled = true;
        
        // Clear progress container and create progress bars
        progressContainer.innerHTML = '';
        const fileArray = Array.from(files);
        const uploadStatuses: Array<{
          index: number;
          file: File;
          uploaded: boolean;
          uploadResult: { temp_path: string; original_name: string } | null;
          processing: boolean;
          processed: boolean;
        }> = fileArray.map((file, index) => ({
          index,
          file,
          uploaded: false,
          uploadResult: null,
          processing: false,
          processed: false
        }));
        
        // Create progress bars
        uploadStatuses.forEach((status) => {
          const progressDiv = document.createElement('div');
          progressDiv.id = `upload-progress-${status.index}`;
          progressDiv.style.cssText = 'margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 4px;';
          progressDiv.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 5px;">${status.file.name}</div>
            <div style="background: #f0f0f0; border-radius: 4px; height: 20px; position: relative; overflow: hidden;">
              <div id="upload-progress-bar-${status.index}" style="background: #4CAF50; height: 100%; width: 0%; transition: width 0.3s;"></div>
              <div id="upload-progress-text-${status.index}" style="position: absolute; top: 0; left: 0; right: 0; text-align: center; line-height: 20px; font-size: 12px;">Waiting...</div>
            </div>
          `;
          progressContainer.appendChild(progressDiv);
        });
        
        // Upload all files in parallel
        const uploadPromises = fileArray.map(async (file, index) => {
          const formData = new FormData();
          formData.append('file', file);
          
          const progressBar = document.getElementById(`upload-progress-bar-${index}`) as HTMLElement;
          const progressText = document.getElementById(`upload-progress-text-${index}`) as HTMLElement;
          
          try {
            progressText.textContent = 'Uploading...';
            
            const xhr = new XMLHttpRequest();
            
            // Track upload progress
            xhr.upload.addEventListener('progress', (e) => {
              if (e.lengthComputable) {
                const percent = (e.loaded / e.total) * 100;
                progressBar.style.width = `${percent}%`;
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
                      // Handle both single file and array response formats
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
            progressBar.style.width = '100%';
            progressBar.style.background = '#4CAF50';
            progressText.textContent = 'Uploaded';
            
            uploadStatuses[index].uploaded = true;
            uploadStatuses[index].uploadResult = result;
            
            return { index, result };
          } catch (error) {
            progressBar.style.background = '#f44336';
            progressText.textContent = `Error: ${error instanceof Error ? error.message : String(error)}`;
            throw { index, error };
          }
        });
        
        // Wait for all uploads to complete (but don't fail if some fail)
        const uploadResults = await Promise.allSettled(uploadPromises);
        
        // Process files sequentially in order
        let nextIndexToProcess = 0;
        const processNext = async () => {
          // Find the next file that's ready to process (uploaded and in order)
          while (nextIndexToProcess < uploadStatuses.length) {
            const status = uploadStatuses[nextIndexToProcess];
            
            // Check if this file is ready (uploaded and not yet processed)
            if (status.uploaded && status.uploadResult && !status.processed && !status.processing) {
              status.processing = true;
              
              const progressText = document.getElementById(`upload-progress-text-${nextIndexToProcess}`) as HTMLElement;
              progressText.textContent = 'Processing...';
              
              try {
                // Make MCP call to upload_images
                await this.rpc.call('upload_images', {
                  page_id: pageId,
                  file0_path: status.uploadResult.temp_path,
                  file0_name: status.uploadResult.original_name
                });
                
                status.processed = true;
                progressText.textContent = 'Complete';
                
                nextIndexToProcess++;
                // Process next file
                await processNext();
              } catch (error) {
                status.processing = false;
                progressText.textContent = `Error: ${error instanceof Error ? error.message : String(error)}`;
                const progressBar = document.getElementById(`upload-progress-bar-${nextIndexToProcess}`) as HTMLElement;
                progressBar.style.background = '#f44336';
                // Stop processing on error
                return;
              }
            } else if (!status.uploaded) {
              // This file hasn't finished uploading yet, wait a bit and check again
              setTimeout(() => processNext(), 100);
              return;
            } else {
              // This file is already processed or failed, move to next
              nextIndexToProcess++;
            }
          }
        };
        
        // Start processing
        await processNext();
        
        // Reload page to show new images
        try {
          const { PageManager } = await import('./page-manager.js');
          const pageManager = PageManager.getInstance();
          const pageData = await this.rpc.getPage(pageId);
          pageManager.setPageData(pageData);
          // Trigger page refresh
          window.location.reload();
        } catch (error) {
          console.error('Failed to reload page:', error);
        }
        
        // Close overlay
        overlayManager.close(overlay);
      },
      onCancel: () => {
        overlayManager.close(overlay);
      }
    });
  }
}


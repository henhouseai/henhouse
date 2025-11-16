/**
 * Upload handler for image uploads
 */
import { OverlayManager } from './overlay-manager.js';
export class UploadHandler {
    constructor(rpc, seedData) {
        this.uploadStatuses = [];
        this.chooseFilesBtn = null;
        this.uploadBtn = null;
        this.overlay = null;
        this.rpc = rpc;
        this.seedData = seedData;
        this.fileInput = document.createElement('input');
        this.fileInput.type = 'file';
        this.fileInput.multiple = true;
        this.fileInput.accept = 'image/*';
        this.fileInput.style.display = 'none';
        this.filesContainer = document.createElement('div');
        this.filesContainer.id = 'upload-files-container';
        this.filesContainer.style.cssText = 'padding: 20px;';
    }
    /**
     * Handle Upload: Upload images to current page
     */
    async handle() {
        const overlayManager = OverlayManager.getInstance();
        // Get current page ID
        const pageId = this.seedData.page?.id;
        if (!pageId) {
            this.rpc.showError('Upload', new Error('No page ID available'));
            return;
        }
        // Create custom header with Cancel, Choose Files, and Upload buttons
        const headerDiv = document.createElement('div');
        headerDiv.className = 'overlayHeader';
        headerDiv.style.cssText = 'display: flex; justify-content: space-between; align-items: center;';
        const titleSpan = document.createElement('span');
        titleSpan.textContent = 'Upload Images';
        headerDiv.appendChild(titleSpan);
        const buttonsDiv = document.createElement('div');
        buttonsDiv.style.cssText = 'display: flex; gap: 10px;';
        // Cancel button (red)
        const cancelBtn = document.createElement('a');
        cancelBtn.className = 'cancelButton';
        cancelBtn.textContent = 'Cancel';
        cancelBtn.href = '#';
        cancelBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (this.overlay) {
                overlayManager.close(this.overlay);
            }
        });
        buttonsDiv.appendChild(cancelBtn);
        // Choose Files button (blue/gray)
        this.chooseFilesBtn = document.createElement('a');
        this.chooseFilesBtn.className = 'chooseFilesButton';
        this.chooseFilesBtn.textContent = 'Choose Files';
        this.chooseFilesBtn.href = '#';
        this.chooseFilesBtn.style.cssText = 'background: #2196F3; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none;';
        this.chooseFilesBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.fileInput.click();
        });
        buttonsDiv.appendChild(this.chooseFilesBtn);
        // Upload button (green)
        this.uploadBtn = document.createElement('a');
        this.uploadBtn.className = 'submitButton overlay-submit';
        this.uploadBtn.textContent = 'Upload';
        this.uploadBtn.href = '#';
        buttonsDiv.appendChild(this.uploadBtn);
        headerDiv.appendChild(buttonsDiv);
        // Handle file selection
        this.fileInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (!files || files.length === 0)
                return;
            for (let i = 0; i < files.length; i++) {
                this.addFile(files[i]);
            }
            // Reset input so same file can be selected again
            this.fileInput.value = '';
        });
        // Show overlay
        this.overlay = overlayManager.show({
            header: headerDiv,
            content: this.filesContainer,
            closable: false, // We handle closing manually
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
                const processNext = async () => {
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
                            }
                            catch (error) {
                                status.processing = false;
                                status.error = error instanceof Error ? error.message : String(error);
                                hasErrors = true;
                                this.updateFileStatus(status, `Error: ${status.error}`, 'error');
                                // Stop processing on error
                                return;
                            }
                        }
                        else if (!status.uploaded) {
                            // Wait for upload to complete
                            setTimeout(() => processNext(), 100);
                            return;
                        }
                        else {
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
                    }
                    catch (error) {
                        return { _showMessage: `Uploaded images but failed to reload page: ${error instanceof Error ? error.message : String(error)}`, _autoFade: false };
                    }
                }
                else {
                    // Don't auto-fade on errors
                    return { _showMessage: 'Some uploads failed. Please check errors below.', _autoFade: false };
                }
            },
            onCancel: () => {
                overlayManager.close(this.overlay);
            }
        });
    }
    addFile(file) {
        const index = this.uploadStatuses.length;
        const fileDiv = document.createElement('div');
        fileDiv.className = 'upload-file-item';
        fileDiv.style.cssText = 'margin-bottom: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 4px; background: white; position: relative;';
        // Remove button (X)
        const removeBtn = document.createElement('button');
        removeBtn.textContent = '×';
        removeBtn.style.cssText = 'position: absolute; top: 5px; right: 5px; background: #f44336; color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; font-size: 18px; line-height: 1;';
        removeBtn.addEventListener('click', () => {
            this.removeFile(index);
        });
        fileDiv.appendChild(removeBtn);
        // File name
        const fileNameDiv = document.createElement('div');
        fileNameDiv.textContent = file.name;
        fileNameDiv.style.cssText = 'font-weight: bold; margin-bottom: 10px; padding-right: 30px;';
        fileDiv.appendChild(fileNameDiv);
        // Status message
        const statusDiv = document.createElement('div');
        statusDiv.id = `upload-status-${index}`;
        statusDiv.className = 'upload-status';
        statusDiv.textContent = 'Pending';
        statusDiv.style.cssText = 'color: #666; font-size: 14px;';
        fileDiv.appendChild(statusDiv);
        // Progress bar container (initially hidden)
        const progressContainer = document.createElement('div');
        progressContainer.id = `upload-progress-container-${index}`;
        progressContainer.style.cssText = 'margin-top: 10px; display: none;';
        const progressBar = document.createElement('div');
        progressBar.id = `upload-progress-bar-${index}`;
        progressBar.style.cssText = 'background: #f0f0f0; border-radius: 4px; height: 20px; position: relative; overflow: hidden;';
        const progressFill = document.createElement('div');
        progressFill.id = `upload-progress-fill-${index}`;
        progressFill.style.cssText = 'background: #4CAF50; height: 100%; width: 0%; transition: width 0.3s;';
        progressBar.appendChild(progressFill);
        progressContainer.appendChild(progressBar);
        fileDiv.appendChild(progressContainer);
        this.filesContainer.appendChild(fileDiv);
        const status = {
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
    removeFile(index) {
        // Find and remove the file status
        const statusIndex = this.uploadStatuses.findIndex(s => s.index === index);
        if (statusIndex === -1)
            return;
        const status = this.uploadStatuses[statusIndex];
        status.div.remove();
        this.uploadStatuses.splice(statusIndex, 1);
        // Re-index remaining files
        this.uploadStatuses.forEach((s, i) => {
            s.index = i;
            const statusDiv = s.div.querySelector(`#upload-status-${s.index}`);
            const progressContainer = s.div.querySelector(`#upload-progress-container-${s.index}`);
            const progressBar = s.div.querySelector(`#upload-progress-bar-${s.index}`);
            const progressFill = s.div.querySelector(`#upload-progress-fill-${s.index}`);
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
    updateFileStatus(status, message, type) {
        const statusDiv = status.div.querySelector(`#upload-status-${status.index}`);
        if (!statusDiv)
            return;
        statusDiv.textContent = message;
        // Update colors based on type
        switch (type) {
            case 'pending':
                statusDiv.style.color = '#666';
                break;
            case 'uploading':
                statusDiv.style.color = '#2196F3';
                break;
            case 'uploaded':
                statusDiv.style.color = '#4CAF50';
                break;
            case 'processing':
                statusDiv.style.color = '#FF9800';
                break;
            case 'success':
                statusDiv.style.color = '#4CAF50';
                statusDiv.style.fontWeight = 'bold';
                break;
            case 'error':
                statusDiv.style.color = '#f44336';
                statusDiv.style.fontWeight = 'bold';
                break;
        }
    }
    async uploadFile(status, pageId) {
        const formData = new FormData();
        formData.append('file', status.file);
        const progressContainer = status.div.querySelector(`#upload-progress-container-${status.index}`);
        const progressFill = status.div.querySelector(`#upload-progress-fill-${status.index}`);
        if (progressContainer) {
            progressContainer.style.display = 'block';
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
            const uploadPromise = new Promise((resolve, reject) => {
                xhr.addEventListener('load', () => {
                    if (xhr.status === 200) {
                        try {
                            const result = JSON.parse(xhr.responseText);
                            if (result.error) {
                                reject(new Error(result.error));
                            }
                            else {
                                const fileData = result.files ? result.files[0] : result;
                                resolve({
                                    temp_path: fileData.temp_path,
                                    original_name: fileData.original_name
                                });
                            }
                        }
                        catch (e) {
                            reject(new Error('Failed to parse response'));
                        }
                    }
                    else {
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
                progressFill.style.background = '#4CAF50';
            }
            status.uploaded = true;
            status.uploadResult = result;
            this.updateFileStatus(status, 'Uploaded - Pending processing', 'uploaded');
        }
        catch (error) {
            status.error = error instanceof Error ? error.message : String(error);
            if (progressFill) {
                progressFill.style.background = '#f44336';
            }
            this.updateFileStatus(status, `Error: ${status.error}`, 'error');
            throw error;
        }
    }
}

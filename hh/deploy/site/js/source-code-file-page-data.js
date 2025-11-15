/**
 * SourceCodeFilePageData - Handles source code file pages with path and language fields.
 * Dynamic fields (file_path, language) are automatically discovered by base class.
 */
import { PageData } from './page-data.js';
import { PageManager } from './page-manager.js';
import { OverlayManager } from './overlay-manager.js';
export class SourceCodeFilePageData extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for source code file specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings(), // Include base page mappings (name, text)
            // Source code file specific mappings
            {
                fields: ['file_path'],
                mcpTool: 'modify_path',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    path: values['file_path']
                })
            },
            {
                fields: ['language'],
                mcpTool: 'modify_language',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    language: values['language']
                })
            }
        ];
    }
    /**
     * Handler for source_code_file_combo: Edit text, file_path, and language
     */
    async source_code_file_combo(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            // Get editable fields
            const currentText = this.getField('text', 'form') || '';
            const currentFilePath = this.getField('file_path', 'form') || '';
            const currentLanguage = this.getField('language', 'form') || '';
            // Get read-only fields (these should NOT be registered for editing)
            const pageIdValue = this.getField('id') || '';
            const pageClass = this.getField('class') || '';
            const pageLink = this.getField('link') || '';
            const lastModified = this.getField('last_modified') || '';
            const username = this.getField('username') || '';
            const path = this.getField('path') || [];
            const pathStr = Array.isArray(path) ? path.map((p) => p.name).filter(Boolean).join(' / ') : '';
            // Create form HTML with editable and read-only fields
            const formHtml = `
        <div class="overlayContent">
          <div class="overlay-form-section">
            <h3 class="overlay-section-title">Editable Fields:</h3>
            <div class="overlay-form-group">
              <label>File path:</label>
              <input type="text" id="page-field-file_path" value="${this.escapeHtml(currentFilePath)}" class="overlay-form-input">
            </div>
            <div class="overlay-form-group">
              <label>Language:</label>
              <input type="text" id="page-field-language" value="${this.escapeHtml(currentLanguage)}" class="overlay-form-input">
            </div>
            <div class="overlay-form-group">
              <label>Page text:</label>
              <textarea id="page-field-text" name="text" rows="20" cols="80" class="overlay-form-textarea">${this.escapeHtml(currentText)}</textarea>
            </div>
          </div>
          <div class="overlay-form-divider">
            <h3 class="overlay-section-title">Read-Only Fields (for display only):</h3>
            <div class="overlay-form-grid">
              <div><strong>ID:</strong></div>
              <div>${this.escapeHtml(String(pageIdValue))}</div>
              <div><strong>Class:</strong></div>
              <div>${this.escapeHtml(pageClass)}</div>
              <div><strong>Link:</strong></div>
              <div>${this.escapeHtml(pageLink)}</div>
              <div><strong>Last Modified:</strong></div>
              <div>${this.escapeHtml(lastModified)}</div>
              <div><strong>Username:</strong></div>
              <div>${this.escapeHtml(username)}</div>
              <div><strong>Path:</strong></div>
              <div>${this.escapeHtml(pathStr)}</div>
            </div>
          </div>
        </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Edit Source Code File',
                content: formHtml,
                closable: true,
                submitLabel: 'Submit',
                cancelLabel: 'Cancel',
                onCancel: () => {
                    pageManager.clearFieldRegistry();
                },
                onUnmount: () => {
                    pageManager.clearFieldRegistry();
                },
                onSubmit: async () => {
                    // Process operations incrementally
                    const changedFields = pageManager['detectChangedFields']();
                    const editableFields = changedFields.filter((field) => field !== 'class');
                    if (editableFields.length === 0) {
                        return { success: true, noChanges: true, _showMessage: 'No changes made', _autoFade: true };
                    }
                    const optimalMappings = pageManager['selectOptimalMappings'](editableFields);
                    const currentValues = pageManager['extractFormValues']();
                    if (!pageId) {
                        throw new Error('No page ID available');
                    }
                    const result = await this.processOperationsIncrementally(rpc, optimalMappings, currentValues, pageId);
                    const allSucceeded = result.success && result.errors.length === 0;
                    if (allSucceeded) {
                        if (result.success && pageId) {
                            // Update page text if it was changed
                            const textOp = result.operations?.find((op) => op.fields?.includes('text'));
                            if (textOp && textOp.success) {
                                try {
                                    const getTextResult = await rpc.call('get_text', { page_id: pageId });
                                    const parsedTextResult = rpc.extractMCPData(getTextResult);
                                    const processedText = parsedTextResult?.processed_text;
                                    if (processedText) {
                                        const textDiv = document.getElementById(`page-text-${pageId}`);
                                        if (textDiv) {
                                            textDiv.innerHTML = processedText;
                                        }
                                    }
                                }
                                catch (error) {
                                    console.error('Failed to fetch updated text:', error);
                                }
                            }
                            // Update file_path and language in internal PageData if they were changed
                            const filePathOp = result.operations?.find((op) => op.fields?.includes('file_path'));
                            if (filePathOp && filePathOp.success && filePathOp.result) {
                                const parsedResult = rpc.extractMCPData(filePathOp.result);
                                const resultPageData = parsedResult?.page || parsedResult;
                                const newFilePath = resultPageData?.file_path;
                                if (newFilePath !== undefined) {
                                    this.updateFieldValue('file_path', newFilePath);
                                }
                            }
                            const languageOp = result.operations?.find((op) => op.fields?.includes('language'));
                            if (languageOp && languageOp.success && languageOp.result) {
                                const parsedResult = rpc.extractMCPData(languageOp.result);
                                const resultPageData = parsedResult?.page || parsedResult;
                                const newLanguage = resultPageData?.language;
                                if (newLanguage !== undefined) {
                                    this.updateFieldValue('language', newLanguage);
                                }
                            }
                        }
                        return { ...result, _autoFade: true };
                    }
                    else {
                        // Don't throw - errors are already shown in overlay
                        return { ...result };
                    }
                }
            });
            // Focus the file path input after overlay is shown
            setTimeout(() => {
                const input = document.getElementById('page-field-file_path');
                if (input) {
                    input.focus();
                    input.select();
                }
            }, 100);
        }
        catch (error) {
            rpc.showError('source_code_file_combo', error);
        }
    }
}

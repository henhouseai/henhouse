/**
 * PageActionsFields - Mixin for field editing actions (modify_name, modify_text, combo)
 */
import { PageManager } from './page-manager.js';
import { OverlayManager } from './overlay/overlay-manager.js';
export class PageActionsFields {
    /**
     * Handler for modify_name: Edit page name
     */
    async modify_name(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            // Request 'name' field with 'form' context to register it for editing
            const currentName = this.getField('name', 'form') || '';
            // Create form HTML with standardized field ID using array-based content structure
            const formHtml = `
          <div class="overlay-form-group">
            <label>Page name:</label>
            <input type="text" id="page-field-name" value="${this.escapeHtml(currentName)}" class="overlay-form-input">
          </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Modify Page Name',
                content: [formHtml],
                contentHeaders: [''],
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
                            const nameOp = result.operations?.find((op) => op.fields?.includes('name'));
                            if (nameOp && nameOp.success && nameOp.result) {
                                // nameOp.result is already the extracted data
                                const resultPageData = nameOp.result?.page || nameOp.result;
                                const newName = resultPageData?.name;
                                const newRawText = resultPageData?.text;
                                if (newName) {
                                    this.updateFieldValue('name', newName);
                                    if (newRawText !== undefined) {
                                        this.updateFieldValue('text', newRawText);
                                    }
                                    // Update breadcrumb DOM
                                    const headerEl = document.getElementById('header');
                                    if (headerEl) {
                                        const pathUl = headerEl.querySelector('ul.path');
                                        if (pathUl) {
                                            const listItems = pathUl.querySelectorAll('li');
                                            if (listItems.length > 0) {
                                                const lastLi = listItems[listItems.length - 1];
                                                const lastLink = lastLi.querySelector('a');
                                                if (lastLink) {
                                                    lastLink.textContent = newName;
                                                }
                                            }
                                        }
                                    }
                                    // Update page text in case it contains a link to itself
                                    try {
                                        // Don't pass debug options to get_text - it's just a data fetch
                                        const getTextResult = await rpc.call('get_text', { page_id: pageId }, null);
                                        const processedText = getTextResult.data?.processed_text;
                                        this.updatePageTextDiv(pageId, processedText);
                                    }
                                    catch (error) {
                                        console.error('Failed to fetch updated text after name change:', error);
                                    }
                                }
                            }
                        }
                        return { ...result, _autoFade: true, debug: result.debug };
                    }
                    else {
                        // Don't throw - errors are already shown in overlay
                        return { ...result };
                    }
                }
            });
            // Focus the input after overlay is shown
            setTimeout(() => {
                const input = document.getElementById('page-field-name');
                if (input) {
                    input.focus();
                    input.select();
                }
            }, 100);
        }
        catch (error) {
            rpc.showError('modify_name', error);
        }
    }
    /**
     * Handler for modify_text: Edit page text content
     */
    async modify_text(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            // Request 'text' field with 'form' context to register it for editing
            const currentText = this.getField('text', 'form') || '';
            // Create textarea form with standardized field ID using array-based content structure
            const formHtml = `
          <div class="overlay-form-group">
            <textarea id="page-field-text" name="text" rows="20" cols="80" class="overlay-form-textarea">${this.escapeHtml(currentText)}</textarea>
          </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Text Editor',
                content: [formHtml],
                contentHeaders: [''],
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
                        // After successful submit, fetch processed text and update DOM
                        if (result && pageId) {
                            try {
                                // Don't pass debug options to get_text - it's just a data fetch
                                const getTextResult = await rpc.call('get_text', { page_id: pageId }, null);
                                const processedText = getTextResult.data?.processed_text;
                                this.updatePageTextDiv(pageId, processedText);
                            }
                            catch (error) {
                                console.error('Failed to fetch updated text:', error);
                            }
                        }
                        return { ...result, _autoFade: true, debug: result.debug };
                    }
                    else {
                        // Don't throw - errors are already shown in overlay
                        return { ...result, debug: result.debug };
                    }
                }
            });
            // Focus the textarea after overlay is shown
            setTimeout(() => {
                const textarea = document.getElementById('page-field-text');
                if (textarea) {
                    textarea.focus();
                }
            }, 100);
        }
        catch (error) {
            rpc.showError('modify_text', error);
        }
    }
    /**
     * Handler for combo: Multi-field editing form
     */
    async combo(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            // Get editable fields
            const currentName = this.getField('name', 'form') || '';
            const currentText = this.getField('text', 'form') || '';
            // Get read-only fields (these should NOT be registered for editing)
            const pageIdValue = this.getField('id') || '';
            const pageClass = this.getField('class') || '';
            const pageLink = this.getField('link') || '';
            const lastModified = this.getField('last_modified') || '';
            const username = this.getField('username') || '';
            const path = this.getField('path') || [];
            const pathStr = Array.isArray(path) ? path.map((p) => p.name).filter(Boolean).join(' / ') : '';
            // Create form HTML with editable and read-only fields using array-based content structure
            const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Page name:</label>
            <input type="text" id="page-field-name" value="${this.escapeHtml(currentName)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Page text:</label>
            <textarea id="page-field-text" name="text" rows="10" cols="80" class="overlay-form-textarea">${this.escapeHtml(currentText)}</textarea>
          </div>
      `;
            const readOnlyFieldsHtml = `
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
      `;
            OverlayManager.getInstance().show({
                header: 'Combo Test Form',
                content: [editableFieldsHtml, readOnlyFieldsHtml],
                contentHeaders: ['Editable Fields', 'Read-Only Fields (for display only)'],
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
                            const nameOp = result.operations?.find((op) => op.fields?.includes('name'));
                            if (nameOp && nameOp.success && nameOp.result) {
                                // nameOp.result is already the extracted data
                                const resultPageData = nameOp.result?.page || nameOp.result;
                                const newName = resultPageData?.name;
                                if (newName) {
                                    const headerEl = document.getElementById('header');
                                    if (headerEl) {
                                        const pathUl = headerEl.querySelector('ul.path');
                                        if (pathUl) {
                                            const listItems = pathUl.querySelectorAll('li');
                                            if (listItems.length > 0) {
                                                const lastLi = listItems[listItems.length - 1];
                                                const lastLink = lastLi.querySelector('a');
                                                if (lastLink) {
                                                    lastLink.textContent = newName;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            const textOp = result.operations?.find((op) => op.fields?.includes('text'));
                            if (textOp && textOp.success) {
                                try {
                                    // Don't pass debug options to get_text - it's just a data fetch
                                    const getTextResult = await rpc.call('get_text', { page_id: pageId }, null);
                                    const processedText = getTextResult.data?.processed_text;
                                    this.updatePageTextDiv(pageId, processedText);
                                }
                                catch (error) {
                                    console.error('Failed to fetch updated text:', error);
                                }
                            }
                        }
                        return { ...result, _autoFade: true, debug: result.debug };
                    }
                    else {
                        // Don't throw - errors are already shown in overlay
                        return { ...result, debug: result.debug };
                    }
                }
            });
            // Focus the name input after overlay is shown
            setTimeout(() => {
                const input = document.getElementById('page-field-name');
                if (input) {
                    input.focus();
                    input.select();
                }
            }, 100);
        }
        catch (error) {
            rpc.showError('combo', error);
        }
    }
    /**
     * Handler for set_page_visibility: Edit page visibility
     */
    async set_page_visibility(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            // Request 'visibility' field with 'form' context to register it for editing
            const currentVisibility = this.getField('visibility', 'form') || 1;
            // Create form HTML with standardized field ID using array-based content structure
            const formHtml = `
          <div class="overlay-form-group">
            <label>Visibility:</label>
            <input type="number" id="page-field-visibility" value="${currentVisibility}" min="0" class="overlay-form-input">
          </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Set Page Visibility',
                content: [formHtml],
                contentHeaders: [''],
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
                        return { ...result, _autoFade: true, debug: result.debug };
                    }
                    else {
                        // Don't throw - errors are already shown in overlay
                        return { ...result, debug: result.debug };
                    }
                }
            });
            // Focus the input after overlay is shown
            setTimeout(() => {
                const input = document.getElementById('page-field-visibility');
                if (input) {
                    input.focus();
                    input.select();
                }
            }, 100);
        }
        catch (error) {
            rpc.showError('set_page_visibility', error);
        }
    }
    /**
     * Handler for set_page_display_style: Edit page display style
     */
    async set_page_display_style(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            // Request 'displayStyle' field with 'form' context to register it for editing
            const currentDisplayStyle = this.getField('displayStyle', 'form') || 1;
            // Create form HTML with standardized field ID using array-based content structure
            const formHtml = `
          <div class="overlay-form-group">
            <label>Display Style:</label>
            <input type="number" id="page-field-displayStyle" value="${currentDisplayStyle}" min="0" class="overlay-form-input">
          </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Set Page Display Style',
                content: [formHtml],
                contentHeaders: [''],
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
                        return { ...result, _autoFade: true, debug: result.debug };
                    }
                    else {
                        // Don't throw - errors are already shown in overlay
                        return { ...result, debug: result.debug };
                    }
                }
            });
            // Focus the input after overlay is shown
            setTimeout(() => {
                const input = document.getElementById('page-field-displayStyle');
                if (input) {
                    input.focus();
                    input.select();
                }
            }, 100);
        }
        catch (error) {
            rpc.showError('set_page_display_style', error);
        }
    }
}

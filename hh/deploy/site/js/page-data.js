/**
 * PageData - Base class for managing page data.
 * Pure data model - business logic is in PageManager.
 */
import { PageManager } from './page-manager.js';
import { OverlayManager } from './overlay-manager.js';
export class PageData {
    constructor(data) {
        this.dynamicFields = {};
        // Read-only fields that can be accessed but not edited
        this.readOnlyFields = new Set([
            'id',
            'class',
            'link',
            'last_modified',
            'username',
            'path'
        ]);
        this.data = data;
        this.discoverDynamicFields();
        // Register field mappings with PageManager
        const pageManager = PageManager.getInstance();
        pageManager.registerFieldMappings(this.getFieldMappings());
    }
    /**
     * Discover dynamic fields that aren't in the base page fields list
     */
    discoverDynamicFields() {
        for (const [key, value] of Object.entries(this.data.page)) {
            if (!PageData.BASE_PAGE_FIELDS.includes(key)) {
                this.dynamicFields[key] = value;
            }
        }
    }
    /**
     * Get field value with special handling for certain fields
     * @param fieldName - Name of the field to get
     * @param context - 'display' (default) or 'form' (registers field for editing)
     * @returns Field value or null if not found
     */
    getField(fieldName, context = 'display') {
        // Special handling for base page fields
        switch (fieldName) {
            case 'text':
                // Special text processing - return raw text for now
                const textValue = this.data.page.text;
                if (context === 'form') {
                    PageManager.getInstance().registerField('text', textValue, 'textarea');
                }
                return textValue;
            case 'name':
                // Special breadcrumb/display handling
                const nameValue = this.data.page.name;
                if (context === 'form') {
                    PageManager.getInstance().registerField('name', nameValue, 'text');
                }
                return nameValue;
            case 'class':
                // Read-only field - return value but don't register for editing
                return this.data.page.class;
            default:
                // Check if it's a read-only field
                if (this.readOnlyFields.has(fieldName)) {
                    // Return value from page data or dynamic fields, but don't register for editing
                    if (fieldName in this.data.page) {
                        return this.data.page[fieldName];
                    }
                    if (fieldName in this.dynamicFields) {
                        return this.dynamicFields[fieldName];
                    }
                    return null;
                }
                // Check if it's a base page field
                if (fieldName in this.data.page) {
                    const value = this.data.page[fieldName];
                    if (context === 'form') {
                        // Auto-detect field type for base fields
                        const fieldType = this.detectFieldType(fieldName, value);
                        PageManager.getInstance().registerField(fieldName, value, fieldType);
                    }
                    return value;
                }
                // Check if it's a dynamic field
                if (fieldName in this.dynamicFields) {
                    const value = this.dynamicFields[fieldName];
                    if (context === 'form') {
                        // Auto-detect field type for dynamic fields
                        const fieldType = this.detectFieldType(fieldName, value);
                        PageManager.getInstance().registerField(fieldName, value, fieldType);
                    }
                    return value;
                }
                // Field not found
                return null;
        }
    }
    /**
     * Auto-detect field type based on field name and value
     */
    detectFieldType(fieldName, value) {
        if (typeof value === 'boolean')
            return 'checkbox';
        if (typeof value === 'number')
            return 'number';
        if (typeof value === 'string' && value.length > 100)
            return 'textarea';
        return 'text';
    }
    /**
     * Update internal data with new field value after successful update
     * This ensures the next form shows the updated value, not the old one
     */
    updateFieldValue(fieldName, newValue) {
        // Check if it's a base page field
        if (fieldName in this.data.page) {
            this.data.page[fieldName] = newValue;
        }
        else {
            // Otherwise, store in dynamic fields
            this.dynamicFields[fieldName] = newValue;
        }
    }
    /**
     * Get field-to-MCP mappings for this page class.
     * Derived classes should override this to provide their specific mappings.
     * Base class provides mappings for common page fields.
     */
    getFieldMappings() {
        return [
            // Individual field setters (highest priority - exact matches)
            {
                fields: ['name'],
                mcpTool: 'modify_name',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    name: values['name']
                })
            },
            {
                fields: ['text'],
                mcpTool: 'modify_text',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    text: values['text']
                })
            }
            // Derived classes can add more mappings here
        ];
    }
    /**
     * Get page ID (convenience method)
     */
    get id() {
        return this.data.page.id;
    }
    // ===== Images Helpers =====
    getImages() {
        return this.data.images || [];
    }
    getImageCount() {
        return this.data.images?.length || 0;
    }
    getPrimaryImage() {
        return this.data.images && this.data.images.length > 0 ? this.data.images[0] : null;
    }
    getImageByRank(rank) {
        return this.data.images?.find(img => img.image_rank === rank) || null;
    }
    // ===== Children Helpers =====
    getChildrenByClass() {
        return this.data.children_by_class || {};
    }
    getChildrenForClass(className) {
        const classData = this.data.children_by_class?.[className];
        return classData?.children || [];
    }
    getAllChildren() {
        const all = [];
        for (const classData of Object.values(this.data.children_by_class || {})) {
            all.push(...(classData.children || []));
        }
        return all;
    }
    getChildCount() {
        return this.getAllChildren().length;
    }
    getChildCountForClass(className) {
        return this.getChildrenForClass(className).length;
    }
    // ===== Path/Breadcrumb Helpers =====
    getBreadcrumbPath() {
        return this.data.page.path || [];
    }
    getBreadcrumbNames() {
        return this.getBreadcrumbPath().map(p => p.name || '').filter(n => n.length > 0);
    }
    // ===== Raw Data Access =====
    getRawData() {
        return this.data;
    }
    getPageData() {
        return this.data.page;
    }
    // ===== Handler Methods =====
    // These are UI handlers for page-specific CRUD operations
    // They accept RPC client as parameter and use PageManager for business logic
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
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
            // Create form HTML with standardized field ID
            const formHtml = `
        <div class="overlayContent">
          <div>
            <label>Page name:</label>
            <input type="text" id="page-field-name" value="${this.escapeHtml(currentName)}">
          </div>
        </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Modify Page Name',
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
                    const result = await pageManager.submitChanges(rpc);
                    if (result.noChanges) {
                        return { ...result, _showMessage: result.message || 'No changes made', _autoFade: true };
                    }
                    const messages = [];
                    if (result.operations && result.operations.length > 0) {
                        result.operations.forEach((op) => {
                            messages.push(op.message || `${op.mapping}: ${op.success ? 'Success' : 'Failed'}`);
                        });
                    }
                    else {
                        messages.push(result.message || (result.success ? 'Success' : 'Failed'));
                    }
                    const combinedMessage = messages.join('\n');
                    const allSucceeded = result.success && result.errors.length === 0;
                    if (allSucceeded) {
                        if (result.success && pageId) {
                            const nameOp = result.operations?.find((op) => op.fields?.includes('name'));
                            if (nameOp && nameOp.success && nameOp.result) {
                                const parsedResult = rpc.extractMCPData(nameOp.result);
                                const resultPageData = parsedResult?.page || parsedResult;
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
                                        console.error('Failed to fetch updated text after name change:', error);
                                    }
                                }
                            }
                        }
                        return { ...result, _showMessage: combinedMessage, _autoFade: true };
                    }
                    else {
                        throw new Error(combinedMessage);
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
            // Create textarea form with standardized field ID
            const formHtml = `
        <div class="overlayContent">
          <div>
            <textarea id="page-field-text" name="text" rows="20" cols="80" style="width: 100%; min-height: 400px; font-family: monospace;">${this.escapeHtml(currentText)}</textarea>
          </div>
        </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Text Editor',
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
                    const result = await pageManager.submitChanges(rpc);
                    if (result.noChanges) {
                        return { ...result, _showMessage: result.message || 'No changes made', _autoFade: true };
                    }
                    const messages = [];
                    if (result.operations && result.operations.length > 0) {
                        result.operations.forEach((op) => {
                            messages.push(op.message || `${op.mapping}: ${op.success ? 'Success' : 'Failed'}`);
                        });
                    }
                    else {
                        messages.push(result.message || (result.success ? 'Success' : 'Failed'));
                    }
                    const combinedMessage = messages.join('\n');
                    const allSucceeded = result.success && result.errors.length === 0;
                    if (allSucceeded) {
                        // After successful submit, fetch processed text and update DOM
                        if (result && pageId) {
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
                        return { ...result, _showMessage: combinedMessage, _autoFade: true };
                    }
                    else {
                        throw new Error(combinedMessage);
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
     * Handler for delete_page: Delete a page with confirmation
     */
    async delete_page(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            const pageName = this.getField('name') || `Page ${pageId}`;
            const pageClass = this.getField('class') || 'page';
            // Create form HTML with confirmation checkbox
            const formHtml = `
        <div class="overlayContent">
          <div style="margin-bottom: 20px;">
            <p><strong>Warning:</strong> This will permanently delete the page and all its children.</p>
            <p>Page: <strong>${this.escapeHtml(pageName)}</strong> (ID: ${pageId}, Class: ${this.escapeHtml(pageClass)})</p>
          </div>
          <div>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" id="page-delete-confirm" style="width: auto;">
              <span>I confirm that I want to delete this page</span>
            </label>
          </div>
        </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Delete Page',
                content: formHtml,
                closable: true,
                submitLabel: 'Delete',
                cancelLabel: 'Cancel',
                onCancel: () => {
                    pageManager.clearFieldRegistry();
                },
                onUnmount: () => {
                    pageManager.clearFieldRegistry();
                },
                onSubmit: async () => {
                    const confirmCheckbox = document.getElementById('page-delete-confirm');
                    if (!confirmCheckbox || !confirmCheckbox.checked) {
                        throw new Error('You must confirm deletion by checking the confirmation box');
                    }
                    try {
                        const result = await rpc.call('delete_page', {
                            page_id: pageId,
                            confirm: true
                        });
                        return {
                            success: true,
                            _showMessage: `Page "${this.escapeHtml(pageName)}" has been deleted successfully.`,
                            _autoFade: true
                        };
                    }
                    catch (error) {
                        const errorMessage = error instanceof Error ? error.message : String(error);
                        throw new Error(`Failed to delete page: ${errorMessage}`);
                    }
                }
            });
            // Focus the checkbox after overlay is shown
            setTimeout(() => {
                const checkbox = document.getElementById('page-delete-confirm');
                if (checkbox) {
                    checkbox.focus();
                }
            }, 100);
        }
        catch (error) {
            rpc.showError('delete_page', error);
        }
    }
    /**
     * Handler for combo: Test form with name/text editable and read-only fields displayed
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
            // Create form HTML with editable and read-only fields
            const formHtml = `
        <div class="overlayContent">
          <div style="margin-bottom: 20px;">
            <h3 style="margin-bottom: 10px;">Editable Fields:</h3>
            <div style="margin-bottom: 15px;">
              <label>Page name:</label>
              <input type="text" id="page-field-name" value="${this.escapeHtml(currentName)}" style="width: 100%;">
            </div>
            <div style="margin-bottom: 15px;">
              <label>Page text:</label>
              <textarea id="page-field-text" name="text" rows="10" cols="80" style="width: 100%; min-height: 200px; font-family: monospace;">${this.escapeHtml(currentText)}</textarea>
            </div>
          </div>
          <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ccc;">
            <h3 style="margin-bottom: 10px;">Read-Only Fields (for display only):</h3>
            <div style="display: grid; grid-template-columns: 150px 1fr; gap: 10px; margin-bottom: 10px;">
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
                header: 'Combo Test Form',
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
                    const result = await pageManager.submitChanges(rpc);
                    if (result.noChanges) {
                        return { ...result, _showMessage: result.message || 'No changes made', _autoFade: true };
                    }
                    const messages = [];
                    if (result.operations && result.operations.length > 0) {
                        result.operations.forEach((op) => {
                            messages.push(op.message || `${op.mapping}: ${op.success ? 'Success' : 'Failed'}`);
                        });
                    }
                    else {
                        messages.push(result.message || (result.success ? 'Success' : 'Failed'));
                    }
                    const combinedMessage = messages.join('\n');
                    const allSucceeded = result.success && result.errors.length === 0;
                    if (allSucceeded) {
                        if (result.success && pageId) {
                            const nameOp = result.operations?.find((op) => op.fields?.includes('name'));
                            if (nameOp && nameOp.success && nameOp.result) {
                                const parsedResult = rpc.extractMCPData(nameOp.result);
                                const resultPageData = parsedResult?.page || parsedResult;
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
                        }
                        return { ...result, _showMessage: combinedMessage, _autoFade: true };
                    }
                    else {
                        throw new Error(combinedMessage);
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
}
// Base page fields that are always present
PageData.BASE_PAGE_FIELDS = [
    'id', 'name', 'link', 'parent', 'class', 'visibility', 'text',
    'last_modified', 'username', 'comments', 'path'
];

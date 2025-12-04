/**
 * PageActionsPages - Mixin for page management actions (add_page, move_page, delete_page)
 */
import { PageManager } from './page-manager.js';
import { OverlayManager } from './overlay/overlay-manager.js';
export class PageActionsPages {
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
            // Create form HTML with confirmation checkbox using array-based content structure
            const formHtml = `
          <div class="overlay-warning-text">
            <p><strong>Warning:</strong> This will permanently delete the page and all its children.</p>
            <p>Page: <strong>${this.escapeHtml(pageName)}</strong> (ID: ${pageId}, Class: ${this.escapeHtml(pageClass)})</p>
          </div>
          <div class="overlay-form-group">
            <label class="overlay-label-inline">
              <input type="checkbox" id="page-delete-confirm" class="overlay-form-checkbox">
              <span>I confirm that I want to delete this page</span>
            </label>
          </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Delete Page',
                content: [formHtml],
                contentHeaders: [''],
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
                        // Use standardized redirect pattern: 'parent' redirects to parent page
                        return {
                            debug: result.debug,
                            success: true,
                            _showMessage: `Page "${this.escapeHtml(pageName)}" has been deleted successfully.`,
                            _autoFade: true,
                            _redirectAfterFade: 'parent' // Standardized redirect pattern
                        };
                    }
                    catch (error) {
                        throw error;
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
     * Handler for add_page: Create a new child page
     */
    async add_page(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            // Step 1: Get allowed child classes
            const classInfoResult = await rpc.call('get_add_page_class_info', { page_id: pageId });
            const classInfo = classInfoResult.data;
            if (!classInfo || !classInfo.allowed_classes || classInfo.allowed_classes.length === 0) {
                throw new Error('No allowed child classes found for this page');
            }
            const allowedClasses = classInfo.allowed_classes;
            // Step 2: Build form HTML with class selector and name input
            let classSelectOptions = '';
            let selectedClass = '';
            let selectedClassAllowNull = true;
            if (allowedClasses.length === 1) {
                // Auto-select if only one option
                selectedClass = allowedClasses[0].class_name;
                selectedClassAllowNull = allowedClasses[0].allow_null_names;
                classSelectOptions = `<option value="${this.escapeHtml(selectedClass)}" selected>${this.escapeHtml(selectedClass)}</option>`;
            }
            else {
                // Multiple options - show dropdown
                classSelectOptions = '<option value="">-- Select a class --</option>';
                for (const classOption of allowedClasses) {
                    classSelectOptions += `<option value="${this.escapeHtml(classOption.class_name)}" data-allow-null="${classOption.allow_null_names}">${this.escapeHtml(classOption.class_name)}</option>`;
                }
            }
            const formHtml = `
          <div class="overlay-form-group">
            <label>Page class:</label>
            <select id="add-page-class" class="overlay-form-select">
              ${classSelectOptions}
            </select>
          </div>
          <div class="overlay-form-group">
            <label>Page name:</label>
            <input type="text" id="add-page-name" value="" class="overlay-form-input" placeholder="${selectedClassAllowNull ? 'Optional' : 'Required'}">
          </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Add New Page',
                content: [formHtml],
                contentHeaders: [''],
                closable: true,
                submitLabel: 'Add Page',
                cancelLabel: 'Cancel',
                onSubmit: async () => {
                    const classSelect = document.getElementById('add-page-class');
                    const nameInput = document.getElementById('add-page-name');
                    if (!classSelect || !nameInput) {
                        throw new Error('Form elements not found');
                    }
                    const selectedClassValue = classSelect.value;
                    const nameValue = nameInput.value.trim();
                    // Validate class selection
                    if (!selectedClassValue) {
                        throw new Error('Please select a page class');
                    }
                    // Find the selected class info to check allow_null_names
                    const selectedClassInfo = allowedClasses.find(c => c.class_name === selectedClassValue);
                    if (!selectedClassInfo) {
                        throw new Error('Invalid class selection');
                    }
                    // Validate name based on allow_null_names
                    if (!selectedClassInfo.allow_null_names && !nameValue) {
                        throw new Error('A name is required for this page class');
                    }
                    // Build params for add_page MCP call
                    const params = {
                        target_page: pageId,
                        class: selectedClassValue
                    };
                    // Only include name if provided (even if allow_null_names is true, user might want to specify)
                    if (nameValue) {
                        params.name = nameValue;
                    }
                    try {
                        const result = await rpc.call('add_page', params);
                        const newPageName = result.data?.page?.name || nameValue || selectedClassValue;
                        const newPageId = result.data?.page?.id;
                        // Determine redirect URL using standard format
                        const redirectUrl = this.getPageUrl(newPageId);
                        return {
                            success: true,
                            _showMessage: `Page "${this.escapeHtml(newPageName)}" has been created successfully.`,
                            _autoFade: true,
                            _redirectAfterFade: redirectUrl,
                            debug: result.debug
                        };
                    }
                    catch (error) {
                        throw error;
                    }
                }
            });
            // Set up class change handler to update name placeholder
            setTimeout(() => {
                const classSelect = document.getElementById('add-page-class');
                const nameInput = document.getElementById('add-page-name');
                if (classSelect && nameInput && allowedClasses.length > 1) {
                    classSelect.addEventListener('change', () => {
                        const selectedOption = classSelect.options[classSelect.selectedIndex];
                        const allowNull = selectedOption.getAttribute('data-allow-null') === 'true';
                        nameInput.placeholder = allowNull ? 'Optional' : 'Required';
                    });
                }
                // Focus the appropriate field
                if (allowedClasses.length > 1 && classSelect) {
                    classSelect.focus();
                }
                else if (nameInput) {
                    nameInput.focus();
                }
            }, 100);
        }
        catch (error) {
            rpc.showError('add_page', error);
        }
    }
    /**
     * Handler for move_page: Move page to new parent (smoke test with browser)
     */
    async move_page(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const { Browser } = await import('./browser.js');
            const browser = new Browser({
                mode: 'page',
                initialPageId: pageId,
                onSubmit: async (result) => {
                    // Smoke test: just show success message
                    const selectedPageId = result;
                    const targetId = Array.isArray(selectedPageId) ? selectedPageId[0] : selectedPageId;
                    console.log(`Would move page ${pageId} to parent ${targetId}`);
                    // In real implementation, would call rpc.call('move_page', { page_id: pageId, target_page: targetId })
                }
            });
            await browser.show();
        }
        catch (error) {
            rpc.showError('move_page', error);
        }
    }
}

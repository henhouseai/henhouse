/**
 * doc_section_page_data - Handles document section pages.
 * Metadata fields (section_level, sort_order, section_type) are automatically discovered by base class.
 * For now, simple extension with no custom handlers.
 */
import { PageData } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';
export class doc_section_page_data extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for doc_section specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings(), // Include base page mappings (name, text)
            // DocSection specific mappings
            {
                fields: ['section_level'],
                apiTool: 'modify_doc_section_info',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    section_level: parseInt(values['section_level']) || 2
                })
            },
            {
                fields: ['sort_order'],
                apiTool: 'modify_doc_section_info',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    sort_order: parseInt(values['sort_order']) || 0
                })
            },
            {
                fields: ['section_type'],
                apiTool: 'modify_doc_section_info',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    section_type: values['section_type']
                })
            }
        ];
    }
    /**
     * Handler for doc_section_combo: Edit section_level, sort_order, and section_type
     */
    async doc_section_combo(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            // Get editable fields
            const currentSectionLevel = this.getField('section_level', 'form') || '';
            const currentSortOrder = this.getField('sort_order', 'form') || '';
            const currentSectionType = this.getField('section_type', 'form') || '';
            // Get read-only fields
            const pageIdValue = this.getField('id') || '';
            const pageClass = this.getField('class') || '';
            const pageLink = this.getField('link') || '';
            const lastModified = this.getField('last_modified') || '';
            const username = this.getField('username') || '';
            const path = this.getField('path') || [];
            const pathStr = Array.isArray(path) ? path.map((p) => p.name).filter(Boolean).join(' / ') : '';
            // Create form HTML with editable and read-only fields
            const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Section Level:</label>
            <select id="page-field-section_level" class="overlay-form-input">
              <option value="1" ${currentSectionLevel === '1' ? 'selected' : ''}>1 (#)</option>
              <option value="2" ${currentSectionLevel === '2' ? 'selected' : ''}>2 (##)</option>
              <option value="3" ${currentSectionLevel === '3' ? 'selected' : ''}>3 (###)</option>
              <option value="4" ${currentSectionLevel === '4' ? 'selected' : ''}>4 (####)</option>
              <option value="5" ${currentSectionLevel === '5' ? 'selected' : ''}>5 (#####)</option>
              <option value="6" ${currentSectionLevel === '6' ? 'selected' : ''}>6 (######)</option>
            </select>
          </div>
          <div class="overlay-form-group">
            <label>Sort Order:</label>
            <input type="number" id="page-field-sort_order" value="${this.escapeHtml(currentSortOrder)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Section Type:</label>
            <select id="page-field-section_type" class="overlay-form-input">
              <option value="heading" ${currentSectionType === 'heading' ? 'selected' : ''}>Heading</option>
              <option value="content" ${currentSectionType === 'content' ? 'selected' : ''}>Content</option>
              <option value="code" ${currentSectionType === 'code' ? 'selected' : ''}>Code</option>
              <option value="list" ${currentSectionType === 'list' ? 'selected' : ''}>List</option>
              <option value="table" ${currentSectionType === 'table' ? 'selected' : ''}>Table</option>
            </select>
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
                header: 'Edit Doc Section',
                content: [editableFieldsHtml, readOnlyFieldsHtml],
                contentHeaders: ['Editable Fields', 'Read-Only Fields (for display only)'],
                mode: 'fixed',
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
                        // Update section_level, sort_order, and section_type in internal PageData if they were changed
                        const sectionLevelOp = result.operations?.find((op) => op.fields?.includes('section_level'));
                        if (sectionLevelOp && sectionLevelOp.success && sectionLevelOp.result) {
                            const parsedResult = rpc.extractAPIData(sectionLevelOp.result);
                            const resultPageData = parsedResult?.page || parsedResult;
                            const newSectionLevel = resultPageData?.section_level;
                            if (newSectionLevel !== undefined) {
                                this.updateFieldValue('section_level', newSectionLevel);
                            }
                        }
                        const sortOrderOp = result.operations?.find((op) => op.fields?.includes('sort_order'));
                        if (sortOrderOp && sortOrderOp.success && sortOrderOp.result) {
                            const parsedResult = rpc.extractAPIData(sortOrderOp.result);
                            const resultPageData = parsedResult?.page || parsedResult;
                            const newSortOrder = resultPageData?.sort_order;
                            if (newSortOrder !== undefined) {
                                this.updateFieldValue('sort_order', newSortOrder);
                            }
                        }
                        const sectionTypeOp = result.operations?.find((op) => op.fields?.includes('section_type'));
                        if (sectionTypeOp && sectionTypeOp.success && sectionTypeOp.result) {
                            const parsedResult = rpc.extractAPIData(sectionTypeOp.result);
                            const resultPageData = parsedResult?.page || parsedResult;
                            const newSectionType = resultPageData?.section_type;
                            if (newSectionType !== undefined) {
                                this.updateFieldValue('section_type', newSectionType);
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
            // Focus the section level input after overlay is shown
            setTimeout(() => {
                const select = document.getElementById('page-field-section_level');
                if (select) {
                    select.focus();
                }
            }, 100);
        }
        catch (error) {
            rpc.showError('doc_section_combo', error);
        }
    }
}

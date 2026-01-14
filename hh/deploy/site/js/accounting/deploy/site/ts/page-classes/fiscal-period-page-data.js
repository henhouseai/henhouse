/**
 * fiscal_period_page_data - Handles fiscal period pages with date range fields.
 * Dynamic fields are automatically discovered by base class.
 */
import { PageData } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';
export class fiscal_period_page_data extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for fiscal period specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings(), // Include base page mappings (name, text)
            // Fiscal period specific mappings - grouped operation
            {
                fields: ['startDate', 'endDate'],
                apiTool: 'modify_fiscal_period_info',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    startDate: values['startDate'] || '',
                    endDate: values['endDate'] || ''
                })
            }
        ];
    }
    /**
     * Handler for modify_fiscal_period_info app action.
     * Edit start date and end date together.
     */
    async modify_fiscal_period_info(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            const currentStartDate = this.getField('startDate', 'form') || '';
            const currentEndDate = this.getField('endDate', 'form') || '';
            // Get read-only fields
            const pageIdValue = this.getField('id') || '';
            const pageClass = this.getField('class') || '';
            const pageName = this.getField('name') || '';
            const lastModified = this.getField('last_modified') || '';
            // Create form HTML
            const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Start Date:</label>
            <input type="date" id="page-field-startDate" value="${this.escapeHtml(currentStartDate)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>End Date:</label>
            <input type="date" id="page-field-endDate" value="${this.escapeHtml(currentEndDate)}" class="overlay-form-input">
          </div>
      `;
            const readOnlyFieldsHtml = `
          <div class="overlay-form-grid">
            <div><strong>ID:</strong></div>
            <div>${this.escapeHtml(String(pageIdValue))}</div>
            <div><strong>Name:</strong></div>
            <div>${this.escapeHtml(pageName)}</div>
            <div><strong>Class:</strong></div>
            <div>${this.escapeHtml(pageClass)}</div>
            <div><strong>Last Modified:</strong></div>
            <div>${this.escapeHtml(lastModified)}</div>
          </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Edit Fiscal Period',
                content: [editableFieldsHtml, readOnlyFieldsHtml],
                contentHeaders: ['Editable Fields', 'Read-Only Fields'],
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
                        if ('startDate' in currentValues) {
                            this.updateFieldValue('startDate', currentValues['startDate'] || '');
                        }
                        if ('endDate' in currentValues) {
                            this.updateFieldValue('endDate', currentValues['endDate'] || '');
                        }
                        return {
                            success: true,
                            _showMessage: 'Fiscal period information updated successfully',
                            _autoFade: true,
                            debug: result.debug
                        };
                    }
                    else {
                        return { ...result };
                    }
                }
            });
        }
        catch (error) {
            rpc.showError('modify_fiscal_period_info', error);
        }
    }
}

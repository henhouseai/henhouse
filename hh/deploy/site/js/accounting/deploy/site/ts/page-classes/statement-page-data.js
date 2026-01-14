/**
 * statement_page_data - Handles statement pages with date and balance fields.
 * Dynamic fields are automatically discovered by base class.
 */
import { PageData } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';
export class statement_page_data extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for statement specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings(), // Include base page mappings (name, text)
            // Statement specific mappings - two grouped operations
            {
                fields: ['startDate', 'endDate', 'openingBalance', 'closingBalance'],
                apiTool: 'modify_statement_info',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    startDate: values['startDate'] || '',
                    endDate: values['endDate'] || '',
                    openingBalance: parseFloat(values['openingBalance']) || 0,
                    closingBalance: parseFloat(values['closingBalance']) || 0
                })
            },
            {
                fields: ['interestEarned', 'financeCharge'],
                apiTool: 'modify_finance_info',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    interestEarned: parseFloat(values['interestEarned']) || 0,
                    financeCharge: parseFloat(values['financeCharge']) || 0
                })
            }
        ];
    }
    /**
     * Handler for modify_statement_info app action.
     * Edit start date, end date, opening balance, and closing balance together.
     */
    async modify_statement_info(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            const currentStartDate = this.getField('startDate', 'form') || '';
            const currentEndDate = this.getField('endDate', 'form') || '';
            const currentOpeningBalance = this.getField('openingBalance', 'form') || 0;
            const currentClosingBalance = this.getField('closingBalance', 'form') || 0;
            // Get read-only fields
            const pageIdValue = this.getField('id') || '';
            const pageClass = this.getField('class') || '';
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
          <div class="overlay-form-group">
            <label>Opening Balance:</label>
            <input type="number" id="page-field-openingBalance" value="${currentOpeningBalance}" step="0.01" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Closing Balance:</label>
            <input type="number" id="page-field-closingBalance" value="${currentClosingBalance}" step="0.01" class="overlay-form-input">
          </div>
      `;
            const readOnlyFieldsHtml = `
          <div class="overlay-form-grid">
            <div><strong>ID:</strong></div>
            <div>${this.escapeHtml(String(pageIdValue))}</div>
            <div><strong>Class:</strong></div>
            <div>${this.escapeHtml(pageClass)}</div>
            <div><strong>Last Modified:</strong></div>
            <div>${this.escapeHtml(lastModified)}</div>
          </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Edit Statement Info',
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
                        if ('openingBalance' in currentValues) {
                            this.updateFieldValue('openingBalance', parseFloat(currentValues['openingBalance']) || 0);
                        }
                        if ('closingBalance' in currentValues) {
                            this.updateFieldValue('closingBalance', parseFloat(currentValues['closingBalance']) || 0);
                        }
                        return {
                            success: true,
                            _showMessage: 'Statement information updated successfully',
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
            rpc.showError('modify_statement_info', error);
        }
    }
    /**
     * Handler for modify_finance_info app action.
     * Edit interest earned and finance charge together.
     */
    async modify_finance_info(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            const currentInterestEarned = this.getField('interestEarned', 'form') || 0;
            const currentFinanceCharge = this.getField('financeCharge', 'form') || 0;
            // Get read-only fields
            const pageIdValue = this.getField('id') || '';
            const pageClass = this.getField('class') || '';
            const lastModified = this.getField('last_modified') || '';
            // Create form HTML
            const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Interest Earned:</label>
            <input type="number" id="page-field-interestEarned" value="${currentInterestEarned}" step="0.01" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Finance Charge:</label>
            <input type="number" id="page-field-financeCharge" value="${currentFinanceCharge}" step="0.01" class="overlay-form-input">
          </div>
      `;
            const readOnlyFieldsHtml = `
          <div class="overlay-form-grid">
            <div><strong>ID:</strong></div>
            <div>${this.escapeHtml(String(pageIdValue))}</div>
            <div><strong>Class:</strong></div>
            <div>${this.escapeHtml(pageClass)}</div>
            <div><strong>Last Modified:</strong></div>
            <div>${this.escapeHtml(lastModified)}</div>
          </div>
      `;
            OverlayManager.getInstance().show({
                header: 'Edit Finance Info',
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
                        if ('interestEarned' in currentValues) {
                            this.updateFieldValue('interestEarned', parseFloat(currentValues['interestEarned']) || 0);
                        }
                        if ('financeCharge' in currentValues) {
                            this.updateFieldValue('financeCharge', parseFloat(currentValues['financeCharge']) || 0);
                        }
                        return {
                            success: true,
                            _showMessage: 'Finance information updated successfully',
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
            rpc.showError('modify_finance_info', error);
        }
    }
}

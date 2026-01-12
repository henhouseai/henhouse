/**
 * invoice_page_data - Handles invoice pages with reference and total fields.
 * Dynamic fields are automatically discovered by base class.
 */
import { PageData } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';
export class invoice_page_data extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for invoice specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings(), // Include base page mappings (name, text)
            // Invoice specific mappings - two grouped operations
            {
                fields: ['date', 'reference'],
                mcpTool: 'modify_invoice_info',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    date: values['date'] || '',
                    reference: values['reference'] || null
                })
            },
            {
                fields: ['total', 'tax', 'shipping'],
                mcpTool: 'modify_invoice_cost_breakdown',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    total: parseFloat(values['total']) || 0,
                    tax: parseFloat(values['tax']) || 0,
                    shipping: parseFloat(values['shipping']) || 0
                })
            }
        ];
    }
    /**
     * Handler for modify_invoice_info app action.
     * Edit date and reference together.
     */
    async modify_invoice_info(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            const currentDate = this.getField('date', 'form') || '';
            const currentReference = this.getField('reference', 'form') || '';
            // Get read-only fields
            const pageIdValue = this.getField('id') || '';
            const pageClass = this.getField('class') || '';
            const lastModified = this.getField('last_modified') || '';
            // Create form HTML
            const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Date:</label>
            <input type="date" id="page-field-date" value="${this.escapeHtml(currentDate)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Reference:</label>
            <input type="text" id="page-field-reference" value="${this.escapeHtml(currentReference)}" class="overlay-form-input">
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
                header: 'Edit Invoice Info',
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
                        if ('date' in currentValues) {
                            this.updateFieldValue('date', currentValues['date'] || '');
                        }
                        if ('reference' in currentValues) {
                            this.updateFieldValue('reference', currentValues['reference'] || null);
                        }
                        return {
                            success: true,
                            _showMessage: 'Invoice information updated successfully',
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
            rpc.showError('modify_invoice_info', error);
        }
    }
    /**
     * Handler for modify_invoice_cost_breakdown app action.
     * Edit total, tax, and shipping together.
     */
    async modify_invoice_cost_breakdown(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const pageManager = PageManager.getInstance();
            const currentTotal = this.getField('total', 'form') || 0;
            const currentTax = this.getField('tax', 'form') || 0;
            const currentShipping = this.getField('shipping', 'form') || 0;
            // Get read-only fields
            const pageIdValue = this.getField('id') || '';
            const pageClass = this.getField('class') || '';
            const lastModified = this.getField('last_modified') || '';
            // Create form HTML
            const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Total:</label>
            <input type="number" id="page-field-total" value="${currentTotal}" step="0.01" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Tax:</label>
            <input type="number" id="page-field-tax" value="${currentTax}" step="0.01" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Shipping:</label>
            <input type="number" id="page-field-shipping" value="${currentShipping}" step="0.01" class="overlay-form-input">
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
                header: 'Edit Cost Breakdown',
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
                        if ('total' in currentValues) {
                            this.updateFieldValue('total', parseFloat(currentValues['total']) || 0);
                        }
                        if ('tax' in currentValues) {
                            this.updateFieldValue('tax', parseFloat(currentValues['tax']) || 0);
                        }
                        if ('shipping' in currentValues) {
                            this.updateFieldValue('shipping', parseFloat(currentValues['shipping']) || 0);
                        }
                        return {
                            success: true,
                            _showMessage: 'Cost breakdown updated successfully',
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
            rpc.showError('modify_invoice_cost_breakdown', error);
        }
    }
}

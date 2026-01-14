/**
 * sale_page_data - Handles sale pages with customer and total fields.
 * Dynamic fields are automatically discovered by base class.
 */

import { PageData, GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';

export class sale_page_data extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for sale specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings(), // Include base page mappings (name, text)
      // Sale specific mappings - three grouped operations
      {
        fields: ['date', 'receiptNum', 'saleType'],
        apiTool: 'modify_sale_info',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          date: values['date'] || '',
          receiptNum: values['receiptNum'] || null,
          saleType: values['saleType'] || 'retail'
        })
      },
      {
        fields: ['customerName', 'address', 'city', 'state', 'postalCode', 'country'],
        apiTool: 'modify_customer_info',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          customerName: values['customerName'] || null,
          address: values['address'] || null,
          city: values['city'] || null,
          state: values['state'] || null,
          postalCode: values['postalCode'] || null,
          country: values['country'] || null
        })
      },
      {
        fields: ['total', 'tax', 'shipping'],
        apiTool: 'modify_sale_cost_breakdown',
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
   * Handler for modify_sale_info app action.
   * Edit date, receipt number, and sale type together.
   */
  async modify_sale_info(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();

      const currentDate = this.getField('date', 'form') || '';
      const currentReceiptNum = this.getField('receiptNum', 'form') || '';
      const currentSaleType = this.getField('saleType', 'form') || 'retail';
      const allowedTypes = ['retail', 'wholesale', 'consignment', 'royalty', 'service', 'advance', 'account', 'refund', 'other', 'capital-gain', 'gift', 'sublet', 'employment', 'asset sale'];

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
            <label>Receipt Number:</label>
            <input type="text" id="page-field-receiptNum" value="${this.escapeHtml(currentReceiptNum)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Sale Type:</label>
            <select id="page-field-saleType" class="overlay-form-select">
              ${allowedTypes.map(type => `<option value="${type}" ${currentSaleType === type ? 'selected' : ''}>${this.escapeHtml(type)}</option>`).join('')}
            </select>
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
        header: 'Edit Sale Info',
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
          const editableFields = changedFields.filter((field: string) => field !== 'class');
          
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
            if ('receiptNum' in currentValues) {
              this.updateFieldValue('receiptNum', currentValues['receiptNum'] || null);
            }
            if ('saleType' in currentValues) {
              this.updateFieldValue('saleType', currentValues['saleType'] || 'retail');
            }
            
            return {
              success: true,
              _showMessage: 'Sale information updated successfully',
              _autoFade: true,
              debug: result.debug
            };
          } else {
            return { ...result };
          }
        }
      });
    } catch (error) {
      rpc.showError('modify_sale_info', error);
    }
  }

  /**
   * Handler for modify_customer_info app action.
   * Edit customer information fields together.
   */
  async modify_customer_info(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();

      const currentCustomerName = this.getField('customerName', 'form') || '';
      const currentAddress = this.getField('address', 'form') || '';
      const currentCity = this.getField('city', 'form') || '';
      const currentState = this.getField('state', 'form') || '';
      const currentPostalCode = this.getField('postalCode', 'form') || '';
      const currentCountry = this.getField('country', 'form') || '';

      // Get read-only fields
      const pageIdValue = this.getField('id') || '';
      const pageClass = this.getField('class') || '';
      const lastModified = this.getField('last_modified') || '';

      // Create form HTML
      const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Customer Name:</label>
            <input type="text" id="page-field-customerName" value="${this.escapeHtml(currentCustomerName)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Address:</label>
            <input type="text" id="page-field-address" value="${this.escapeHtml(currentAddress)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>City:</label>
            <input type="text" id="page-field-city" value="${this.escapeHtml(currentCity)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>State:</label>
            <input type="text" id="page-field-state" value="${this.escapeHtml(currentState)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Postal Code:</label>
            <input type="text" id="page-field-postalCode" value="${this.escapeHtml(currentPostalCode)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Country:</label>
            <input type="text" id="page-field-country" value="${this.escapeHtml(currentCountry)}" class="overlay-form-input">
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
        header: 'Edit Customer Info',
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
          const editableFields = changedFields.filter((field: string) => field !== 'class');
          
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
            if ('customerName' in currentValues) {
              this.updateFieldValue('customerName', currentValues['customerName'] || null);
            }
            if ('address' in currentValues) {
              this.updateFieldValue('address', currentValues['address'] || null);
            }
            if ('city' in currentValues) {
              this.updateFieldValue('city', currentValues['city'] || null);
            }
            if ('state' in currentValues) {
              this.updateFieldValue('state', currentValues['state'] || null);
            }
            if ('postalCode' in currentValues) {
              this.updateFieldValue('postalCode', currentValues['postalCode'] || null);
            }
            if ('country' in currentValues) {
              this.updateFieldValue('country', currentValues['country'] || null);
            }
            
            return {
              success: true,
              _showMessage: 'Customer information updated successfully',
              _autoFade: true,
              debug: result.debug
            };
          } else {
            return { ...result };
          }
        }
      });
    } catch (error) {
      rpc.showError('modify_customer_info', error);
    }
  }

  /**
   * Handler for modify_sale_cost_breakdown app action.
   * Edit total, tax, and shipping together.
   */
  async modify_sale_cost_breakdown(rpc: any): Promise<void> {
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
          const editableFields = changedFields.filter((field: string) => field !== 'class');
          
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
          } else {
            return { ...result };
          }
        }
      });
    } catch (error) {
      rpc.showError('modify_sale_cost_breakdown', error);
    }
  }
}


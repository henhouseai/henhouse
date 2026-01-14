/**
 * transfer_page_data - Handles transfer pages with amount, date, fee, and transferTo fields.
 * Dynamic fields are automatically discovered by base class.
 */

import { PageData, GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';

export class transfer_page_data extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for transfer specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings(), // Include base page mappings (name, text)
      // Transfer specific mappings - two separate operations
      {
        fields: ['date', 'amount', 'modifier', 'fee'],
        apiTool: 'modify_transfer_info',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          date: values['date'] || '',
          amount: parseFloat(values['amount']) || 0,
          modifier: parseFloat(values['modifier']) || 0,
          fee: parseFloat(values['fee']) || 0
        })
      },
      {
        fields: ['transferTo'],
        apiTool: 'modify_target_info',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          transfer_to: values['transferTo'] || null
        })
      }
    ];
  }

  /**
   * Handler for modify_transfer_info app action.
   * Edit date, amount, modifier, and fee together.
   */
  async modify_transfer_info(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();

      const currentDate = this.getField('date', 'form') || '';
      const currentAmount = this.getField('amount', 'form') || 0;
      const currentModifier = this.getField('modifier', 'form') || 0;
      const currentFee = this.getField('fee', 'form') || 0;

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
            <label>Amount:</label>
            <input type="number" id="page-field-amount" value="${currentAmount}" step="0.01" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Modifier:</label>
            <input type="number" id="page-field-modifier" value="${currentModifier}" step="0.01" class="overlay-form-input">
            <div class="overlay-form-help">If non-zero, amount will be adjusted by this value</div>
          </div>
          <div class="overlay-form-group">
            <label>Fee:</label>
            <input type="number" id="page-field-fee" value="${currentFee}" step="0.01" class="overlay-form-input">
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
        header: 'Edit Transfer Info',
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
            if ('amount' in currentValues) {
              this.updateFieldValue('amount', parseFloat(currentValues['amount']) || 0);
            }
            if ('fee' in currentValues) {
              this.updateFieldValue('fee', parseFloat(currentValues['fee']) || 0);
            }
            
            return {
              success: true,
              _showMessage: 'Transfer information updated successfully',
              _autoFade: true,
              debug: result.debug
            };
          } else {
            return { ...result };
          }
        }
      });
    } catch (error) {
      rpc.showError('modify_transfer_info', error);
    }
  }

  /**
   * Handler for modify_target_info app action.
   * Edit transfer target page ID.
   */
  async modify_target_info(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();

      const currentTransferTo = this.getField('transferTo', 'form') || null;

      // Get read-only fields
      const pageIdValue = this.getField('id') || '';
      const pageClass = this.getField('class') || '';
      const lastModified = this.getField('last_modified') || '';

      // Create form HTML
      const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Transfer To (Page ID):</label>
            <input type="number" id="page-field-transferTo" value="${currentTransferTo || ''}" class="overlay-form-input" placeholder="Leave empty to clear">
            <div class="overlay-form-help">Enter the page ID of the target statement, sale, or invoice. Leave empty to clear.</div>
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
        header: 'Edit Transfer Target',
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
          
          // Handle transferTo - convert empty string to null
          if ('transferTo' in currentValues) {
            const transferToValue = currentValues['transferTo'];
            if (transferToValue === '' || transferToValue === null || transferToValue === undefined) {
              currentValues['transferTo'] = null;
            } else {
              currentValues['transferTo'] = parseInt(transferToValue);
            }
          }
          
          const result = await this.processOperationsIncrementally(rpc, optimalMappings, currentValues, pageId);
          const allSucceeded = result.success && result.errors.length === 0;

          if (allSucceeded) {
            if ('transferTo' in currentValues) {
              this.updateFieldValue('transferTo', currentValues['transferTo']);
            }
            
            return {
              success: true,
              _showMessage: 'Transfer target updated successfully',
              _autoFade: true,
              debug: result.debug
            };
          } else {
            return { ...result };
          }
        }
      });
    } catch (error) {
      rpc.showError('modify_target_info', error);
    }
  }
}


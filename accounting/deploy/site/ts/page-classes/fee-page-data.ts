/**
 * fee_page_data - Handles fee pages with date and fee amount fields.
 * Dynamic fields are automatically discovered by base class.
 */

import { PageData, GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';

export class fee_page_data extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for fee specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings(), // Include base page mappings (name, text)
      // Fee specific mappings - grouped operation
      {
        fields: ['fee', 'date'],
        apiTool: 'modify_fee_info',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          fee: parseFloat(values['fee']) || 0,
          date: values['date'] || ''
        })
      }
    ];
  }

  /**
   * Handler for modify_fee_info app action.
   * Edit fee amount and date together.
   */
  async modify_fee_info(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();

      // Get editable fields
      const currentFee = this.getField('fee', 'form') || 0;
      const currentDate = this.getField('date', 'form') || '';

      // Get read-only fields
      const pageIdValue = this.getField('id') || '';
      const pageClass = this.getField('class') || '';
      const lastModified = this.getField('last_modified') || '';
      const username = this.getField('username') || '';

      // Create form HTML
      const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Fee Amount:</label>
            <input type="number" id="page-field-fee" value="${currentFee}" step="0.01" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Date:</label>
            <input type="date" id="page-field-date" value="${this.escapeHtml(currentDate)}" class="overlay-form-input">
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
            <div><strong>Username:</strong></div>
            <div>${this.escapeHtml(username)}</div>
          </div>
      `;

      OverlayManager.getInstance().show({
        header: 'Edit Fee',
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
            // Update internal data
            if ('fee' in currentValues) {
              this.updateFieldValue('fee', parseFloat(currentValues['fee']) || 0);
            }
            if ('date' in currentValues) {
              this.updateFieldValue('date', currentValues['date'] || '');
            }
            
            return {
              success: true,
              _showMessage: 'Fee information updated successfully',
              _autoFade: true,
              debug: result.debug
            };
          } else {
            return { ...result };
          }
        }
      });
    } catch (error) {
      rpc.showError('modify_fee_info', error);
    }
  }
}


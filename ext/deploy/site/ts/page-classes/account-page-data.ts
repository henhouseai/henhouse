/**
 * account_page_data - Handles account pages with type field.
 * Dynamic fields (type) are automatically discovered by base class.
 */

import { PageData, GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';

export class account_page_data extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for account specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings(), // Include base page mappings (name, text)
      // Account specific mappings
      {
        fields: ['type'],
        mcpTool: 'modify_account_type',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          type: values['type']
        })
      }
    ];
  }

  /**
   * Handler for modify_account_type app action.
   * Edit account type.
   */
  async modify_account_type(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();
      
      const currentType = this.getField('type', 'form') || 'cash';
      const allowedTypes = ['cash', 'checking', 'savings', 'online', 'credit', 'loan', 'service', 'person', 'open order', 'lease', 'sublet', 'house fund'];

      // Get read-only fields
      const pageIdValue = this.getField('id') || '';
      const pageClass = this.getField('class') || '';
      const pageName = this.getField('name') || '';
      const lastModified = this.getField('last_modified') || '';

      // Create form HTML with dropdown
      const formHtml = `
          <div class="overlay-form-group">
            <label>Account Type:</label>
            <select id="page-field-type" class="overlay-form-select">
              ${allowedTypes.map(type => `<option value="${type}" ${currentType === type ? 'selected' : ''}>${this.escapeHtml(type)}</option>`).join('')}
            </select>
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
        header: 'Edit Account Type',
        content: [formHtml, readOnlyFieldsHtml],
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
            if ('type' in currentValues) {
              this.updateFieldValue('type', currentValues['type']);
            }
            
            return {
              success: true,
              _showMessage: 'Account type updated successfully',
              _autoFade: true,
              debug: result.debug
            };
          } else {
            return { ...result };
          }
        }
      });
    } catch (error) {
      rpc.showError('modify_account_type', error);
    }
  }
}


/**
 * WorkPageData - Base class for work pages (work docket, ask, task, step).
 * Provides shared functionality for status, meta, and sort_order fields.
 * This is an abstract base class - derived classes should extend this.
 */

import { PageData, GetPageResponse, FieldMapping } from './page-data.js';
import { PageManager } from './page-manager.js';
import { OverlayManager } from './overlay-manager.js';

export class WorkPageData extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for work page fields.
   * Derived classes should call super.getFieldMappings() and add their own.
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings(), // Include base page mappings (name, text)
      // Work page shared mappings
      {
        fields: ['status'],
        mcpTool: 'modify_work_status',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          status: values['status']
        })
      }
    ];
  }

  /**
   * Handler for modify_work_status app action.
   * Shows a form with a dropdown to select the new status.
   */
  async modify_work_status(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();
      
      // Request 'status' field with 'form' context to register it for editing
      const currentStatus = this.getField('status', 'form') || 'todo';

      // Create form HTML with dropdown select box
      const formHtml = `
          <div class="overlay-form-group">
            <label>Status:</label>
            <select id="page-field-status" class="overlay-form-select">
              <option value="todo" ${currentStatus === 'todo' ? 'selected' : ''}>Todo</option>
              <option value="doing" ${currentStatus === 'doing' ? 'selected' : ''}>Doing</option>
              <option value="review" ${currentStatus === 'review' ? 'selected' : ''}>Review</option>
              <option value="done" ${currentStatus === 'done' ? 'selected' : ''}>Done</option>
            </select>
          </div>
      `;

      OverlayManager.getInstance().show({
        header: 'Modify Work Status',
        content: [formHtml],
        contentHeaders: [''],
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
            if ('status' in currentValues) {
              this.updateFieldValue('status', currentValues['status']);
            }
            
            return {
              success: true,
              _showMessage: 'Status updated successfully',
              _autoFade: true,
              debug: result.debug
            };
          } else {
            // Errors already shown in overlay
            return {
              success: false,
              debug: result.debug
            };
          }
        }
      });
    } catch (error) {
      rpc.showError('modify_work_status', error);
    }
  }
}


/**
 * work_page_data - Base class for work pages (work docket, ask, task, step).
 * Provides shared functionality for status, meta, and sort_order fields.
 * This is an abstract base class - derived classes should extend this.
 */

import { PageData, GetPageResponse, FieldMapping } from '../page-data.js';
import { PageManager } from '../page-manager.js';
import { OverlayManager } from '../overlay/overlay-manager.js';

export class work_page_data extends PageData {
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
      },
      {
        fields: ['sort_order'],
        mcpTool: 'modify_work_sort_order',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          sort_order: parseInt(values['sort_order']) || 0
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

  /**
   * Helper method to build key-value table HTML for metadata editing.
   */
  private buildKeyValueTableHtml(fieldName: string, currentData: string, tableId: string): string {
    // Parse current data JSON
    let dataObj: { [key: string]: any } = {};
    try {
      if (currentData && currentData.trim()) {
        dataObj = JSON.parse(currentData);
      }
    } catch (e) {
      // Invalid JSON, start with empty object
      dataObj = {};
    }

    // Convert to array of key-value pairs for table display
    const pairs: Array<{ key: string; value: string }> = Object.keys(dataObj).map(key => ({
      key,
      value: typeof dataObj[key] === 'string' ? dataObj[key] : JSON.stringify(dataObj[key])
    }));

    // If empty, start with one empty row
    if (pairs.length === 0) {
      pairs.push({ key: '', value: '' });
    }

    // Build table HTML
    let tableHtml = `
      <div class="overlay-form-group">
        <label>${fieldName} Key-Value Pairs:</label>
        <table id="${tableId}" class="meta-key-value-table" style="width: 100%; border-collapse: collapse; margin-top: 10px;">
          <thead>
            <tr>
              <th style="width: 40%; padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">Key</th>
              <th style="width: 55%; padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">Value</th>
              <th style="width: 5%; padding: 8px; border: 1px solid #ddd; background: #f5f5f5;"></th>
            </tr>
          </thead>
          <tbody id="${tableId}-tbody">
    `;

    // Add rows for existing pairs
    pairs.forEach((pair, index) => {
      const rowId = `${tableId}-row-${index}`;
      tableHtml += `
        <tr id="${rowId}">
          <td style="padding: 4px; border: 1px solid #ddd;">
            <input type="text" class="meta-key-input" value="${this.escapeHtml(pair.key)}" 
                   style="width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;" 
                   placeholder="Key (no spaces, JSON valid)">
          </td>
          <td style="padding: 4px; border: 1px solid #ddd;">
            <input type="text" class="meta-value-input" value="${this.escapeHtml(pair.value)}" 
                   style="width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;" 
                   placeholder="Value (can be JSON string)">
          </td>
          <td style="padding: 4px; border: 1px solid #ddd; text-align: center;">
            <button type="button" class="meta-remove-btn" style="background: #dc3545; color: white; border: none; padding: 4px 8px; cursor: pointer; border-radius: 3px;">×</button>
          </td>
        </tr>
      `;
    });

    tableHtml += `
          </tbody>
        </table>
        <button type="button" id="${tableId}-add-btn" style="margin-top: 10px; padding: 6px 12px; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 3px;">Add Row</button>
        <div class="overlay-form-help" style="margin-top: 10px;">Keys must be JSON valid (no spaces). Values can be strings or JSON.</div>
      </div>
    `;

    return tableHtml;
  }

  /**
   * Helper method to set up table event handlers (add row, remove row).
   */
  private setupTableHandlers(tableId: string): void {
    setTimeout(() => {
      const tbody = document.querySelector(`#${tableId}-tbody`) as HTMLElement;
      const addBtn = document.querySelector(`#${tableId}-add-btn`) as HTMLElement;
      
      if (!tbody || !addBtn) return;

      // Add row button handler
      addBtn.addEventListener('click', () => {
        const newRow = document.createElement('tr');
        newRow.innerHTML = `
          <td style="padding: 4px; border: 1px solid #ddd;">
            <input type="text" class="meta-key-input" value="" 
                   style="width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;" 
                   placeholder="Key (no spaces, JSON valid)">
          </td>
          <td style="padding: 4px; border: 1px solid #ddd;">
            <input type="text" class="meta-value-input" value="" 
                   style="width: 100%; padding: 4px; border: 1px solid #ccc; box-sizing: border-box;" 
                   placeholder="Value (can be JSON string)">
          </td>
          <td style="padding: 4px; border: 1px solid #ddd; text-align: center;">
            <button type="button" class="meta-remove-btn" style="background: #dc3545; color: white; border: none; padding: 4px 8px; cursor: pointer; border-radius: 3px;">×</button>
          </td>
        `;
        tbody.appendChild(newRow);
        // Attach remove handler to new buttons
        attachRemoveHandlers();
      });

      // Remove button handlers
      const attachRemoveHandlers = () => {
        const removeBtns = tbody.querySelectorAll('.meta-remove-btn');
        removeBtns.forEach(btn => {
          btn.addEventListener('click', (e) => {
            const row = (e.target as HTMLElement).closest('tr');
            if (row && tbody.children.length > 1) {
              row.remove();
            } else if (row) {
              // If last row, just clear it
              const keyInput = row.querySelector('.meta-key-input') as HTMLInputElement;
              const valueInput = row.querySelector('.meta-value-input') as HTMLInputElement;
              if (keyInput) keyInput.value = '';
              if (valueInput) valueInput.value = '';
            }
          });
        });
      };
      attachRemoveHandlers();

    }, 100);
  }

  /**
   * Helper method to extract key-value pairs from table and call modify_work_meta.
   */
  private async submitKeyValueTable(rpc: any, pageId: number, tableId: string, field: string, action: string, fieldLabel: string): Promise<any> {
    // Extract all key-value pairs from table
    const tbody = document.querySelector(`#${tableId}-tbody`) as HTMLElement;
    if (!tbody) {
      throw new Error('Table not found');
    }

    const rows = Array.from(tbody.querySelectorAll('tr'));
    // Build as array of [key, value] pairs to preserve order
    const pairs: Array<[string, any]> = [];

    for (const row of rows) {
      const keyInput = row.querySelector('.meta-key-input') as HTMLInputElement;
      const valueInput = row.querySelector('.meta-value-input') as HTMLInputElement;
      
      if (keyInput && valueInput) {
        const key = keyInput.value.trim();
        const value = valueInput.value.trim();
        
        // Skip empty keys
        if (!key) continue;
        
        // Validate key (no spaces, JSON valid)
        if (key.includes(' ')) {
          throw new Error(`Key "${key}" contains spaces. Keys must be JSON valid (no spaces).`);
        }
        
        // Try to parse value as JSON, fall back to string
        let parsedValue: any;
        try {
          parsedValue = JSON.parse(value);
        } catch (e) {
          parsedValue = value;
        }
        
        pairs.push([key, parsedValue]);
      }
    }

    // Build object from pairs array to preserve insertion order
    const dataObj: { [key: string]: any } = {};
    for (const [key, value] of pairs) {
      dataObj[key] = value;
    }

    // Convert to JSON string
    const dataJson = JSON.stringify(dataObj);

    // Call MCP tool
    try {
      const params = {
        page_id: pageId,
        action: action,
        field: field,
        data: dataJson
      };
      const result = await rpc.call('modify_work_meta', params);

      // Check for debug data in result
      const hasDebugData = result?.debug && Array.isArray(result.debug.entries) && result.debug.entries.length > 0;
      
      // Show debug overlay if debug data is present
      if (hasDebugData) {
        const { handleRPCResponseWithDebug } = await import('../debug-helper.js');
        handleRPCResponseWithDebug(result, 'modify_work_meta', params);
      }
      
      if (result && result.success !== false) {
        return {
          success: true,
          _showMessage: `${fieldLabel} updated successfully`,
          _autoFade: !hasDebugData, // Disable auto-fade if debug data is present
          _redirectAfterFade: 'self', // Refresh page to show updated data
          _debugAlreadyShown: hasDebugData // Signal that debug overlay was already shown
        };
      } else {
        // Server returned error - include debug data if present
        throw new Error(result?.error || `Failed to update ${fieldLabel}`);
      }
    } catch (error: any) {
      // RPC errors may have debug data attached
      const hasDebugData = error?.debug && Array.isArray(error.debug.entries) && error.debug.entries.length > 0;
      
      // Show debug overlay for errors with debug data
      if (hasDebugData) {
        const { handleRPCResponseWithDebug } = await import('../debug-helper.js');
        handleRPCResponseWithDebug(error, 'modify_work_meta', {
          page_id: pageId,
          action: action,
          field: field,
          data: dataJson
        });
      }
      
      throw error;
    }
  }

  /**
   * Handler for metadata app action.
   * Shows a table form with key-value pairs for the meta field.
   */
  async metadata(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      // Fetch fresh page data to get current metadata
      const pageData = await rpc.getPage(pageId);
      const metadata = pageData.getRawData().metadata || {};
      const currentMeta = metadata.meta || {};
      const currentMetaJson = JSON.stringify(currentMeta);
      const tableId = 'meta-table-' + Date.now();
      const tableHtml = this.buildKeyValueTableHtml('Metadata', currentMetaJson, tableId);

      OverlayManager.getInstance().show({
        header: 'Edit Metadata',
        content: [tableHtml],
        contentHeaders: [''],
        mode: 'fixed',
        closable: true,
        submitLabel: 'Submit',
        cancelLabel: 'Cancel',
        onCancel: () => {
          // Cleanup
        },
        onUnmount: () => {
          // Cleanup
        },
        onSubmit: async () => {
          return await this.submitKeyValueTable(rpc, pageId, tableId, 'meta', 'set_all', 'Metadata');
        }
      });

      this.setupTableHandlers(tableId);
    } catch (error) {
      rpc.showError('metadata', error);
    }
  }

  /**
   * Handler for files_touched app action.
   * Shows a table form with key-value pairs for the files_touched field.
   */
  async files_touched(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      // Fetch fresh page data to get current metadata
      const pageData = await rpc.getPage(pageId);
      const metadata = pageData.getRawData().metadata || {};
      const currentFilesTouched = metadata.files_touched || {};
      const currentFilesTouchedJson = JSON.stringify(currentFilesTouched);
      const tableId = 'files-touched-table-' + Date.now();
      const tableHtml = this.buildKeyValueTableHtml('Files Touched', currentFilesTouchedJson, tableId);

      OverlayManager.getInstance().show({
        header: 'Edit Files Touched',
        content: [tableHtml],
        contentHeaders: [''],
        mode: 'fixed',
        closable: true,
        submitLabel: 'Submit',
        cancelLabel: 'Cancel',
        onCancel: () => {
          // Cleanup
        },
        onUnmount: () => {
          // Cleanup
        },
        onSubmit: async () => {
          return await this.submitKeyValueTable(rpc, pageId, tableId, 'files_touched', 'set_all', 'Files Touched');
        }
      });

      this.setupTableHandlers(tableId);
    } catch (error) {
      rpc.showError('files_touched', error);
    }
  }

  /**
   * Handler for deviations app action.
   * Shows a table form with key-value pairs for the deviations field.
   */
  async deviations(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      // Fetch fresh page data to get current metadata
      const pageData = await rpc.getPage(pageId);
      const metadata = pageData.getRawData().metadata || {};
      const currentDeviations = metadata.deviations || {};
      const currentDeviationsJson = JSON.stringify(currentDeviations);
      const tableId = 'deviations-table-' + Date.now();
      const tableHtml = this.buildKeyValueTableHtml('Deviations', currentDeviationsJson, tableId);

      OverlayManager.getInstance().show({
        header: 'Edit Deviations',
        content: [tableHtml],
        contentHeaders: [''],
        mode: 'fixed',
        closable: true,
        submitLabel: 'Submit',
        cancelLabel: 'Cancel',
        onCancel: () => {
          // Cleanup
        },
        onUnmount: () => {
          // Cleanup
        },
        onSubmit: async () => {
          return await this.submitKeyValueTable(rpc, pageId, tableId, 'deviations', 'set_all', 'Deviations');
        }
      });

      this.setupTableHandlers(tableId);
    } catch (error) {
      rpc.showError('deviations', error);
    }
  }

  /**
   * Handler for log_entry app action.
   * Shows a table form with key-value pairs for adding a log entry.
   */
  async log_entry(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      // Start with empty form for log entry
      const tableId = 'log-entry-table-' + Date.now();
      const tableHtml = this.buildKeyValueTableHtml('Log Entry', '{}', tableId);

      OverlayManager.getInstance().show({
        header: 'Add Log Entry',
        content: [tableHtml],
        contentHeaders: [''],
        mode: 'fixed',
        closable: true,
        submitLabel: 'Submit',
        cancelLabel: 'Cancel',
        onCancel: () => {
          // Cleanup
        },
        onUnmount: () => {
          // Cleanup
        },
        onSubmit: async () => {
          return await this.submitKeyValueTable(rpc, pageId, tableId, 'log', 'add', 'Log Entry');
        }
      });

      this.setupTableHandlers(tableId);
    } catch (error) {
      rpc.showError('log_entry', error);
    }
  }


  /**
   * Escape HTML to prevent XSS
   */
  protected escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Handler for modify_work_sort_order app action.
   * Shows a form with a text input to set the new sort_order position.
   */
  async modify_work_sort_order(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();
      
      // Request 'sort_order' field with 'form' context to register it for editing
      const currentSortOrder = this.getField('sort_order', 'form') || 0;

      // Create form HTML with text input for sort_order
      const formHtml = `
          <div class="overlay-form-group">
            <label>Sort Order:</label>
            <input type="number" id="page-field-sort_order" value="${currentSortOrder}" class="overlay-form-input" min="1">
            <div class="overlay-form-help">Enter the position (1-based). Values ≤ 0 go to beginning, values too high go to end.</div>
          </div>
      `;

      OverlayManager.getInstance().show({
        header: 'Modify Work Sort Order',
        content: [formHtml],
        contentHeaders: [''],
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
            if ('sort_order' in currentValues) {
              this.updateFieldValue('sort_order', currentValues['sort_order']);
            }
            
            return {
              success: true,
              _showMessage: 'Sort order updated successfully',
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
      rpc.showError('modify_work_sort_order', error);
    }
  }
}


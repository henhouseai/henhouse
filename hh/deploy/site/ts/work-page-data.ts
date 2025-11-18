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
   * Handler for modify_work_meta_set_all app action.
   * Shows a table form with key-value pairs that can be added, removed, and reordered.
   */
  async modify_work_meta_set_all(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      // Get current meta field
      const currentMeta = this.getField('meta', 'form') || '{}';
      
      // Parse current meta JSON
      let metaObj: { [key: string]: any } = {};
      try {
        if (currentMeta && currentMeta.trim()) {
          metaObj = JSON.parse(currentMeta);
        }
      } catch (e) {
        // Invalid JSON, start with empty object
        metaObj = {};
      }

      // Convert to array of key-value pairs for table display
      const pairs: Array<{ key: string; value: string }> = Object.keys(metaObj).map(key => ({
        key,
        value: typeof metaObj[key] === 'string' ? metaObj[key] : JSON.stringify(metaObj[key])
      }));

      // If empty, start with one empty row
      if (pairs.length === 0) {
        pairs.push({ key: '', value: '' });
      }

      // Build table HTML
      const tableId = 'meta-table-' + Date.now();
      let tableHtml = `
        <div class="overlay-form-group">
          <label>Meta Key-Value Pairs:</label>
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
          <tr id="${rowId}" draggable="true" style="cursor: move;">
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
          <div class="overlay-form-help" style="margin-top: 10px;">Keys must be JSON valid (no spaces). Values can be strings or JSON. Drag rows to reorder.</div>
        </div>
      `;

      OverlayManager.getInstance().show({
        header: 'Modify Meta',
        content: [tableHtml],
        contentHeaders: [''],
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
          const metaObj: { [key: string]: any } = {};
          for (const [key, value] of pairs) {
            metaObj[key] = value;
          }

          // Convert to JSON string (should preserve insertion order in modern JS)
          const metaJson = JSON.stringify(metaObj);

          // Call MCP tool
          try {
            const params = {
              page_id: pageId,
              meta: metaJson
            };
            const result = await rpc.call('modify_work_meta_set_all', params);

            // Check for debug data in result
            const hasDebugData = result?.debug && Array.isArray(result.debug.entries) && result.debug.entries.length > 0;
            
            // Show debug overlay if debug data is present
            if (hasDebugData) {
              const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
              handleRPCResponseWithDebug(result, 'modify_work_meta_set_all', params);
            }
            
            if (result && result.success !== false) {
              // Update internal data
              this.updateFieldValue('meta', metaJson);
              
              return {
                success: true,
                _showMessage: 'Meta updated successfully',
                _autoFade: !hasDebugData, // Disable auto-fade if debug data is present
                // Don't return debug here - we already showed it via handleRPCResponseWithDebug
              };
            } else {
              // Server returned error - include debug data if present
              throw new Error(result?.error || 'Failed to update meta');
            }
          } catch (error: any) {
            // RPC errors may have debug data attached
            const hasDebugData = error?.debug && Array.isArray(error.debug.entries) && error.debug.entries.length > 0;
            
            // Show debug overlay for errors with debug data
            if (hasDebugData) {
              const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
              handleRPCResponseWithDebug(error, 'modify_work_meta_set_all', {
                page_id: pageId,
                meta: metaJson
              });
            }
            
            throw error;
          }
        }
      });

      // Set up event handlers after overlay is shown
      setTimeout(() => {
        const tbody = document.querySelector(`#${tableId}-tbody`) as HTMLElement;
        const addBtn = document.querySelector(`#${tableId}-add-btn`) as HTMLElement;
        
        if (!tbody || !addBtn) return;

        // Add row button handler
        addBtn.addEventListener('click', () => {
          const newRow = document.createElement('tr');
          newRow.setAttribute('draggable', 'true');
          newRow.style.cursor = 'move';
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
          
          // Add another empty row below (auto-add feature)
          const autoRow = document.createElement('tr');
          autoRow.setAttribute('draggable', 'true');
          autoRow.style.cursor = 'move';
          autoRow.innerHTML = `
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
          tbody.appendChild(autoRow);
          
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

        // Drag and drop handlers
        let draggedRow: HTMLTableRowElement | null = null;
        
        tbody.querySelectorAll('tr').forEach(row => {
          row.addEventListener('dragstart', (e) => {
            draggedRow = row as HTMLTableRowElement;
            row.style.opacity = '0.5';
          });
          
          row.addEventListener('dragend', () => {
            if (draggedRow) {
              draggedRow.style.opacity = '1';
              draggedRow = null;
            }
          });
          
          row.addEventListener('dragover', (e) => {
            e.preventDefault();
            const target = e.target as HTMLElement;
            const targetRow = target.closest('tr');
            if (targetRow && targetRow !== draggedRow && draggedRow) {
              const rect = targetRow.getBoundingClientRect();
              const next = (e.clientY - rect.top) / (rect.bottom - rect.top) > 0.5;
              if (next) {
                tbody.insertBefore(draggedRow, targetRow.nextSibling);
              } else {
                tbody.insertBefore(draggedRow, targetRow);
              }
            }
          });
          
          row.addEventListener('drop', (e) => {
            e.preventDefault();
          });
        });
      }, 100);
    } catch (error) {
      rpc.showError('modify_work_meta_set_all', error);
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


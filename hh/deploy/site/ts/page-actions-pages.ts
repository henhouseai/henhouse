/**
 * PageActionsPages - Mixin for page management actions (add_page, move_page, delete_page)
 */

import { PageManager } from './page-manager.js';
import { OverlayManager } from './overlay/overlay-manager.js';
import type { PageData } from './page-data.js';

export class PageActionsPages {
  /**
   * Handler for delete_page: Delete a page with confirmation
   */
  async delete_page(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();
      
      const pageName = this.getField('name') || `Page ${pageId}`;
      const pageClass = this.getField('class') || 'page';
      
      // Create form HTML with confirmation checkbox using array-based content structure
      const formHtml = `
          <div class="overlay-warning-text">
            <p><strong>Warning:</strong> This will permanently delete the page and all its children.</p>
            <p>Page: <strong>${this.escapeHtml(pageName)}</strong> (ID: ${pageId}, Class: ${this.escapeHtml(pageClass)})</p>
          </div>
          <div class="overlay-form-group">
            <label class="overlay-label-inline">
              <input type="checkbox" id="page-delete-confirm" class="overlay-form-checkbox">
              <span>I confirm that I want to delete this page</span>
            </label>
          </div>
      `;

      OverlayManager.getInstance().show({
        header: 'Delete Page',
        content: [formHtml],
        contentHeaders: [''],
        closable: true,
        submitLabel: 'Delete',
        cancelLabel: 'Cancel',
        onCancel: () => {
          pageManager.clearFieldRegistry();
        },
        onUnmount: () => {
          pageManager.clearFieldRegistry();
        },
        onSubmit: async () => {
          const confirmCheckbox = document.getElementById('page-delete-confirm') as HTMLInputElement;
          if (!confirmCheckbox || !confirmCheckbox.checked) {
            throw new Error('You must confirm deletion by checking the confirmation box');
          }
          
          try {
            const result = await rpc.call('delete_page', {
              page_id: pageId,
              confirm: true
            });
            
            // Use standardized redirect pattern: 'parent' redirects to parent page
            return {
              debug: result.debug,
              success: true,
              _showMessage: `Page "${this.escapeHtml(pageName)}" has been deleted successfully.`,
              _autoFade: true,
              _redirectAfterFade: 'parent' // Standardized redirect pattern
            };
          } catch (error) {
            throw error;
          }
        }
      });

      // Focus the checkbox after overlay is shown
      setTimeout(() => {
        const checkbox = document.getElementById('page-delete-confirm') as HTMLInputElement;
        if (checkbox) {
          checkbox.focus();
        }
      }, 100);
    } catch (error) {
      rpc.showError('delete_page', error);
    }
  }

  /**
   * Handler for add_page: Create a new child page
   */
  async add_page(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      // Step 1: Get allowed child classes
      const classInfoResult = await rpc.call('get_add_page_class_info', { page_id: pageId });
      const classInfo = classInfoResult.data;
      
      if (!classInfo || !classInfo.allowed_classes || classInfo.allowed_classes.length === 0) {
        throw new Error('No allowed child classes found for this page');
      }

      const allowedClasses = classInfo.allowed_classes as Array<{
        class_name: string;
        allow_null_names: boolean;
        allow_duplicate_names: boolean;
        auto_link_name: boolean;
      }>;

      // Step 2: Build form HTML with class selector and name input
      let classSelectOptions = '';
      let selectedClass = '';
      let selectedClassAllowNull = true;

      if (allowedClasses.length === 1) {
        // Auto-select if only one option
        selectedClass = allowedClasses[0].class_name;
        selectedClassAllowNull = allowedClasses[0].allow_null_names;
        classSelectOptions = `<option value="${this.escapeHtml(selectedClass)}" selected>${this.escapeHtml(selectedClass)}</option>`;
      } else {
        // Multiple options - show dropdown
        classSelectOptions = '<option value="">-- Select a class --</option>';
        for (const classOption of allowedClasses) {
          classSelectOptions += `<option value="${this.escapeHtml(classOption.class_name)}" data-allow-null="${classOption.allow_null_names}">${this.escapeHtml(classOption.class_name)}</option>`;
        }
      }

      const formHtml = `
          <div class="overlay-form-group">
            <label>Page class:</label>
            <select id="add-page-class" class="overlay-form-select">
              ${classSelectOptions}
            </select>
          </div>
          <div class="overlay-form-group">
            <label>Page name:</label>
            <input type="text" id="add-page-name" value="" class="overlay-form-input" placeholder="${selectedClassAllowNull ? 'Optional' : 'Required'}">
          </div>
      `;

      OverlayManager.getInstance().show({
        header: 'Add New Page',
        content: [formHtml],
        contentHeaders: [''],
        closable: true,
        submitLabel: 'Add Page',
        cancelLabel: 'Cancel',
        onSubmit: async () => {
          const classSelect = document.getElementById('add-page-class') as HTMLSelectElement;
          const nameInput = document.getElementById('add-page-name') as HTMLInputElement;
          
          if (!classSelect || !nameInput) {
            throw new Error('Form elements not found');
          }

          const selectedClassValue = classSelect.value;
          const nameValue = nameInput.value.trim();

          // Validate class selection
          if (!selectedClassValue) {
            throw new Error('Please select a page class');
          }

          // Find the selected class info to check allow_null_names
          const selectedClassInfo = allowedClasses.find(c => c.class_name === selectedClassValue);
          if (!selectedClassInfo) {
            throw new Error('Invalid class selection');
          }

          // Validate name based on allow_null_names
          if (!selectedClassInfo.allow_null_names && !nameValue) {
            throw new Error('A name is required for this page class');
          }

          // Build params for add_page MCP call
          const params: any = {
            target_page: pageId,
            class: selectedClassValue
          };

          // Only include name if provided (even if allow_null_names is true, user might want to specify)
          if (nameValue) {
            params.name = nameValue;
          }

          try {
            const result = await rpc.call('add_page', params);
            
            const newPageName = result.data?.page?.name || nameValue || selectedClassValue;
            const newPageId = result.data?.page?.id;
            
            // Determine redirect URL using standard format
            const redirectUrl = this.getPageUrl(newPageId);
            
            return {
              success: true,
              _showMessage: `Page "${this.escapeHtml(newPageName)}" has been created successfully.`,
              _autoFade: true,
              _redirectAfterFade: redirectUrl,
              debug: result.debug
            };
          } catch (error) {
            throw error;
          }
        }
      });

      // Set up class change handler to update name placeholder
      setTimeout(() => {
        const classSelect = document.getElementById('add-page-class') as HTMLSelectElement;
        const nameInput = document.getElementById('add-page-name') as HTMLInputElement;
        
        if (classSelect && nameInput && allowedClasses.length > 1) {
          classSelect.addEventListener('change', () => {
            const selectedOption = classSelect.options[classSelect.selectedIndex];
            const allowNull = selectedOption.getAttribute('data-allow-null') === 'true';
            nameInput.placeholder = allowNull ? 'Optional' : 'Required';
          });
        }

        // Focus the appropriate field
        if (allowedClasses.length > 1 && classSelect) {
          classSelect.focus();
        } else if (nameInput) {
          nameInput.focus();
        }
      }, 100);
    } catch (error) {
      rpc.showError('add_page', error);
    }
  }

  /**
   * Handler for move_page: Move page to new parent
   */
  async move_page(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageName = this.getField('name') || `Page ${pageId}`;
      
      const formHtml = `
        <div class="overlay-form-group">
          <label>Target parent page ID:</label>
          <input type="number" id="move-page-target" value="" class="overlay-form-input" placeholder="Enter page ID or use Browser button">
        </div>
      `;

      OverlayManager.getInstance().show({
        header: `Move Page: ${this.escapeHtml(pageName)}`,
        content: [formHtml],
        contentHeaders: [''],
        closable: true,
        showSubmit: true,
        submitLabel: 'Move',
        cancelLabel: 'Cancel',
        middleButtonLabel: 'Browser',
        onMiddleButton: async () => {
          const targetInput = document.getElementById('move-page-target') as HTMLInputElement;
          const currentValue = targetInput?.value.trim();
          const initialPageId = currentValue ? parseInt(currentValue, 10) : pageId;
          
          const { Browser } = await import('./browser.js');
          const browser = new Browser({
            mode: 'page',
            initialPageId: isNaN(initialPageId) ? pageId : initialPageId,
            onSubmit: async (result: number | number[] | any) => {
              const selectedPageId = result as number | number[];
              const targetId = Array.isArray(selectedPageId) ? selectedPageId[0] : selectedPageId;
              
              // Set the value in the input field
              if (targetInput) {
                targetInput.value = String(targetId);
              }
              
              // Close the browser overlay
              return { _autoFade: true };
            }
          });
          await browser.show();
        },
        onSubmit: async () => {
          const targetInput = document.getElementById('move-page-target') as HTMLInputElement;
          if (!targetInput) {
            throw new Error('Form elements not found');
          }

          const targetPageId = targetInput.value.trim();
          if (!targetPageId) {
            throw new Error('Please enter a target page ID or use the Browser button to select one');
          }

          const targetId = parseInt(targetPageId, 10);
          if (isNaN(targetId)) {
            throw new Error('Target page ID must be a number');
          }

          // Capture debug options
          const overlay = OverlayManager.getInstance().getTopOverlay();
          let capturedDebugOptions = overlay ? overlay.getDebugOptions() : null;
          if (!capturedDebugOptions) {
            capturedDebugOptions = { debug: false, log: false };
          }

          try {
            const result = await rpc.call('move_page', {
              source_page: pageId,
              target_page: targetId
            }, capturedDebugOptions);

            // Handle debug data if present
            let hasDebugData = false;
            if (result && result.debug && Array.isArray(result.debug.entries) && result.debug.entries.length > 0) {
              hasDebugData = true;
              const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
              handleRPCResponseWithDebug(result, 'move_page', {
                source_page: pageId,
                target_page: targetId
              });
            }

            return {
              _showMessage: `Page "${this.escapeHtml(pageName)}" has been moved successfully.`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self' // Reload current page
            };
          } catch (error) {
            throw error;
          }
        }
      });

      // Focus the input after overlay is shown
      setTimeout(() => {
        const input = document.getElementById('move-page-target') as HTMLInputElement;
        if (input) {
          input.focus();
        }
      }, 100);
    } catch (error) {
      rpc.showError('move_page', error);
    }
  }

  /**
   * Handler for copy_page: Copy page to new parent
   */
  async copy_page(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageName = this.getField('name') || `Page ${pageId}`;
      
      const formHtml = `
        <div class="overlay-form-group">
          <label>Target parent page ID:</label>
          <input type="number" id="copy-page-target" value="" class="overlay-form-input" placeholder="Enter page ID or use Browser button">
        </div>
        <div class="overlay-form-group">
          <label class="overlay-label-inline">
            <input type="checkbox" id="copy-page-recursive" class="overlay-form-checkbox">
            <span>Recursive copy</span>
          </label>
        </div>
        <div class="overlay-form-group">
          <label class="overlay-label-inline">
            <input type="checkbox" id="copy-page-full-recursive" class="overlay-form-checkbox" disabled>
            <span>Full recursive copy</span>
          </label>
        </div>
        <div class="overlay-form-group" id="copy-page-depth-group" style="display: none;">
          <label>Max depth:</label>
          <input type="number" id="copy-page-depth" value="1" min="1" class="overlay-form-input" placeholder="Recursion depth">
        </div>
      `;

      OverlayManager.getInstance().show({
        header: `Copy Page: ${this.escapeHtml(pageName)}`,
        content: [formHtml],
        contentHeaders: [''],
        closable: true,
        showSubmit: true,
        submitLabel: 'Copy',
        cancelLabel: 'Cancel',
        middleButtonLabel: 'Browser',
        onMiddleButton: async () => {
          const targetInput = document.getElementById('copy-page-target') as HTMLInputElement;
          const currentValue = targetInput?.value.trim();
          const initialPageId = currentValue ? parseInt(currentValue, 10) : pageId;
          
          const { Browser } = await import('./browser.js');
          const browser = new Browser({
            mode: 'page',
            initialPageId: isNaN(initialPageId) ? pageId : initialPageId,
            onSubmit: async (result: number | number[] | any) => {
              const selectedPageId = result as number | number[];
              const targetId = Array.isArray(selectedPageId) ? selectedPageId[0] : selectedPageId;
              
              // Set the value in the input field
              if (targetInput) {
                targetInput.value = String(targetId);
              }
              
              // Close the browser overlay
              return { _autoFade: true };
            }
          });
          await browser.show();
        },
        onSubmit: async () => {
          const targetInput = document.getElementById('copy-page-target') as HTMLInputElement;
          const recursiveCheckbox = document.getElementById('copy-page-recursive') as HTMLInputElement;
          const fullRecursiveCheckbox = document.getElementById('copy-page-full-recursive') as HTMLInputElement;
          const depthInput = document.getElementById('copy-page-depth') as HTMLInputElement;

          if (!targetInput || !recursiveCheckbox || !fullRecursiveCheckbox || !depthInput) {
            throw new Error('Form elements not found');
          }

          const targetPageId = targetInput.value.trim();
          if (!targetPageId) {
            throw new Error('Please enter a target page ID or use the Browser button to select one');
          }

          const targetId = parseInt(targetPageId, 10);
          if (isNaN(targetId)) {
            throw new Error('Target page ID must be a number');
          }

          // Build params based on checkboxes
          const params: any = {
            source_page: pageId,
            target_page: targetId
          };

          const recursive = recursiveCheckbox.checked;
          if (recursive) {
            params.recursive = true;
            
            const fullRecursive = fullRecursiveCheckbox.checked;
            if (!fullRecursive) {
              const depthValue = depthInput.value.trim();
              if (depthValue) {
                const depth = parseInt(depthValue, 10);
                if (isNaN(depth) || depth < 1) {
                  throw new Error('Max depth must be a positive number');
                }
                params['recursive-depth'] = depth;
              }
            }
          }

          // Capture debug options
          const overlay = OverlayManager.getInstance().getTopOverlay();
          let capturedDebugOptions = overlay ? overlay.getDebugOptions() : null;
          if (!capturedDebugOptions) {
            capturedDebugOptions = { debug: false, log: false };
          }

          try {
            const result = await rpc.call('copy_page', params, capturedDebugOptions);

            // Handle debug data if present
            let hasDebugData = false;
            if (result && result.debug && Array.isArray(result.debug.entries) && result.debug.entries.length > 0) {
              hasDebugData = true;
              const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
              handleRPCResponseWithDebug(result, 'copy_page', params);
            }

            // Get new page ID from response
            const newPageId = result.data?.page?.id;
            if (!newPageId) {
              throw new Error('Copy succeeded but no new page ID returned');
            }

            // Determine redirect URL using standard format
            const redirectUrl = this.getPageUrl(newPageId);

            return {
              _showMessage: `Page "${this.escapeHtml(pageName)}" has been copied successfully.`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : redirectUrl
            };
          } catch (error) {
            throw error;
          }
        }
      });

      // Set up checkbox handlers after overlay is shown
      setTimeout(() => {
        const recursiveCheckbox = document.getElementById('copy-page-recursive') as HTMLInputElement;
        const fullRecursiveCheckbox = document.getElementById('copy-page-full-recursive') as HTMLInputElement;
        const depthGroup = document.getElementById('copy-page-depth-group') as HTMLElement;
        const targetInput = document.getElementById('copy-page-target') as HTMLInputElement;

        if (recursiveCheckbox && fullRecursiveCheckbox && depthGroup) {
          // Handle recursive checkbox change
          recursiveCheckbox.addEventListener('change', () => {
            if (recursiveCheckbox.checked) {
              fullRecursiveCheckbox.disabled = false;
              depthGroup.style.display = 'block';
            } else {
              fullRecursiveCheckbox.checked = false;
              fullRecursiveCheckbox.disabled = true;
              depthGroup.style.display = 'none';
            }
          });

          // Handle full recursive checkbox change
          fullRecursiveCheckbox.addEventListener('change', () => {
            if (fullRecursiveCheckbox.checked) {
              depthGroup.style.display = 'none';
            } else {
              depthGroup.style.display = 'block';
            }
          });
        }

        // Focus the input after overlay is shown
        if (targetInput) {
          targetInput.focus();
        }
      }, 100);
    } catch (error) {
      rpc.showError('copy_page', error);
    }
  }
}


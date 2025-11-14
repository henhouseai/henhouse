/**
 * Main application entry point and action handlers.
 */

import { getSeedData, SeedData } from './seed.js';
import { RPCClient } from './rpc-client.js';
import { OverlayManager } from './overlay-manager.js';
import { PageManager } from './page-manager.js';
import { AppAction } from './page-data.js';

class ActionHandlers {
  private rpc: RPCClient;
  private seedData: SeedData;
  private hotCacheActionIds: Set<string> = new Set(); // Track hot-cache loaded action IDs

  constructor() {
    this.rpc = new RPCClient();
    this.seedData = getSeedData();
  }

  /**
   * Load page data and set up app actions from get_page response.
   */
  async loadPageAndSetupActions(): Promise<void> {
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      console.warn('No page ID found in seed data, skipping page load');
      return;
    }

    try {
      // Initialize hot-cache action tracking from server-rendered elements
      this.initializeHotCacheActionsFromDOM();
      
      // Fetch page data
      const pageData = await this.rpc.getPage(pageId);
      
      // Store in PageManager
      const pageManager = PageManager.getInstance();
      pageManager.setPageData(pageData);
      
      // Get available actions from page data
      const rawData = pageData.getRawData();
      const availableActions = rawData.available_actions;
      
      if (availableActions && availableActions.length > 0) {
        // Separate hot-cache actions from persistent ones
        const hotCacheActions = availableActions.filter(action => action.source === 'hot_cache');
        const persistentActions = availableActions.filter(action => !action.source || action.source !== 'hot_cache');
        
        // Update hot-cache actions: remove old ones not in new list, add new ones
        this.updateHotCacheActions(hotCacheActions);
        
        // Process persistent actions (only add, never remove - they're server-rendered)
        if (persistentActions.length > 0) {
          const persistentByGroup = this.groupActionsByGroup(persistentActions);
          this.addAppActionsToMenu(persistentByGroup);
          this.attachAppActionHandlers(persistentActions);
        }
      }
    } catch (error) {
      console.error('Failed to load page and setup actions:', error);
      this.rpc.showError('loadPageAndSetupActions', error);
    }
  }

  /**
   * Initialize hot-cache action tracking from server-rendered DOM elements.
   */
  private initializeHotCacheActionsFromDOM(): void {
    // Find all server-rendered hot-cache actions
    const hotCacheElements = document.querySelectorAll('a[data-source="hot_cache"]');
    Array.from(hotCacheElements).forEach((element) => {
      const actionId = element.id;
      if (actionId) {
        this.hotCacheActionIds.add(actionId);
      }
    });
  }

  /**
   * Group app actions by their group field.
   */
  private groupActionsByGroup(actions: AppAction[]): Map<string, AppAction[]> {
    const grouped = new Map<string, AppAction[]>();
    
    for (const action of actions) {
      const groupName = action.group || 'default';
      if (!grouped.has(groupName)) {
        grouped.set(groupName, []);
      }
      grouped.get(groupName)!.push(action);
    }
    
    return grouped;
  }

  /**
   * Add app actions to the menu DOM.
   */
  private addAppActionsToMenu(actionsByGroup: Map<string, AppAction[]>): void {
    const menuContainer = document.getElementById('menu');
    if (!menuContainer) {
      console.warn('Menu container not found');
      return;
    }

    for (const [groupName, actions] of actionsByGroup.entries()) {
      // Try to find existing group by data-group attribute
      let groupUl = menuContainer.querySelector(`ul.applicationActions.menuGroup[data-group="${groupName}"]`) as HTMLUListElement;
      
      if (!groupUl) {
        // Group doesn't exist, create it
        groupUl = document.createElement('ul');
        groupUl.className = 'applicationActions menuGroup';
        groupUl.setAttribute('data-group', groupName);
        
        // Create header with human-readable name (convert snake_case to spaces)
        const headerLi = document.createElement('li');
        headerLi.className = 'header';
        headerLi.textContent = groupName.replace(/_/g, ' ').toUpperCase();
        groupUl.appendChild(headerLi);
        
        // Append to menu container
        menuContainer.appendChild(groupUl);
      }
      
      // Add actions to group (check for duplicates first)
      for (const action of actions) {
        // Check if action already exists in this group
        const existingLink = groupUl.querySelector(`a#${action.id}`);
        if (existingLink) {
          continue; // Skip if already exists
        }
        
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.id = action.id;
        a.textContent = action.label || action.tool_name;
        li.appendChild(a);
        groupUl.appendChild(li);
      }
    }
  }

  /**
   * Update hot-cache actions: remove old ones not in new list, add new ones.
   */
  private updateHotCacheActions(newHotCacheActions: AppAction[]): void {
    const newActionIds = new Set(newHotCacheActions.map(action => action.id));
    const groupsToCheck = new Set<string>();
    
    // Remove hot-cache actions that are no longer in the new list
    for (const oldActionId of this.hotCacheActionIds) {
      if (!newActionIds.has(oldActionId)) {
        // Remove from DOM
        const element = document.getElementById(oldActionId);
        if (element) {
          const li = element.closest('li');
          if (li) {
            const groupUl = li.closest('ul.applicationActions.menuGroup');
            if (groupUl) {
              const groupName = groupUl.getAttribute('data-group');
              if (groupName) {
                groupsToCheck.add(groupName);
              }
            }
            li.remove();
          }
        }
      }
    }
    
    // Check and remove empty groups (only header, no action items)
    const menuContainer = document.getElementById('menu');
    if (menuContainer) {
      for (const groupName of groupsToCheck) {
        const groupUl = menuContainer.querySelector(`ul.applicationActions.menuGroup[data-group="${groupName}"]`) as HTMLUListElement;
        if (groupUl) {
          // Count non-header children (action items)
          const actionItems = groupUl.querySelectorAll('li:not(.header)');
          if (actionItems.length === 0) {
            // Group is empty (only header), remove it
            groupUl.remove();
          }
        }
      }
    }
    
    // Update tracked set
    this.hotCacheActionIds = new Set(newActionIds);
    
    // Add new hot-cache actions
    if (newHotCacheActions.length > 0) {
      const hotCacheByGroup = this.groupActionsByGroup(newHotCacheActions);
      this.addAppActionsToMenu(hotCacheByGroup);
      this.attachAppActionHandlers(newHotCacheActions);
    }
  }

  /**
   * Attach handlers for app actions using exact id as method name.
   */
  private attachAppActionHandlers(actions: AppAction[]): void {
    for (const action of actions) {
      const element = document.getElementById(action.id);
      if (!element) {
        console.warn(`App action element not found: ${action.id}`);
        continue;
      }

      // Check if handler already attached
      if (element.hasAttribute('data-handler-attached')) {
        continue;
      }

      // Look for handler method with exact id name
      const handlerMethod = (this as any)[action.id];
      if (typeof handlerMethod === 'function') {
        element.addEventListener('click', async (e) => {
          e.preventDefault();
          try {
            await handlerMethod.call(this);
          } catch (error) {
            this.rpc.showError(action.id, error);
          }
        });
        element.setAttribute('data-handler-attached', 'true');
      } else {
        console.warn(`Handler method not found for app action: ${action.id}`);
      }
    }
  }

  /**
   * Initialize all action handlers.
   */
  init(): void {
    this.attachHandler('test_one', () => this.handleGetPage());
    this.attachHandler('test_two', () => this.handleCommandList());
    this.attachHandler('test_three', () => this.handleActionList());
    this.attachHandler('test_four', () => this.handleBackendList());
    this.attachHandler('test_five', () => this.handleHttpList());
    this.attachHandler('test_six', () => this.handleParserList());
    this.attachHandler('test_seven', () => this.handleMcpList());
    
    // Overlay test handlers
    this.attachHandler('overlay_test_one', () => this.handleOverlayTestOne());
    this.attachHandler('overlay_test_two', () => this.handleOverlayTestTwo());
    this.attachHandler('overlay_test_three', () => this.handleOverlayTestThree());
    this.attachHandler('overlay_test_four', () => this.handleOverlayTestFour());
    this.attachHandler('overlay_test_five', () => this.handleOverlayTestFive());
    this.attachHandler('overlay_test_six', () => this.handleOverlayTestSix());
    this.attachHandler('overlay_test_seven', () => this.handleOverlayTestSeven());
    this.attachHandler('overlay_test_eight', () => this.handleOverlayTestEight());
    
    // Style test handlers
    this.attachHandler('style_test_one', () => this.handleStyleTestOne());
    this.attachHandler('style_test_two', () => this.handleStyleTestTwo());
    this.attachHandler('style_test_three', () => this.handleStyleTestThree());
    this.attachHandler('style_test_four', () => this.handleStyleTestFour());
    this.attachHandler('style_test_five', () => this.handleStyleTestFive());
    this.attachHandler('style_test_six', () => this.handleStyleTestSix());
    this.attachHandler('style_test_seven', () => this.handleStyleTestSeven());
    this.attachHandler('style_test_eight', () => this.handleStyleTestEight());
    
    // CRUD handlers
    this.attachHandler('pageOptions', () => this.handlePageOptions());
  }

  /**
   * Attach a click handler to an element by ID.
   */
  private attachHandler(id: string, handler: () => Promise<void>): void {
    const element = document.getElementById(id);
    if (!element) {
      console.warn(`Action handler element not found: ${id}`);
      return;
    }

    element.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        await handler();
      } catch (error) {
        this.rpc.showError(id, error);
      }
    });
  }

  /**
   * Handle test_one: get_page
   */
  private async handleGetPage(): Promise<void> {
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      alert('No page ID found in seed data');
      return;
    }

    const result = await this.rpc.call('get_page', { id: String(pageId) });
    alert(`get_page result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_two: command_list
   */
  private async handleCommandList(): Promise<void> {
    const result = await this.rpc.call('command_list', {});
    alert(`command_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_three: action_list
   */
  private async handleActionList(): Promise<void> {
    const result = await this.rpc.call('action_list', {});
    alert(`action_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_four: backend_list
   */
  private async handleBackendList(): Promise<void> {
    const result = await this.rpc.call('backend_list', {});
    alert(`backend_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_five: http_list
   */
  private async handleHttpList(): Promise<void> {
    const result = await this.rpc.call('http_list', {});
    alert(`http_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_six: parser_list
   */
  private async handleParserList(): Promise<void> {
    const result = await this.rpc.call('parser_list', {});
    alert(`parser_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_seven: mcp_list
   */
  private async handleMcpList(): Promise<void> {
    const result = await this.rpc.call('mcp_list', {});
    alert(`mcp_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle overlay_test_one: Simple overlay with text content
   */
  private async handleOverlayTestOne(): Promise<void> {
    const manager = OverlayManager.getInstance();
    manager.show({
      header: 'Simple Overlay Test',
      content: 'This is a simple overlay with just text content. Click Cancel or press ESC to close.',
      closable: true
    });
  }

  /**
   * Handle overlay_test_two: Overlay with HTML content
   */
  private async handleOverlayTestTwo(): Promise<void> {
    const manager = OverlayManager.getInstance();
    const htmlContent = `
      <div>
        <h3>HTML Content Test</h3>
        <p>This overlay contains <strong>HTML</strong> content with formatting.</p>
        <ul>
          <li>Item 1</li>
          <li>Item 2</li>
          <li>Item 3</li>
        </ul>
      </div>
    `;
    manager.show({
      header: 'HTML Overlay Test',
      content: htmlContent,
      closable: true
    });
  }

  /**
   * Handle overlay_test_three: Overlay with submit handler
   */
  private async handleOverlayTestThree(): Promise<void> {
    const manager = OverlayManager.getInstance();
    manager.show({
      header: 'Submit Overlay Test',
      content: 'This overlay has a submit button. Click Submit to see it in action.',
      closable: true,
      onSubmit: async () => {
        // Simulate async operation
        await new Promise(resolve => setTimeout(resolve, 500));
        alert('Submit handler executed!');
        return { success: true };
      },
      onCancel: () => {
        console.log('Overlay cancelled');
      }
    });
  }

  /**
   * Handle overlay_test_four: Multiple overlays stacked
   */
  private async handleOverlayTestFour(): Promise<void> {
    const manager = OverlayManager.getInstance();
    
    // Show first overlay
    manager.show({
      header: 'First Overlay',
      content: 'This is the first overlay. Click Submit to open a second overlay on top.',
      closable: true,
      onSubmit: async () => {
        // Show second overlay on top
        manager.show({
          header: 'Second Overlay',
          content: 'This is a second overlay stacked on top of the first. Notice the z-index stacking.',
          closable: true,
          onSubmit: async () => {
            alert('Second overlay submitted!');
            return { success: true };
          }
        });
        return { success: true };
      }
    });
  }

  /**
   * Handle overlay_test_five: Focus trap test
   */
  private async handleOverlayTestFive(): Promise<void> {
    const manager = OverlayManager.getInstance();
    const htmlContent = `
      <div>
        <p>Focus Trap Test: Press Tab to cycle through focusable elements.</p>
        <p>Focus should stay trapped inside the overlay.</p>
        <input type="text" placeholder="First input" />
        <button>Button 1</button>
        <input type="text" placeholder="Second input" />
        <button>Button 2</button>
        <a href="#">Link</a>
      </div>
    `;
    manager.show({
      header: 'Focus Trap Test',
      content: htmlContent,
      closable: true
    });
  }

  /**
   * Handle overlay_test_six: Backdrop click test
   */
  private async handleOverlayTestSix(): Promise<void> {
    const manager = OverlayManager.getInstance();
    manager.show({
      header: 'Backdrop Click Test',
      content: 'Click the dark backdrop behind this overlay. It should close the overlay.',
      closable: true
    });
  }

  /**
   * Handle overlay_test_seven: Textarea Enter test
   */
  private async handleOverlayTestSeven(): Promise<void> {
    const manager = OverlayManager.getInstance();
    const htmlContent = `
      <div>
        <p>Textarea Enter Test: Press Enter in the textarea below. It should NOT trigger submit.</p>
        <p>Press Enter outside the textarea to trigger submit.</p>
        <textarea rows="4" placeholder="Type here and press Enter - should NOT submit"></textarea>
        <input type="text" placeholder="Press Enter here - SHOULD submit" />
      </div>
    `;
    manager.show({
      header: 'Textarea Enter Test',
      content: htmlContent,
      closable: true,
      onSubmit: async () => {
        alert('Submit triggered! (Enter was pressed outside textarea)');
        return { success: true };
      }
    });
  }

  /**
   * Handle overlay_test_eight: Close all test
   */
  private async handleOverlayTestEight(): Promise<void> {
    const manager = OverlayManager.getInstance();
    
    // Show multiple overlays
    manager.show({
      header: 'Overlay 1',
      content: 'This is overlay 1. We will open 2 more overlays, then close all at once.',
      closable: true
    });
    
    setTimeout(() => {
      manager.show({
        header: 'Overlay 2',
        content: 'This is overlay 2.',
        closable: true
      });
    }, 500);
    
    setTimeout(() => {
      manager.show({
        header: 'Overlay 3',
        content: 'This is overlay 3. Click Submit to close all overlays at once.',
        closable: true,
        onSubmit: async () => {
          manager.closeAll();
          alert('All overlays closed!');
          return { success: true };
        }
      });
    }, 1000);
  }

  /**
   * Handle style_test_one: Empty content test
   */
  private async handleStyleTestOne(): Promise<void> {
    const manager = OverlayManager.getInstance();
    manager.show({
      header: 'Empty Content Test',
      content: '', // Empty string
      closable: true
    });
  }

  /**
   * Handle style_test_two: Long content test
   */
  private async handleStyleTestTwo(): Promise<void> {
    const manager = OverlayManager.getInstance();
    const longContent = Array(50).fill(0).map((_, i) => 
      `<p>This is paragraph ${i + 1}. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>`
    ).join('');
    manager.show({
      header: 'Long Content Test',
      content: `<div>${longContent}</div>`,
      closable: true
    });
  }

  /**
   * Handle style_test_three: Complex HTML test
   */
  private async handleStyleTestThree(): Promise<void> {
    const manager = OverlayManager.getInstance();
    const complexHTML = `
      <div>
        <h2>Complex HTML Test</h2>
        <p>This overlay contains complex nested HTML structures.</p>
        <div style="border: 1px solid #ccc; padding: 10px; margin: 10px; clear: both;">
          <h3>Nested Div</h3>
          <ul style="clear: both; margin-left: 20px; padding-left: 0;">
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
          </ul>
        </div>
        <form>
          <label style="display: block; margin-bottom: 10px;">Name: <input type="text" /></label>
          <label style="display: block; margin-bottom: 10px;">Email: <input type="email" /></label>
        </form>
      </div>
    `;
    manager.show({
      header: 'Complex HTML Test',
      content: complexHTML,
      closable: true
    });
  }

  /**
   * Handle style_test_four: Error message test
   */
  private async handleStyleTestFour(): Promise<void> {
    const manager = OverlayManager.getInstance();
    manager.show({
      header: 'Error Message Test',
      content: 'Click Submit to trigger an error message. The submit button should disappear, show loading, then reappear with an error message.',
      closable: true,
      onSubmit: async () => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        throw new Error('This is a test error message. The submit button should reappear after this error.');
      }
    });
  }

  /**
   * Handle style_test_five: Success message test
   */
  private async handleStyleTestFive(): Promise<void> {
    const manager = OverlayManager.getInstance();
    manager.show({
      header: 'Success Message Test',
      content: 'Click Submit to trigger a success message. The submit button should disappear, show loading, then show a success message.',
      closable: true,
      onSubmit: async () => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        return { success: true };
      }
    });
  }

  /**
   * Handle style_test_six: Loading state test
   */
  private async handleStyleTestSix(): Promise<void> {
    const manager = OverlayManager.getInstance();
    manager.show({
      header: 'Loading State Test',
      content: 'Click Submit to see the loading spinner. It will take 3 seconds to complete.',
      closable: true,
      onSubmit: async () => {
        await new Promise(resolve => setTimeout(resolve, 3000));
        return { success: true };
      }
    });
  }

  /**
   * Handle style_test_seven: Special characters test
   */
  private async handleStyleTestSeven(): Promise<void> {
    const manager = OverlayManager.getInstance();
    const specialContent = `
      <div>
        <p>Special Characters Test:</p>
        <ul>
          <li>Less than: &lt;</li>
          <li>Greater than: &gt;</li>
          <li>Ampersand: &amp;</li>
          <li>Quotes: "double" and 'single'</li>
          <li>HTML tags as text: &lt;div&gt;&lt;/div&gt;</li>
        </ul>
      </div>
    `;
    manager.show({
      header: 'Special Characters Test',
      content: specialContent,
      closable: true
    });
  }

  /**
   * Handle style_test_eight: Table/Form content test
   */
  private async handleStyleTestEight(): Promise<void> {
    const manager = OverlayManager.getInstance();
    const tableFormContent = `
      <div>
        <h3>Table Content</h3>
        <table border="1" style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr>
              <th>Column 1</th>
              <th>Column 2</th>
              <th>Column 3</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Row 1, Cell 1</td>
              <td>Row 1, Cell 2</td>
              <td>Row 1, Cell 3</td>
            </tr>
            <tr>
              <td>Row 2, Cell 1</td>
              <td>Row 2, Cell 2</td>
              <td>Row 2, Cell 3</td>
            </tr>
          </tbody>
        </table>
        <h3>Form Content</h3>
        <form>
          <label>Text Input: <input type="text" placeholder="Enter text" /></label><br/>
          <label>Textarea: <textarea rows="3" placeholder="Enter multiline text"></textarea></label><br/>
          <label>Select: 
            <select>
              <option>Option 1</option>
              <option>Option 2</option>
              <option>Option 3</option>
            </select>
          </label><br/>
          <label>Checkbox: <input type="checkbox" /> Check me</label><br/>
        </form>
      </div>
    `;
    manager.show({
      header: 'Table/Form Content Test',
      content: tableFormContent,
      closable: true
    });
  }

  /**
   * Handle modify_name: Edit page name
   */
  private async modify_name(): Promise<void> {
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      alert('No page ID found in seed data');
      return;
    }

    try {
      // Get page data from PageManager (already loaded, no network call needed)
      const pageManager = PageManager.getInstance();
      const pageData = pageManager.getPageData();
      
      if (!pageData) {
        throw new Error('Page data not found in PageManager');
      }
      
      // Request 'name' field with 'form' context to register it for editing
      const currentName = pageData.getField('name', 'form') || '';

      // Create form HTML with standardized field ID
      const formHtml = `
        <div class="overlayContent">
          <div>
            <label>Page name:</label>
            <input type="text" id="page-field-name" value="${this.escapeHtml(currentName)}">
          </div>
        </div>
      `;

      const overlay = OverlayManager.getInstance().show({
        header: 'Modify Page Name',
        content: formHtml,
        closable: true,
        submitLabel: 'Submit',
        cancelLabel: 'Cancel',
        onCancel: () => {
          // Clear all field checkouts when overlay is closed without submitting
          pageData.clearFieldRegistry();
        },
        onUnmount: () => {
          // Clear all field checkouts when overlay is unmounted
          pageData.clearFieldRegistry();
        },
        onSubmit: async () => {
          // PageData handles change detection and submission automatically
          const result = await pageData.submitChanges(this.rpc);
          
          // Handle "no changes" case - return special marker so overlay knows to show message and fade
          if (result.noChanges) {
            return { ...result, _showMessage: result.message || 'No changes made', _autoFade: true };
          }
          
          // Build detailed success/error messages for each operation
          const messages: string[] = [];
          if (result.operations && result.operations.length > 0) {
            result.operations.forEach((op: any) => {
              messages.push(op.message || `${op.mapping}: ${op.success ? 'Success' : 'Failed'}`);
            });
          } else {
            // Fallback to general message
            messages.push(result.message || (result.success ? 'Success' : 'Failed'));
          }
          
          const combinedMessage = messages.join('\n');
          const allSucceeded = result.success && result.errors.length === 0;
          
          // Return result with message info - overlay will handle display
          if (allSucceeded) {
            // Extract new name from result and update DOM
            if (result.success && pageId) {
              // Find the name update operation result
              const nameOp = result.operations?.find((op: any) => op.fields?.includes('name'));
              if (nameOp && nameOp.success && nameOp.result) {
                const parsedResult = this.rpc.extractMCPData(nameOp.result);
                const resultPageData = parsedResult?.page || parsedResult;
                const newName = resultPageData?.name;
                const newRawText = resultPageData?.text; // Raw text from get_page response
                
                if (newName) {
                  // Update internal PageData with new name (already done by submitChanges, but ensure it's set)
                  pageData.updateFieldValue('name', newName);
                  
                  // Update internal PageData with new raw text (in case self-referential link changed)
                  if (newRawText !== undefined) {
                    pageData.updateFieldValue('text', newRawText);
                  }
                  
                  // Update the last <a> tag in the path (header)
                  const headerEl = document.getElementById('header');
                  if (headerEl) {
                    const pathUl = headerEl.querySelector('ul.path') as HTMLUListElement | null;
                    if (pathUl) {
                      const listItems = pathUl.querySelectorAll('li');
                      if (listItems.length > 0) {
                        const lastLi = listItems[listItems.length - 1];
                        const lastLink = lastLi.querySelector('a') as HTMLAnchorElement | null;
                        if (lastLink) {
                          lastLink.textContent = newName;
                        }
                      }
                    }
                  }
                  
                  // Also update page text in case it contains a link to itself
                  try {
                    const getTextResult = await this.rpc.call('get_text', { page_id: pageId });
                    const parsedTextResult = this.rpc.extractMCPData(getTextResult);
                    const processedText = parsedTextResult?.processed_text;
                    
                    if (processedText) {
                      const textDiv = document.getElementById(`page-text-${pageId}`) as HTMLDivElement | null;
                      if (textDiv) {
                        textDiv.innerHTML = processedText;
                      }
                    }
                  } catch (error) {
                    console.error('Failed to fetch updated text after name change:', error);
                  }
                }
              }
            }
            
            return { ...result, _showMessage: combinedMessage, _autoFade: true };
          } else {
            // Some failed - throw error so overlay shows error and doesn't fade
            throw new Error(combinedMessage);
          }
        }
      });

      // Focus the input after overlay is shown
      setTimeout(() => {
        const input = document.getElementById('page-field-name') as HTMLInputElement;
        if (input) {
          input.focus();
          input.select();
        }
      }, 100);
    } catch (error) {
      this.rpc.showError('modify_name', error);
    }
  }

  /**
   * Handle modify_text: Edit page text content
   */
  private async modify_text(): Promise<void> {
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      alert('No page ID found in seed data');
      return;
    }

    try {
      // Get page data from PageManager (already loaded, no network call needed)
      const pageManager = PageManager.getInstance();
      const pageData = pageManager.getPageData();
      
      if (!pageData) {
        throw new Error('Page data not found in PageManager');
      }
      
      // Request 'text' field with 'form' context to register it for editing
      const currentText = pageData.getField('text', 'form') || '';

      // Create textarea form with standardized field ID
      const formHtml = `
        <div class="overlayContent">
          <div>
            <textarea id="page-field-text" name="text" rows="20" cols="80" style="width: 100%; min-height: 400px; font-family: monospace;">${this.escapeHtml(currentText)}</textarea>
          </div>
        </div>
      `;

      const overlay = OverlayManager.getInstance().show({
        header: 'Text Editor',
        content: formHtml,
        closable: true,
        submitLabel: 'Submit',
        cancelLabel: 'Cancel',
        onCancel: () => {
          // Clear all field checkouts when overlay is closed without submitting
          pageData.clearFieldRegistry();
        },
        onUnmount: () => {
          // Clear all field checkouts when overlay is unmounted
          pageData.clearFieldRegistry();
        },
        onSubmit: async () => {
          // PageData handles change detection and submission automatically
          const result = await pageData.submitChanges(this.rpc);
          
          // Handle "no changes" case - return special marker so overlay knows to show message and fade
          if (result.noChanges) {
            return { ...result, _showMessage: result.message || 'No changes made', _autoFade: true };
          }
          
          // Build detailed success/error messages for each operation
          const messages: string[] = [];
          if (result.operations && result.operations.length > 0) {
            result.operations.forEach((op: any) => {
              messages.push(op.message || `${op.mapping}: ${op.success ? 'Success' : 'Failed'}`);
            });
          } else {
            // Fallback to general message
            messages.push(result.message || (result.success ? 'Success' : 'Failed'));
          }
          
          const combinedMessage = messages.join('\n');
          const allSucceeded = result.success && result.errors.length === 0;
          
          // Return result with message info - overlay will handle display
          if (allSucceeded) {
            // After successful submit, fetch processed text and update DOM
            if (result.success && pageId) {
              // Find the text update operation result
              const textOp = result.operations?.find((op: any) => op.fields?.includes('text'));
              if (textOp && textOp.success) {
                try {
                  const getTextResult = await this.rpc.call('get_text', { page_id: pageId });
                  const parsedTextResult = this.rpc.extractMCPData(getTextResult);
                  const processedText = parsedTextResult?.processed_text;
                  
                  if (processedText) {
                    const textDiv = document.getElementById(`page-text-${pageId}`) as HTMLDivElement | null;
                    if (textDiv) {
                      textDiv.innerHTML = processedText;
                    }
                  }
                } catch (error) {
                  console.error('Failed to fetch updated text:', error);
                  // Don't throw - the submit was successful, just couldn't update display
                }
              }
            }
            
            return { ...result, _showMessage: combinedMessage, _autoFade: true };
          } else {
            // Some failed - throw error so overlay shows error and doesn't fade
            throw new Error(combinedMessage);
          }
        }
      });

      // Focus the textarea after overlay is shown
      setTimeout(() => {
        const textarea = document.getElementById('page-field-text') as HTMLTextAreaElement;
        if (textarea) {
          textarea.focus();
        }
      }, 100);
    } catch (error) {
      this.rpc.showError('modify_text', error);
    }
  }

  /**
   * Handle delete_page: Delete a page with confirmation
   */
  private async delete_page(): Promise<void> {
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      alert('No page ID found in seed data');
      return;
    }

    try {
      // Get page data from PageManager
      const pageManager = PageManager.getInstance();
      const pageData = pageManager.getPageData();
      
      if (!pageData) {
        throw new Error('Page data not found in PageManager');
      }
      
      const pageName = pageData.getField('name') || `Page ${pageId}`;
      const pageClass = pageData.getField('class') || 'page';
      
      // Create form HTML with confirmation checkbox
      const formHtml = `
        <div class="overlayContent">
          <div style="margin-bottom: 20px;">
            <p><strong>Warning:</strong> This will permanently delete the page and all its children.</p>
            <p>Page: <strong>${this.escapeHtml(pageName)}</strong> (ID: ${pageId}, Class: ${this.escapeHtml(pageClass)})</p>
          </div>
          <div>
            <label style="display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" id="page-delete-confirm" style="width: auto;">
              <span>I confirm that I want to delete this page</span>
            </label>
          </div>
        </div>
      `;

      const overlay = OverlayManager.getInstance().show({
        header: 'Delete Page',
        content: formHtml,
        closable: true,
        submitLabel: 'Delete',
        cancelLabel: 'Cancel',
        onCancel: () => {
          // Clear any field checkouts when overlay is closed
          pageData.clearFieldRegistry();
        },
        onUnmount: () => {
          // Clear any field checkouts when overlay is unmounted
          pageData.clearFieldRegistry();
        },
        onSubmit: async () => {
          // Check if confirmation checkbox is checked
          const confirmCheckbox = document.getElementById('page-delete-confirm') as HTMLInputElement;
          if (!confirmCheckbox || !confirmCheckbox.checked) {
            throw new Error('You must confirm deletion by checking the confirmation box');
          }
          
          // Call delete_page MCP tool
          try {
            const result = await this.rpc.call('delete_page', {
              page_id: pageId,
              confirm: true
            });
            
            const parsedResult = this.rpc.extractMCPData(result);
            
            // Return success - overlay will auto-fade
            return {
              success: true,
              _showMessage: `Page "${this.escapeHtml(pageName)}" has been deleted successfully.`,
              _autoFade: true
            };
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            throw new Error(`Failed to delete page: ${errorMessage}`);
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
      this.rpc.showError('delete_page', error);
    }
  }

  /**
   * Handle combo: Test form with name/text editable and read-only fields displayed
   */
  private async combo(): Promise<void> {
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      alert('No page ID found in seed data');
      return;
    }

    try {
      // Get page data from PageManager
      const pageManager = PageManager.getInstance();
      const pageData = pageManager.getPageData();
      
      if (!pageData) {
        throw new Error('Page data not found in PageManager');
      }
      
      // Get editable fields
      const currentName = pageData.getField('name', 'form') || '';
      const currentText = pageData.getField('text', 'form') || '';
      
      // Get read-only fields (these should NOT be registered for editing)
      const pageIdValue = pageData.getField('id') || '';
      const pageClass = pageData.getField('class') || '';
      const pageLink = pageData.getField('link') || '';
      const lastModified = pageData.getField('last_modified') || '';
      const username = pageData.getField('username') || '';
      const path = pageData.getField('path') || [];
      const pathStr = Array.isArray(path) ? path.map((p: any) => p.name).filter(Boolean).join(' / ') : '';
      
      // Create form HTML with editable and read-only fields
      const formHtml = `
        <div class="overlayContent">
          <div style="margin-bottom: 20px;">
            <h3 style="margin-bottom: 10px;">Editable Fields:</h3>
            <div style="margin-bottom: 15px;">
              <label>Page name:</label>
              <input type="text" id="page-field-name" value="${this.escapeHtml(currentName)}" style="width: 100%;">
            </div>
            <div style="margin-bottom: 15px;">
              <label>Page text:</label>
              <textarea id="page-field-text" name="text" rows="10" cols="80" style="width: 100%; min-height: 200px; font-family: monospace;">${this.escapeHtml(currentText)}</textarea>
            </div>
          </div>
          <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ccc;">
            <h3 style="margin-bottom: 10px;">Read-Only Fields (for display only):</h3>
            <div style="display: grid; grid-template-columns: 150px 1fr; gap: 10px; margin-bottom: 10px;">
              <div><strong>ID:</strong></div>
              <div>${this.escapeHtml(String(pageIdValue))}</div>
              <div><strong>Class:</strong></div>
              <div>${this.escapeHtml(pageClass)}</div>
              <div><strong>Link:</strong></div>
              <div>${this.escapeHtml(pageLink)}</div>
              <div><strong>Last Modified:</strong></div>
              <div>${this.escapeHtml(lastModified)}</div>
              <div><strong>Username:</strong></div>
              <div>${this.escapeHtml(username)}</div>
              <div><strong>Path:</strong></div>
              <div>${this.escapeHtml(pathStr)}</div>
            </div>
          </div>
        </div>
      `;

      const overlay = OverlayManager.getInstance().show({
        header: 'Combo Test Form',
        content: formHtml,
        closable: true,
        submitLabel: 'Submit',
        cancelLabel: 'Cancel',
        onCancel: () => {
          // Clear field checkouts when overlay is closed
          pageData.clearFieldRegistry();
        },
        onUnmount: () => {
          // Clear field checkouts when overlay is unmounted
          pageData.clearFieldRegistry();
        },
        onSubmit: async () => {
          // PageData handles change detection and submission automatically
          // This will only submit name and text (read-only fields won't be in registry)
          const result = await pageData.submitChanges(this.rpc);
          
          // Handle "no changes" case
          if (result.noChanges) {
            return { ...result, _showMessage: result.message || 'No changes made', _autoFade: true };
          }
          
          // Build detailed success/error messages
          const messages: string[] = [];
          if (result.operations && result.operations.length > 0) {
            result.operations.forEach((op: any) => {
              messages.push(op.message || `${op.mapping}: ${op.success ? 'Success' : 'Failed'}`);
            });
          } else {
            messages.push(result.message || (result.success ? 'Success' : 'Failed'));
          }
          
          const combinedMessage = messages.join('\n');
          const allSucceeded = result.success && result.errors.length === 0;
          
          if (allSucceeded) {
            // Update DOM if needed (similar to modify_name and modify_text)
            if (result.success && pageId) {
              // Find name update operation
              const nameOp = result.operations?.find((op: any) => op.fields?.includes('name'));
              if (nameOp && nameOp.success && nameOp.result) {
                const parsedResult = this.rpc.extractMCPData(nameOp.result);
                const resultPageData = parsedResult?.page || parsedResult;
                const newName = resultPageData?.name;
                
                if (newName) {
                  // Update breadcrumb
                  const headerEl = document.getElementById('header');
                  if (headerEl) {
                    const pathUl = headerEl.querySelector('ul.path') as HTMLUListElement | null;
                    if (pathUl) {
                      const listItems = pathUl.querySelectorAll('li');
                      if (listItems.length > 0) {
                        const lastLi = listItems[listItems.length - 1];
                        const lastLink = lastLi.querySelector('a') as HTMLAnchorElement | null;
                        if (lastLink) {
                          lastLink.textContent = newName;
                        }
                      }
                    }
                  }
                }
              }
              
              // Find text update operation
              const textOp = result.operations?.find((op: any) => op.fields?.includes('text'));
              if (textOp && textOp.success) {
                try {
                  const getTextResult = await this.rpc.call('get_text', { page_id: pageId });
                  const parsedTextResult = this.rpc.extractMCPData(getTextResult);
                  const processedText = parsedTextResult?.processed_text;
                  
                  if (processedText) {
                    const textDiv = document.getElementById(`page-text-${pageId}`) as HTMLDivElement | null;
                    if (textDiv) {
                      textDiv.innerHTML = processedText;
                    }
                  }
                } catch (error) {
                  console.error('Failed to fetch updated text:', error);
                }
              }
            }
            
            return { ...result, _showMessage: combinedMessage, _autoFade: true };
          } else {
            // Some failed - throw error so overlay shows error and doesn't fade
            throw new Error(combinedMessage);
          }
        }
      });

      // Focus the name input after overlay is shown
      setTimeout(() => {
        const input = document.getElementById('page-field-name') as HTMLInputElement;
        if (input) {
          input.focus();
          input.select();
        }
      }, 100);
    } catch (error) {
      this.rpc.showError('combo', error);
    }
  }

  /**
   * Handle pageOptions: Edit page options
   */
  private async handlePageOptions(): Promise<void> {
    // TODO: Implement pageOptions handler
    alert('Page Options not yet implemented');
  }

  /**
   * Escape HTML to prevent XSS
   */
  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
  const handlers = new ActionHandlers();
  handlers.init();
  
  // Load page data and populate app actions
  await handlers.loadPageAndSetupActions();
});


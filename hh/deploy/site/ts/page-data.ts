/**
 * PageData - Base class for managing page data.
 * Pure data model - business logic is in PageManager.
 */

import { PageManager } from './page-manager.js';
import { OverlayManager } from './overlay-manager.js';
import { getSeedData } from './seed.js';

export interface PageInfo {
  id: number;
  name: string | null;
  link: string | null;
  parent: number | null;
  class: string;
  visibility: number;
  text: string | null;
  last_modified: string | null;
  username: string | null;
  comments: string | null;
  path?: Array<{ id: number; name: string | null; link: string | null; class?: string }>;
  [key: string]: any; // Allow derived class fields
}

export interface ImageInfo {
  id: number;
  caption: string | null;
  username: string | null;
  uploaded: string | null;
  visibility: number;
  view_count: number;
  image_rank: number;
  instances: Array<{
    width: number;
    height: number;
    src: string;
    filesize: number;
  }>;
  max_width: number;
  max_height: number;
  max_filesize: number;
  aspect_ratio: string;
  file_path: string;
  num_instances: number;
}

export interface ChildPageInfo {
  id: number;
  name: string | null;
  parent: number;
  class: string;
  [key: string]: any;
}

export interface ChildrenByClass {
  [class_name: string]: {
    class: string;
    children: ChildPageInfo[];
  };
}

export interface AppAction {
  id: string;
  tool_name: string;
  description: string;
  label: string;
  group: string;
  source?: string; // 'hot_cache' or 'persistent'
  requires_fields?: string[];
}

export interface GetPageResponse {
  page: PageInfo;
  images: ImageInfo[];
  children_by_class: ChildrenByClass;
  available_actions?: AppAction[];
}

export interface FieldRegistry {
  [fieldName: string]: {
    originalValue: any;
    extracted: boolean;
    fieldType: 'text' | 'textarea' | 'select' | 'checkbox' | 'number' | 'custom';
    domSelector?: string;
  };
}

/**
 * FieldMapping defines how form fields map to MCP tools.
 * Multiple fields can map to the same MCP tool (grouped operations).
 * Priority: lower number = higher priority (prefer exact matches, then smaller groups)
 */
export interface FieldMapping {
  fields: string[];           // Field names that this mapping covers
  mcpTool: string;            // MCP tool name to call
  priority: number;           // Lower = higher priority (0 = exact match, 1 = small group, 2 = larger group)
  buildParams: (fields: string[], values: { [fieldName: string]: any }, pageId: number) => any; // Function to build MCP params
}

export class PageData {
  protected data: GetPageResponse;
  protected dynamicFields: { [key: string]: any } = {};
  
  // Read-only fields that can be accessed but not edited
  protected readonly readOnlyFields: Set<string> = new Set([
    'id',
    'class',
    'link',
    'last_modified',
    'username',
    'path'
  ]);
  
  // Base page fields that are always present
  private static readonly BASE_PAGE_FIELDS = [
    'id', 'name', 'link', 'parent', 'class', 'visibility', 'text',
    'last_modified', 'username', 'comments', 'path'
  ];

  constructor(data: GetPageResponse) {
    this.data = data;
    this.discoverDynamicFields();
    // Register field mappings with PageManager
    const pageManager = PageManager.getInstance();
    pageManager.registerFieldMappings(this.getFieldMappings());
  }

  /**
   * Discover dynamic fields that aren't in the base page fields list
   */
  private discoverDynamicFields(): void {
    for (const [key, value] of Object.entries(this.data.page)) {
      if (!PageData.BASE_PAGE_FIELDS.includes(key)) {
        this.dynamicFields[key] = value;
      }
    }
  }

  /**
   * Get field value with special handling for certain fields
   * @param fieldName - Name of the field to get
   * @param context - 'display' (default) or 'form' (registers field for editing)
   * @returns Field value or null if not found
   */
  getField(fieldName: string, context: 'display' | 'form' = 'display'): any {
    // Special handling for base page fields
    switch (fieldName) {
      case 'text':
        // Special text processing - return raw text for now
        const textValue = this.data.page.text;
        if (context === 'form') {
          PageManager.getInstance().registerField('text', textValue, 'textarea');
        }
        return textValue;
      
      case 'name':
        // Special breadcrumb/display handling
        const nameValue = this.data.page.name;
        if (context === 'form') {
          PageManager.getInstance().registerField('name', nameValue, 'text');
        }
        return nameValue;
      
      case 'class':
        // Read-only field - return value but don't register for editing
        return this.data.page.class;
      
      default:
        // Check if it's a read-only field
        if (this.readOnlyFields.has(fieldName)) {
          // Return value from page data or dynamic fields, but don't register for editing
          if (fieldName in this.data.page) {
            return this.data.page[fieldName];
          }
          if (fieldName in this.dynamicFields) {
            return this.dynamicFields[fieldName];
          }
          return null;
        }
        
        // Check if it's a base page field
        if (fieldName in this.data.page) {
          const value = this.data.page[fieldName];
          if (context === 'form') {
            // Auto-detect field type for base fields
            const fieldType = this.detectFieldType(fieldName, value);
            PageManager.getInstance().registerField(fieldName, value, fieldType);
          }
          return value;
        }
        
        // Check if it's a dynamic field
        if (fieldName in this.dynamicFields) {
          const value = this.dynamicFields[fieldName];
          if (context === 'form') {
            // Auto-detect field type for dynamic fields
            const fieldType = this.detectFieldType(fieldName, value);
            PageManager.getInstance().registerField(fieldName, value, fieldType);
          }
          return value;
        }
        
        // Field not found
        return null;
    }
  }

  /**
   * Auto-detect field type based on field name and value
   */
  private detectFieldType(fieldName: string, value: any): 'text' | 'textarea' | 'select' | 'checkbox' | 'number' | 'custom' {
    if (typeof value === 'boolean') return 'checkbox';
    if (typeof value === 'number') return 'number';
    if (typeof value === 'string' && value.length > 100) return 'textarea';
    return 'text';
  }

  /**
   * Update internal data with new field value after successful update
   * This ensures the next form shows the updated value, not the old one
   */
  updateFieldValue(fieldName: string, newValue: any): void {
    // Check if it's a base page field
    if (fieldName in this.data.page) {
      this.data.page[fieldName] = newValue;
    } else {
      // Otherwise, store in dynamic fields
      this.dynamicFields[fieldName] = newValue;
    }
  }

  /**
   * Get field-to-MCP mappings for this page class.
   * Derived classes should override this to provide their specific mappings.
   * Base class provides mappings for common page fields.
   * This is protected - use getFieldMappingsPublic() for external access.
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      // Individual field setters (highest priority - exact matches)
      {
        fields: ['name'],
        mcpTool: 'modify_name',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          name: values['name']
        })
      },
      {
        fields: ['text'],
        mcpTool: 'modify_text',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          text: values['text']
        })
      }
      // Derived classes can add more mappings here
    ];
  }

  /**
   * Public method to get field mappings (for PageManager access).
   */
  getFieldMappingsPublic(): FieldMapping[] {
    return this.getFieldMappings();
  }

  /**
   * Get page ID (convenience method)
   */
  get id(): number {
    return this.data.page.id;
  }

  // ===== Images Helpers =====
  getImages(): ImageInfo[] {
    return this.data.images || [];
  }

  getImageCount(): number {
    return this.data.images?.length || 0;
  }

  getPrimaryImage(): ImageInfo | null {
    return this.data.images && this.data.images.length > 0 ? this.data.images[0] : null;
  }

  getImageByRank(rank: number): ImageInfo | null {
    return this.data.images?.find(img => img.image_rank === rank) || null;
  }

  // ===== Children Helpers =====
  getChildrenByClass(): ChildrenByClass {
    return this.data.children_by_class || {};
  }

  getChildrenForClass(className: string): ChildPageInfo[] {
    const classData = this.data.children_by_class?.[className];
    return classData?.children || [];
  }

  getAllChildren(): ChildPageInfo[] {
    const all: ChildPageInfo[] = [];
    for (const classData of Object.values(this.data.children_by_class || {})) {
      all.push(...(classData.children || []));
    }
    return all;
  }

  getChildCount(): number {
    return this.getAllChildren().length;
  }

  getChildCountForClass(className: string): number {
    return this.getChildrenForClass(className).length;
  }

  // ===== Path/Breadcrumb Helpers =====
  getBreadcrumbPath(): Array<{ id: number; name: string | null; link: string | null; class?: string }> {
    return this.data.page.path || [];
  }

  getBreadcrumbNames(): string[] {
    return this.getBreadcrumbPath().map(p => p.name || '').filter(n => n.length > 0);
  }

  // ===== Raw Data Access =====
  getRawData(): GetPageResponse {
    return this.data;
  }

  getPageData(): PageInfo {
    return this.data.page;
  }

  // ===== Handler Methods =====
  // These are UI handlers for page-specific CRUD operations
  // They accept RPC client as parameter and use PageManager for business logic

  /**
   * Escape HTML to prevent XSS
   */
  protected escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Process operations incrementally, updating overlay as each completes.
   * Returns final result with all operations.
   */
  protected async processOperationsIncrementally(
    rpc: any,
    optimalMappings: Array<{ mapping: any; fields: string[] }>,
    currentValues: { [fieldName: string]: any },
    pageId: number
  ): Promise<any> {
    const overlayManager = OverlayManager.getInstance();
    const overlay = overlayManager.getTopOverlay();
    
    // Capture debug options once at the start (before any RPC calls)
    // This ensures all calls in the loop use the same debug options
    let capturedDebugOptions: any = null;
    if (overlay) {
      capturedDebugOptions = overlay.getDebugOptions();
    }
    
    const allOperations: any[] = [];
    let allSucceeded = true;
    let hasDebugData = false; // Track if any operation returned debug data
    
    // Process each operation individually (not in parallel)
    for (const { mapping, fields } of optimalMappings) {
      const params = mapping.buildParams(fields, currentValues, pageId);
      
      try {
        // Pass captured debug options to each RPC call
        const rawResult = await rpc.call(mapping.mcpTool, params, capturedDebugOptions);
        // rawResult is already RPCCallResult with data and debug
        const result = rawResult.data;
        
        // Handle debug data immediately - create overlay for each response with debug
        // Only show debug overlay if debug data exists and has entries
        if (rawResult.debug && Array.isArray(rawResult.debug.entries) && rawResult.debug.entries.length > 0) {
          hasDebugData = true; // Mark that we found debug data
          const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
          handleRPCResponseWithDebug(rawResult, mapping.mcpTool, params);
        }
        
        // Clear fields from registry after successful update
        PageManager.getInstance()['clearFields'](fields);
        
        // Update internal PageData
        fields.forEach((fieldName: string) => {
          if (fieldName in currentValues) {
            this.updateFieldValue(fieldName, currentValues[fieldName]);
          }
        });
        
        const operation = {
          mapping: mapping.mcpTool,
          fields,
          success: true,
          result,
          message: `Successfully updated ${fields.join(', ')}`
        };
        
        allOperations.push(operation);
        
        // Add success message to overlay immediately
        if (overlay) {
          const currentMessages = (overlay as any)['state'].messages || [];
          overlay.setState({
            messages: [...currentMessages, { type: 'success' as const, text: operation.message }]
          });
        }
      } catch (error) {
        allSucceeded = false;
        const errorMessage = error instanceof Error ? error.message : String(error);
        
        // Check for debug data in error (from RPCError)
        if (error && typeof error === 'object' && 'debug' in error) {
          const errorDebug = (error as any).debug;
          // Handle debug data immediately - create overlay for error response with debug
          // Only show debug overlay if debug data exists and has entries
          if (errorDebug && Array.isArray(errorDebug.entries) && errorDebug.entries.length > 0) {
            hasDebugData = true; // Mark that we found debug data
            const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
            handleRPCResponseWithDebug(error, mapping.mcpTool, params);
          }
        }
        
        const operation = {
          mapping: mapping.mcpTool,
          fields,
          success: false,
          error,
          message: `Failed to update ${fields.join(', ')}: ${errorMessage}`
        };
        
        allOperations.push(operation);
        
        // Add error message to overlay immediately
        if (overlay) {
          const currentMessages = (overlay as any)['state'].messages || [];
          overlay.setState({
            messages: [...currentMessages, { type: 'error' as const, text: operation.message }]
          });
        }
      }
    }
    
    return {
      success: allSucceeded,
      noChanges: false,
      operations: allOperations,
      successes: allOperations.filter((op: any) => op.success),
      errors: allOperations.filter((op: any) => !op.success),
      // Return a flag indicating if any operation had debug data (prevents auto-fade)
      debug: hasDebugData ? {} : undefined
    };
  }

  /**
   * Get the URL for a page using the numeric path format.
   * @param pageId The page ID, or null/undefined for root
   * @returns The page URL (e.g., "/1" or "/" for root)
   */
  protected getPageUrl(pageId: number | null | undefined): string {
    if (!pageId) {
      return '/';
    }
    return `/${pageId}`;
  }

  /**
   * Helper method to update the page text div in the DOM.
   * Creates the div if it doesn't exist, updates it if text exists, or removes it if text is empty.
   */
  protected updatePageTextDiv(pageId: number, processedText: string | null | undefined): void {
    let textDiv = document.getElementById(`page-text-${pageId}`) as HTMLDivElement | null;
    
    if (processedText && processedText.trim()) {
      // Text exists - create div if it doesn't exist, then update it
      if (!textDiv) {
        // Find content wrapper or main content area to insert the text div
        const contentWrapper = document.querySelector('.contentWrapper') || document.querySelector('main') || document.body;
        textDiv = document.createElement('div');
        textDiv.id = `page-text-${pageId}`;
        textDiv.className = 'content pageText';
        // Insert after upper_content if it exists, otherwise at the start of content
        const upperContent = contentWrapper.querySelector('.upper_content') || contentWrapper.querySelector('[class*="upper"]');
        if (upperContent && upperContent.nextSibling) {
          contentWrapper.insertBefore(textDiv, upperContent.nextSibling);
        } else {
          contentWrapper.insertBefore(textDiv, contentWrapper.firstChild);
        }
      }
      textDiv.innerHTML = processedText;
    } else {
      // Text is empty - delete the div if it exists
      if (textDiv) {
        textDiv.remove();
      }
    }
  }

  /**
   * Handler for modify_name: Edit page name
   */
  async modify_name(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();
      
      // Request 'name' field with 'form' context to register it for editing
      const currentName = this.getField('name', 'form') || '';

      // Create form HTML with standardized field ID using array-based content structure
      const formHtml = `
          <div class="overlay-form-group">
            <label>Page name:</label>
            <input type="text" id="page-field-name" value="${this.escapeHtml(currentName)}" class="overlay-form-input">
          </div>
      `;

      OverlayManager.getInstance().show({
        header: 'Modify Page Name',
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
            if (result.success && pageId) {
              const nameOp = result.operations?.find((op: any) => op.fields?.includes('name'));
              if (nameOp && nameOp.success && nameOp.result) {
                // nameOp.result is already the extracted data
                const resultPageData = nameOp.result?.page || nameOp.result;
                const newName = resultPageData?.name;
                const newRawText = resultPageData?.text;
                
                if (newName) {
                  this.updateFieldValue('name', newName);
                  if (newRawText !== undefined) {
                    this.updateFieldValue('text', newRawText);
                  }
                  
                  // Update breadcrumb DOM
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
                  
                  // Update page text in case it contains a link to itself
                  try {
                    // Don't pass debug options to get_text - it's just a data fetch
                    const getTextResult = await rpc.call('get_text', { page_id: pageId }, null);
                    const processedText = getTextResult.data?.processed_text;
                    this.updatePageTextDiv(pageId, processedText);
                  } catch (error) {
                    console.error('Failed to fetch updated text after name change:', error);
                  }
                }
              }
            }
            
            return { ...result, _autoFade: true, debug: result.debug };
          } else {
            // Don't throw - errors are already shown in overlay
            return { ...result };
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
      rpc.showError('modify_name', error);
    }
  }

  /**
   * Handler for modify_text: Edit page text content
   */
  async modify_text(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();
      
      // Request 'text' field with 'form' context to register it for editing
      const currentText = this.getField('text', 'form') || '';

      // Create textarea form with standardized field ID using array-based content structure
      const formHtml = `
          <div class="overlay-form-group">
            <textarea id="page-field-text" name="text" rows="20" cols="80" class="overlay-form-textarea">${this.escapeHtml(currentText)}</textarea>
          </div>
      `;

      OverlayManager.getInstance().show({
        header: 'Text Editor',
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
            // After successful submit, fetch processed text and update DOM
            if (result && pageId) {
              try {
                // Don't pass debug options to get_text - it's just a data fetch
                const getTextResult = await rpc.call('get_text', { page_id: pageId }, null);
                const processedText = getTextResult.data?.processed_text;
                
                this.updatePageTextDiv(pageId, processedText);
              } catch (error) {
                console.error('Failed to fetch updated text:', error);
              }
            }
            
            return { ...result, _autoFade: true, debug: result.debug };
          } else {
            // Don't throw - errors are already shown in overlay
            return { ...result, debug: result.debug };
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
      rpc.showError('modify_text', error);
    }
  }

  /**
   * Handler for delete_page: Delete a page with confirmation
   */
  async delete_page(rpc: any): Promise<void> {
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
      rpc.showError('delete_page', error);
    }
  }

  /**
   * Handler for combo: Test form with name/text editable and read-only fields displayed
   */
  async combo(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();
      
      // Get editable fields
      const currentName = this.getField('name', 'form') || '';
      const currentText = this.getField('text', 'form') || '';
      
      // Get read-only fields (these should NOT be registered for editing)
      const pageIdValue = this.getField('id') || '';
      const pageClass = this.getField('class') || '';
      const pageLink = this.getField('link') || '';
      const lastModified = this.getField('last_modified') || '';
      const username = this.getField('username') || '';
      const path = this.getField('path') || [];
      const pathStr = Array.isArray(path) ? path.map((p: any) => p.name).filter(Boolean).join(' / ') : '';
      
      // Create form HTML with editable and read-only fields using array-based content structure
      const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Page name:</label>
            <input type="text" id="page-field-name" value="${this.escapeHtml(currentName)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Page text:</label>
            <textarea id="page-field-text" name="text" rows="10" cols="80" class="overlay-form-textarea">${this.escapeHtml(currentText)}</textarea>
          </div>
      `;

      const readOnlyFieldsHtml = `
          <div class="overlay-form-grid">
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
      `;

      OverlayManager.getInstance().show({
        header: 'Combo Test Form',
        content: [editableFieldsHtml, readOnlyFieldsHtml],
        contentHeaders: ['Editable Fields', 'Read-Only Fields (for display only)'],
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
            if (result.success && pageId) {
              const nameOp = result.operations?.find((op: any) => op.fields?.includes('name'));
              if (nameOp && nameOp.success && nameOp.result) {
                // nameOp.result is already the extracted data
                const resultPageData = nameOp.result?.page || nameOp.result;
                const newName = resultPageData?.name;
                
                if (newName) {
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
              
              const textOp = result.operations?.find((op: any) => op.fields?.includes('text'));
              if (textOp && textOp.success) {
              try {
                // Don't pass debug options to get_text - it's just a data fetch
                const getTextResult = await rpc.call('get_text', { page_id: pageId }, null);
                const processedText = getTextResult.data?.processed_text;
                this.updatePageTextDiv(pageId, processedText);
              } catch (error) {
                console.error('Failed to fetch updated text:', error);
              }
              }
            }
            
            return { ...result, _autoFade: true, debug: result.debug };
          } else {
            // Don't throw - errors are already shown in overlay
            return { ...result, debug: result.debug };
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
      rpc.showError('combo', error);
    }
  }

  /**
   * Handler for add_page: Create a new child page
   */
  async add_page(rpc: any): Promise<void> {
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
            const errorMessage = error instanceof Error ? error.message : String(error);
            throw new Error(`Failed to create page: ${errorMessage}`);
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
   * Handle Upload: Upload images to current page
   */
  async Upload(rpc: any): Promise<void> {
    const { UploadHandler } = await import('./upload-handler.js');
    const handler = new UploadHandler(rpc, getSeedData());
    await handler.handle();
  }
}


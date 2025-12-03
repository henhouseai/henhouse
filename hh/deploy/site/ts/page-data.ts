/**
 * PageData - Base class for managing page data.
 * Pure data model - business logic is in PageManager.
 */

import { PageManager } from './page-manager.js';
import { OverlayManager } from './overlay/overlay-manager.js';
import { getSeedData } from './seed.js';
import { PageActionsFields } from './page-actions-fields.js';
import { PageActionsPages } from './page-actions-pages.js';
import { PageActionsImages } from './page-actions-images.js';

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
        const detailedErrors = (error && typeof error === 'object' && 'errors' in error && Array.isArray((error as any).errors))
          ? (error as any).errors
          : [];
        
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
          message: `Failed to update ${fields.join(', ')}: ${errorMessage}`,
          detailedErrors
        };
        
        allOperations.push(operation);
        
        // Add error message to overlay immediately
        if (overlay) {
          const currentMessages = (overlay as any)['state'].messages || [];
          const newMessages = [{ type: 'error' as const, text: operation.message }];
          if (detailedErrors.length > 0) {
            detailedErrors.forEach((err: { type?: string; content: string }) => {
              newMessages.push({
                type: 'error' as const,
                text: `${err.type || 'error'}: ${err.content}`
              });
            });
          }
          overlay.setState({
            messages: [...currentMessages, ...newMessages]
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
   * Handle Upload: Upload images to current page
   */
  async Upload(rpc: any): Promise<void> {
    const { UploadHandler } = await import('./upload-handler.js');
    const handler = new UploadHandler(rpc, getSeedData());
    await handler.handle();
  }
}

// Apply mixins to PageData class
Object.assign(PageData.prototype, PageActionsFields.prototype);
Object.assign(PageData.prototype, PageActionsPages.prototype);
Object.assign(PageData.prototype, PageActionsImages.prototype);


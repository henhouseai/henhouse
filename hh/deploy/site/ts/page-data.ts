/**
 * PageData - Base class for managing page data with form field registry and smart submission.
 */

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

export class PageData {
  protected data: GetPageResponse;
  protected fieldRegistry: FieldRegistry = {};
  protected dynamicFields: { [key: string]: any } = {};
  
  // Base page fields that are always present
  private static readonly BASE_PAGE_FIELDS = [
    'id', 'name', 'link', 'parent', 'class', 'visibility', 'text',
    'last_modified', 'username', 'comments', 'path'
  ];

  constructor(data: GetPageResponse) {
    this.data = data;
    this.discoverDynamicFields();
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
          this.registerField('text', textValue, 'textarea');
        }
        return textValue;
      
      case 'name':
        // Special breadcrumb/display handling
        const nameValue = this.data.page.name;
        if (context === 'form') {
          this.registerField('name', nameValue, 'text');
        }
        return nameValue;
      
      case 'class':
        // Read-only field
        return this.data.page.class;
      
      default:
        // Check if it's a base page field
        if (fieldName in this.data.page) {
          const value = this.data.page[fieldName];
          if (context === 'form') {
            // Auto-detect field type for base fields
            const fieldType = this.detectFieldType(fieldName, value);
            this.registerField(fieldName, value, fieldType);
          }
          return value;
        }
        
        // Check if it's a dynamic field
        if (fieldName in this.dynamicFields) {
          const value = this.dynamicFields[fieldName];
          if (context === 'form') {
            // Auto-detect field type for dynamic fields
            const fieldType = this.detectFieldType(fieldName, value);
            this.registerField(fieldName, value, fieldType);
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
   * Register a field in the registry
   */
  protected registerField(fieldName: string, originalValue: any, fieldType: 'text' | 'textarea' | 'select' | 'checkbox' | 'number' | 'custom'): void {
    this.fieldRegistry[fieldName] = {
      originalValue,
      extracted: true,
      fieldType,
      domSelector: `#page-field-${fieldName}`
    };
  }

  /**
   * Get list of registered field names
   */
  getRegisteredFields(): string[] {
    return Object.keys(this.fieldRegistry);
  }

  /**
   * Check if a field is registered
   */
  isFieldRegistered(fieldName: string): boolean {
    return fieldName in this.fieldRegistry;
  }

  /**
   * Extract field values from form DOM using standardized selectors
   */
  extractFormValues(): { [fieldName: string]: any } {
    const values: { [fieldName: string]: any } = {};
    
    for (const [fieldName, registry] of Object.entries(this.fieldRegistry)) {
      const element = document.querySelector(registry.domSelector || `#page-field-${fieldName}`) as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
      
      if (element) {
        if (registry.fieldType === 'checkbox') {
          values[fieldName] = (element as HTMLInputElement).checked;
        } else if (registry.fieldType === 'number') {
          values[fieldName] = parseInt((element as HTMLInputElement).value) || 0;
        } else {
          values[fieldName] = element.value;
        }
      }
    }
    
    return values;
  }

  /**
   * Detect which fields have changed from original values
   */
  detectChangedFields(): string[] {
    const currentValues = this.extractFormValues();
    const changed: string[] = [];
    
    for (const [fieldName, registry] of Object.entries(this.fieldRegistry)) {
      const currentValue = currentValues[fieldName];
      const originalValue = registry.originalValue;
      
      // Normalize for comparison
      const normalizedCurrent = this.normalizeValue(currentValue, registry.fieldType);
      const normalizedOriginal = this.normalizeValue(originalValue, registry.fieldType);
      
      if (normalizedCurrent !== normalizedOriginal) {
        changed.push(fieldName);
      }
    }
    
    return changed;
  }

  private normalizeValue(value: any, fieldType: string): string {
    if (value === null || value === undefined) return '';
    if (fieldType === 'number') return String(value);
    if (fieldType === 'checkbox') return String(Boolean(value));
    return String(value).trim();
  }

  /**
   * Submit changes - automatically determines which MCP calls to make
   */
  async submitChanges(rpc: any): Promise<any> {
    const changedFields = this.detectChangedFields();
    
    // Filter out read-only fields like 'class'
    const editableFields = changedFields.filter(field => field !== 'class');
    
    if (editableFields.length === 0) {
      return { success: true, message: 'No changes detected' };
    }

    // Execute all updates in parallel
    const promises = editableFields.map(async (fieldName) => {
      const currentValues = this.extractFormValues();
      const value = currentValues[fieldName];
      
      // Map field name to MCP tool name
      const toolName = this.getMCPToolName(fieldName);
      const params = this.buildMCPParams(fieldName, value);
      
      try {
        const result = await rpc.call(toolName, params);
        // Update registry with new value
        this.fieldRegistry[fieldName].originalValue = value;
        return { field: fieldName, success: true, result };
      } catch (error) {
        return { field: fieldName, success: false, error };
      }
    });

    const results = await Promise.all(promises);
    
    const errors = results.filter(r => !r.success);
    if (errors.length > 0) {
      const errorFields = errors.map(e => e.field).join(', ');
      throw new Error(`Failed to update fields: ${errorFields}`);
    }

    return { success: true, updated: editableFields, results };
  }

  /**
   * Map field names to MCP tool names
   */
  protected getMCPToolName(fieldName: string): string {
    // Special cases for base page fields
    const toolMap: { [key: string]: string } = {
      'name': 'modify_name',
      'text': 'modify_text',
      'visibility': 'modify_page'
    };
    
    if (toolMap[fieldName]) {
      return toolMap[fieldName];
    }
    
    // For dynamic fields, try modify_<field_name> convention
    // This will need to be adjusted based on actual MCP tool naming
    return `modify_${fieldName}`;
  }

  /**
   * Build MCP parameters for a field update
   */
  protected buildMCPParams(fieldName: string, value: any): any {
    const baseParams: any = {
      page_id: this.id
    };
    
    // Special handling for known base fields
    if (fieldName === 'name') {
      baseParams.name = value;
    } else if (fieldName === 'text') {
      baseParams.text = value;
    } else if (fieldName === 'visibility') {
      baseParams.visibility = value;
    } else {
      // Generic handling for dynamic fields
      baseParams[fieldName] = value;
    }
    
    return baseParams;
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
}


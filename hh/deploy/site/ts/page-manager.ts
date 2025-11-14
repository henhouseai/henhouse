/**
 * PageManager - Singleton manager for current page data.
 * Central authority for field registry, mappings, change detection, and submission.
 */

import { PageData, FieldRegistry, FieldMapping } from './page-data.js';

export class PageManager {
  private static instance: PageManager | null = null;
  private currentPageData: PageData | null = null;
  private fieldRegistry: FieldRegistry = {};
  private fieldMappings: FieldMapping[] = [];

  private constructor() {
    // Private constructor for singleton pattern
  }

  /**
   * Get the singleton instance of PageManager.
   */
  static getInstance(): PageManager {
    if (!PageManager.instance) {
      PageManager.instance = new PageManager();
    }
    return PageManager.instance;
  }

  /**
   * Set the current page data and clear registries.
   */
  setPageData(pageData: PageData): void {
    this.currentPageData = pageData;
    this.fieldRegistry = {};
    this.fieldMappings = [];
  }

  /**
   * Get the current page data.
   */
  getPageData(): PageData | null {
    return this.currentPageData;
  }

  /**
   * Clear the current page data and registries.
   */
  clearPageData(): void {
    this.currentPageData = null;
    this.fieldRegistry = {};
    this.fieldMappings = [];
  }

  /**
   * Register field mappings from a PageData class.
   * Called by PageData constructors to contribute their mappings.
   */
  registerFieldMappings(mappings: FieldMapping[]): void {
    this.fieldMappings.push(...mappings);
  }

  /**
   * Register a field in the registry for editing.
   */
  registerField(fieldName: string, originalValue: any, fieldType: 'text' | 'textarea' | 'select' | 'checkbox' | 'number' | 'custom'): void {
    this.fieldRegistry[fieldName] = {
      originalValue,
      extracted: true,
      fieldType,
      domSelector: `#page-field-${fieldName}`
    };
  }

  /**
   * Get list of registered field names.
   */
  getRegisteredFields(): string[] {
    return Object.keys(this.fieldRegistry);
  }

  /**
   * Check if a field is registered.
   */
  isFieldRegistered(fieldName: string): boolean {
    return fieldName in this.fieldRegistry;
  }

  /**
   * Clear specific fields from the registry (after successful update or form close).
   */
  clearFields(fieldNames: string[]): void {
    for (const fieldName of fieldNames) {
      delete this.fieldRegistry[fieldName];
    }
  }

  /**
   * Clear all fields from the registry (when form is closed without submitting).
   */
  clearFieldRegistry(): void {
    this.fieldRegistry = {};
  }

  /**
   * Extract field values from form DOM using standardized selectors.
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
   * Detect which fields have changed from original values.
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
    return String(value);
  }

  /**
   * Select optimal MCP calls based on changed fields.
   * Algorithm: Weighted Set Cover with Exact Match Preference
   * - Prefer exact matches (priority 0)
   * - Prefer smaller groups over larger ones
   * - Avoid setting fields that don't need to be set
   */
  selectOptimalMappings(changedFields: string[]): Array<{ mapping: FieldMapping; fields: string[] }> {
    const selected: Array<{ mapping: FieldMapping; fields: string[] }> = [];
    const covered = new Set<string>();
    
    // Sort mappings by priority (lower = better), then by size (smaller = better)
    const sortedMappings = [...this.fieldMappings].sort((a, b) => {
      if (a.priority !== b.priority) return a.priority - b.priority;
      return a.fields.length - b.fields.length;
    });
    
    // Greedy selection: pick mappings that cover the most uncovered fields
    while (covered.size < changedFields.length) {
      let bestMapping: FieldMapping | null = null;
      let bestFields: string[] = [];
      let bestScore = -1;
      
      for (const mapping of sortedMappings) {
        // Find which fields from this mapping are in changedFields and not yet covered
        const uncoveredFields = mapping.fields.filter(f => 
          changedFields.includes(f) && !covered.has(f)
        );
        
        if (uncoveredFields.length === 0) continue;
        
        // Score: prefer exact matches (all fields in mapping are changed and uncovered)
        const isExactMatch = uncoveredFields.length === mapping.fields.length && 
                            mapping.fields.every(f => changedFields.includes(f));
        const score = isExactMatch ? 1000 - mapping.priority : uncoveredFields.length - mapping.priority;
        
        if (score > bestScore) {
          bestScore = score;
          bestMapping = mapping;
          bestFields = uncoveredFields;
        }
      }
      
      if (!bestMapping) {
        // No mapping found for remaining fields - this shouldn't happen if mappings are complete
        const uncovered = changedFields.filter(f => !covered.has(f));
        console.warn(`No mapping found for fields: ${uncovered.join(', ')}`);
        break;
      }
      
      selected.push({ mapping: bestMapping, fields: bestFields });
      bestFields.forEach(f => covered.add(f));
    }
    
    return selected;
  }

  /**
   * Submit changes - automatically determines which MCP calls to make using optimal mapping algorithm.
   * Returns detailed results for each operation.
   */
  async submitChanges(rpc: any): Promise<any> {
    const changedFields = this.detectChangedFields();
    
    // Filter out read-only fields like 'class'
    const editableFields = changedFields.filter(field => field !== 'class');
    
    if (editableFields.length === 0) {
      return { 
        success: true, 
        noChanges: true,
        message: 'No changes made'
      };
    }
    
    // Select optimal MCP calls
    const optimalMappings = this.selectOptimalMappings(editableFields);
    const currentValues = this.extractFormValues();
    const pageId = this.currentPageData?.id;
    
    if (!pageId) {
      throw new Error('No page ID available');
    }
    
    // Execute all MCP calls in parallel
    const promises = optimalMappings.map(async ({ mapping, fields }) => {
      const params = mapping.buildParams(fields, currentValues, pageId);
      
      try {
        const result = await rpc.call(mapping.mcpTool, params);
        // Clear fields from registry after successful update (they're no longer "checked out")
        this.clearFields(fields);
        
        // Update internal PageData with new values
        fields.forEach(fieldName => {
          if (fieldName in currentValues && this.currentPageData) {
            this.currentPageData.updateFieldValue(fieldName, currentValues[fieldName]);
          }
        });
        
        return { 
          mapping: mapping.mcpTool, 
          fields, 
          success: true, 
          result,
          message: `Successfully updated ${fields.join(', ')}`
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { 
          mapping: mapping.mcpTool, 
          fields, 
          success: false, 
          error,
          message: `Failed to update ${fields.join(', ')}: ${errorMessage}`
        };
      }
    });
    
    const results = await Promise.all(promises);
    const successes = results.filter(r => r.success);
    const errors = results.filter(r => !r.success);
    const allSucceeded = errors.length === 0;
    
    // Build combined message
    const messages: string[] = [];
    if (successes.length > 0) {
      messages.push(...successes.map(r => r.message));
    }
    if (errors.length > 0) {
      messages.push(...errors.map(r => r.message));
    }
    const combinedMessage = messages.join('\n');
    
    return {
      success: allSucceeded,
      noChanges: false,
      operations: results,
      successes: successes,
      errors: errors,
      message: combinedMessage
    };
  }
}


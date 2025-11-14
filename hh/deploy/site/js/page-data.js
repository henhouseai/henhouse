/**
 * PageData - Base class for managing page data with form field registry and smart submission.
 */
export class PageData {
    constructor(data) {
        this.fieldRegistry = {};
        this.dynamicFields = {};
        this.data = data;
        this.discoverDynamicFields();
    }
    /**
     * Discover dynamic fields that aren't in the base page fields list
     */
    discoverDynamicFields() {
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
    getField(fieldName, context = 'display') {
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
    detectFieldType(fieldName, value) {
        if (typeof value === 'boolean')
            return 'checkbox';
        if (typeof value === 'number')
            return 'number';
        if (typeof value === 'string' && value.length > 100)
            return 'textarea';
        return 'text';
    }
    /**
     * Register a field in the registry
     */
    registerField(fieldName, originalValue, fieldType) {
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
    getRegisteredFields() {
        return Object.keys(this.fieldRegistry);
    }
    /**
     * Check if a field is registered
     */
    isFieldRegistered(fieldName) {
        return fieldName in this.fieldRegistry;
    }
    /**
     * Extract field values from form DOM using standardized selectors
     */
    extractFormValues() {
        const values = {};
        for (const [fieldName, registry] of Object.entries(this.fieldRegistry)) {
            const element = document.querySelector(registry.domSelector || `#page-field-${fieldName}`);
            if (element) {
                if (registry.fieldType === 'checkbox') {
                    values[fieldName] = element.checked;
                }
                else if (registry.fieldType === 'number') {
                    values[fieldName] = parseInt(element.value) || 0;
                }
                else {
                    values[fieldName] = element.value;
                }
            }
        }
        return values;
    }
    /**
     * Detect which fields have changed from original values
     */
    detectChangedFields() {
        const currentValues = this.extractFormValues();
        const changed = [];
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
    normalizeValue(value, fieldType) {
        if (value === null || value === undefined)
            return '';
        if (fieldType === 'number')
            return String(value);
        if (fieldType === 'checkbox')
            return String(Boolean(value));
        return String(value).trim();
    }
    /**
     * Get field-to-MCP mappings for this page class.
     * Derived classes should override this to provide their specific mappings.
     * Base class provides mappings for common page fields.
     */
    getFieldMappings() {
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
     * Select optimal MCP calls based on changed fields.
     * Algorithm: Weighted Set Cover with Exact Match Preference
     * - Prefer exact matches (priority 0)
     * - Prefer smaller groups over larger ones
     * - Avoid setting fields that don't need to be set
     */
    selectOptimalMappings(changedFields) {
        const allMappings = this.getFieldMappings();
        const selected = [];
        const covered = new Set();
        // Sort mappings by priority (lower = better), then by size (smaller = better)
        const sortedMappings = [...allMappings].sort((a, b) => {
            if (a.priority !== b.priority)
                return a.priority - b.priority;
            return a.fields.length - b.fields.length;
        });
        // Greedy selection: pick mappings that cover the most uncovered fields
        while (covered.size < changedFields.length) {
            let bestMapping = null;
            let bestFields = [];
            let bestScore = -1;
            for (const mapping of sortedMappings) {
                // Find which fields from this mapping are in changedFields and not yet covered
                const uncoveredFields = mapping.fields.filter(f => changedFields.includes(f) && !covered.has(f));
                if (uncoveredFields.length === 0)
                    continue;
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
     * Submit changes - automatically determines which MCP calls to make using optimal mapping algorithm
     */
    async submitChanges(rpc) {
        const changedFields = this.detectChangedFields();
        // Filter out read-only fields like 'class'
        const editableFields = changedFields.filter(field => field !== 'class');
        if (editableFields.length === 0) {
            return { success: true, message: 'No changes detected' };
        }
        // Select optimal MCP calls
        const optimalMappings = this.selectOptimalMappings(editableFields);
        const currentValues = this.extractFormValues();
        // Execute all MCP calls in parallel
        const promises = optimalMappings.map(async ({ mapping, fields }) => {
            const params = mapping.buildParams(fields, currentValues, this.id);
            try {
                const result = await rpc.call(mapping.mcpTool, params);
                // Update registry with new values for all fields in this mapping
                fields.forEach(fieldName => {
                    if (this.fieldRegistry[fieldName]) {
                        this.fieldRegistry[fieldName].originalValue = currentValues[fieldName];
                    }
                });
                return { mapping: mapping.mcpTool, fields, success: true, result };
            }
            catch (error) {
                return { mapping: mapping.mcpTool, fields, success: false, error };
            }
        });
        const results = await Promise.all(promises);
        const errors = results.filter(r => !r.success);
        if (errors.length > 0) {
            const errorDetails = errors.map(e => `${e.mapping}(${e.fields.join(', ')})`).join(', ');
            throw new Error(`Failed to update: ${errorDetails}`);
        }
        return { success: true, updated: editableFields, operations: results };
    }
    /**
     * Map field names to MCP tool names (legacy method - kept for backward compatibility)
     * New code should use getFieldMappings() instead
     */
    getMCPToolName(fieldName) {
        const mappings = this.getFieldMappings();
        // Find first mapping that includes this field
        for (const mapping of mappings) {
            if (mapping.fields.includes(fieldName)) {
                return mapping.mcpTool;
            }
        }
        // Fallback to modify_<field_name> convention
        return `modify_${fieldName}`;
    }
    /**
     * Build MCP parameters for a field update (legacy method - kept for backward compatibility)
     * New code should use FieldMapping.buildParams instead
     */
    buildMCPParams(fieldName, value) {
        const mappings = this.getFieldMappings();
        // Find first mapping that includes this field
        for (const mapping of mappings) {
            if (mapping.fields.includes(fieldName)) {
                return mapping.buildParams([fieldName], { [fieldName]: value }, this.id);
            }
        }
        // Fallback
        return {
            page_id: this.id,
            [fieldName]: value
        };
    }
    /**
     * Get page ID (convenience method)
     */
    get id() {
        return this.data.page.id;
    }
    // ===== Images Helpers =====
    getImages() {
        return this.data.images || [];
    }
    getImageCount() {
        return this.data.images?.length || 0;
    }
    getPrimaryImage() {
        return this.data.images && this.data.images.length > 0 ? this.data.images[0] : null;
    }
    getImageByRank(rank) {
        return this.data.images?.find(img => img.image_rank === rank) || null;
    }
    // ===== Children Helpers =====
    getChildrenByClass() {
        return this.data.children_by_class || {};
    }
    getChildrenForClass(className) {
        const classData = this.data.children_by_class?.[className];
        return classData?.children || [];
    }
    getAllChildren() {
        const all = [];
        for (const classData of Object.values(this.data.children_by_class || {})) {
            all.push(...(classData.children || []));
        }
        return all;
    }
    getChildCount() {
        return this.getAllChildren().length;
    }
    getChildCountForClass(className) {
        return this.getChildrenForClass(className).length;
    }
    // ===== Path/Breadcrumb Helpers =====
    getBreadcrumbPath() {
        return this.data.page.path || [];
    }
    getBreadcrumbNames() {
        return this.getBreadcrumbPath().map(p => p.name || '').filter(n => n.length > 0);
    }
    // ===== Raw Data Access =====
    getRawData() {
        return this.data;
    }
    getPageData() {
        return this.data.page;
    }
}
// Base page fields that are always present
PageData.BASE_PAGE_FIELDS = [
    'id', 'name', 'link', 'parent', 'class', 'visibility', 'text',
    'last_modified', 'username', 'comments', 'path'
];

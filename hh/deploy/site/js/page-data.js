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
     * Submit changes - automatically determines which MCP calls to make
     */
    async submitChanges(rpc) {
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
            }
            catch (error) {
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
    getMCPToolName(fieldName) {
        // Special cases for base page fields
        const toolMap = {
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
    buildMCPParams(fieldName, value) {
        const baseParams = {
            page_id: this.id
        };
        // Special handling for known base fields
        if (fieldName === 'name') {
            baseParams.name = value;
        }
        else if (fieldName === 'text') {
            baseParams.text = value;
        }
        else if (fieldName === 'visibility') {
            baseParams.visibility = value;
        }
        else {
            // Generic handling for dynamic fields
            baseParams[fieldName] = value;
        }
        return baseParams;
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

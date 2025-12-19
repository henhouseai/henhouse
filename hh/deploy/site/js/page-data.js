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
import { PageActionsFiles } from './page-actions-files.js';
import { PageActionsAudio } from './page-actions-audio.js';
import { PageActionsVideo } from './page-actions-video.js';
export class PageData {
    constructor(data) {
        this.dynamicFields = {};
        // Read-only fields that can be accessed but not edited
        this.readOnlyFields = new Set([
            'id',
            'class',
            'link',
            'last_modified',
            'username',
            'path'
        ]);
        this.data = data;
        this.discoverDynamicFields();
        // Register field mappings with PageManager
        const pageManager = PageManager.getInstance();
        pageManager.registerFieldMappings(this.getFieldMappings());
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
     * Update internal data with new field value after successful update
     * This ensures the next form shows the updated value, not the old one
     */
    updateFieldValue(fieldName, newValue) {
        // Check if it's a base page field
        if (fieldName in this.data.page) {
            this.data.page[fieldName] = newValue;
        }
        else {
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
            },
            {
                fields: ['visibility'],
                mcpTool: 'set_page_visibility',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    visibility: values['visibility']
                })
            },
            {
                fields: ['displayStyle'],
                mcpTool: 'set_page_display_style',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    display_style: values['displayStyle']
                })
            }
            // Derived classes can add more mappings here
        ];
    }
    /**
     * Public method to get field mappings (for PageManager access).
     */
    getFieldMappingsPublic() {
        return this.getFieldMappings();
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
    // ===== Handler Methods =====
    // These are UI handlers for page-specific CRUD operations
    // They accept RPC client as parameter and use PageManager for business logic
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    /**
     * Process operations incrementally, updating overlay as each completes.
     * Returns final result with all operations.
     */
    async processOperationsIncrementally(rpc, optimalMappings, currentValues, pageId) {
        const overlayManager = OverlayManager.getInstance();
        const overlay = overlayManager.getTopOverlay();
        // Capture debug options once at the start (before any RPC calls)
        // This ensures all calls in the loop use the same debug options
        let capturedDebugOptions = null;
        if (overlay) {
            capturedDebugOptions = overlay.getDebugOptions();
        }
        const allOperations = [];
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
                fields.forEach((fieldName) => {
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
                    const currentMessages = overlay['state'].messages || [];
                    overlay.setState({
                        messages: [...currentMessages, { type: 'success', text: operation.message }]
                    });
                }
            }
            catch (error) {
                allSucceeded = false;
                const errorMessage = error instanceof Error ? error.message : String(error);
                const detailedErrors = (error && typeof error === 'object' && 'errors' in error && Array.isArray(error.errors))
                    ? error.errors
                    : [];
                // Check for debug data in error (from RPCError)
                if (error && typeof error === 'object' && 'debug' in error) {
                    const errorDebug = error.debug;
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
                    const currentMessages = overlay['state'].messages || [];
                    const newMessages = [{ type: 'error', text: operation.message }];
                    if (detailedErrors.length > 0) {
                        detailedErrors.forEach((err) => {
                            newMessages.push({
                                type: 'error',
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
            successes: allOperations.filter((op) => op.success),
            errors: allOperations.filter((op) => !op.success),
            // Return a flag indicating if any operation had debug data (prevents auto-fade)
            debug: hasDebugData ? {} : undefined
        };
    }
    /**
     * Get the URL for a page using the numeric path format.
     * @param pageId The page ID, or null/undefined for root
     * @returns The page URL (e.g., "/1" or "/" for root)
     */
    getPageUrl(pageId) {
        if (!pageId) {
            return '/';
        }
        return `/${pageId}`;
    }
    /**
     * Helper method to update the page text div in the DOM.
     * Creates the div if it doesn't exist, updates it if text exists, or removes it if text is empty.
     */
    updatePageTextDiv(pageId, processedText) {
        let textDiv = document.getElementById(`page-text-${pageId}`);
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
                }
                else {
                    contentWrapper.insertBefore(textDiv, contentWrapper.firstChild);
                }
            }
            textDiv.innerHTML = processedText;
        }
        else {
            // Text is empty - delete the div if it exists
            if (textDiv) {
                textDiv.remove();
            }
        }
    }
    /**
     * Handle Upload: Upload images to current page
     */
    async Upload(rpc) {
        const { UploadHandler } = await import('./upload-handler.js');
        const handler = new UploadHandler(rpc, getSeedData());
        await handler.handle();
    }
    /**
     * Handle upload_audio_app: Upload audio files to current page
     */
    async upload_audio_app(rpc) {
        const { UploadHandler } = await import('./upload-handler.js');
        const handler = new UploadHandler(rpc, getSeedData(), 'audio');
        await handler.handle();
    }
    /**
     * Handle upload_video_app: Upload video files to current page
     */
    async upload_video_app(rpc) {
        const { UploadHandler } = await import('./upload-handler.js');
        const handler = new UploadHandler(rpc, getSeedData(), 'video');
        await handler.handle();
    }
}
// Base page fields that are always present
PageData.BASE_PAGE_FIELDS = [
    'id', 'name', 'link', 'parent', 'class', 'visibility', 'text',
    'last_modified', 'username', 'comments', 'path'
];
// Apply mixins to PageData class
function applyMixin(target, source) {
    const sourcePrototype = source.prototype;
    const targetPrototype = target.prototype;
    // Get all property names from source prototype
    const propertyNames = Object.getOwnPropertyNames(sourcePrototype);
    for (const name of propertyNames) {
        // Skip constructor
        if (name === 'constructor') {
            continue;
        }
        // Get property descriptor
        const descriptor = Object.getOwnPropertyDescriptor(sourcePrototype, name);
        if (descriptor && typeof descriptor.value === 'function') {
            // Copy method to target prototype
            targetPrototype[name] = descriptor.value;
        }
    }
}
applyMixin(PageData, PageActionsFields);
applyMixin(PageData, PageActionsPages);
applyMixin(PageData, PageActionsImages);
applyMixin(PageData, PageActionsFiles);
applyMixin(PageData, PageActionsAudio);
applyMixin(PageData, PageActionsVideo);

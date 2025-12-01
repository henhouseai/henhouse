/**
 * RPC Client - custom MCP wrapper for JSON-RPC calls to the backend.
 */
import { PageDataFactory } from './page-data-factory.js';
import { OverlayManager } from './overlay/overlay-manager.js';
/**
 * Custom error class that can hold multiple error messages
 */
export class RPCError extends Error {
    constructor(message, code, errors = []) {
        super(message);
        this.name = 'RPCError';
        this.code = code;
        this.errors = errors;
        // Don't format multiple errors into one message - keep them separate
    }
}
export class RPCClient {
    /**
     * Extract and parse MCP response data from the envelope.
     * MCP responses have structure: { content: [{ type: "text", text: "<JSON_STRING>" }] }
     * Now parses ALL content items to extract both main data and debug data.
     */
    extractMCPData(result) {
        const response = { data: null };
        if (result && result.content && Array.isArray(result.content)) {
            // Parse all content items
            for (const contentItem of result.content) {
                if (contentItem.type === 'text' && typeof contentItem.text === 'string') {
                    try {
                        const parsed = JSON.parse(contentItem.text);
                        // Check if this is debug data (has "entries" array)
                        if (parsed && Array.isArray(parsed.entries)) {
                            response.debug = parsed;
                        }
                        else if (response.data === null) {
                            // First non-debug content item is the main data
                            response.data = parsed;
                        }
                    }
                    catch (e) {
                        // If parsing fails, skip this content item
                        console.warn('Failed to parse MCP content item:', e);
                    }
                }
            }
        }
        // Fallback: if no data extracted, return result as-is
        if (response.data === null) {
            response.data = result;
        }
        return response;
    }
    /**
     * Make an MCP JSON-RPC call to the backend.
     * @param method - The tool name to call
     * @param params - Parameters to pass (debug options will be automatically added if set in overlay)
     * @param debugOptions - Optional debug options to use (overrides overlay lookup)
     * @returns Object with data and optional debug info
     */
    async call(method, params = {}, debugOptions) {
        // Store original params before merging debug options (for request info display)
        const originalParams = { ...params };
        // Use provided debugOptions, or check current overlay for debug options
        if (!debugOptions) {
            const overlayManager = OverlayManager.getInstance();
            const topOverlay = overlayManager.getTopOverlay();
            if (topOverlay) {
                debugOptions = topOverlay.getDebugOptions();
            }
        }
        // Merge debug options into params (don't overwrite existing params)
        if (debugOptions) {
            if (debugOptions.debug) {
                params.debug = 1;
            }
            if (debugOptions.log) {
                params.log = 1;
            }
            if (debugOptions.white) {
                params.white = debugOptions.white;
            }
            if (debugOptions.gray) {
                params.gray = debugOptions.gray;
            }
            if (debugOptions.black) {
                params.black = debugOptions.black;
            }
            if (debugOptions.debugLimit) {
                params['debug-limit'] = debugOptions.debugLimit;
            }
        }
        // Use tools/call structure: method is the tool name, params go in arguments
        const payload = {
            jsonrpc: '2.0',
            id: Date.now(),
            method: 'tools/call',
            params: {
                name: method,
                arguments: params
            }
        };
        try {
            const response = await fetch('/mcp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (data.error) {
                // Extract all errors from error.data.errors if available
                const allErrors = [];
                if (data.error.data?.errors && Array.isArray(data.error.data.errors)) {
                    for (const err of data.error.data.errors) {
                        if (typeof err.content === 'string') {
                            allErrors.push({
                                type: err.type || 'error',
                                content: err.content
                            });
                        }
                    }
                }
                // Also check for debug data in error.data.content
                let debugData;
                if (data.error.data?.content && Array.isArray(data.error.data.content)) {
                    for (const contentItem of data.error.data.content) {
                        if (contentItem.type === 'text' && typeof contentItem.text === 'string') {
                            try {
                                const parsed = JSON.parse(contentItem.text);
                                if (parsed && Array.isArray(parsed.entries)) {
                                    debugData = parsed;
                                    break;
                                }
                            }
                            catch (e) {
                                // Skip if not valid JSON
                            }
                        }
                    }
                }
                // If we have multiple errors, use RPCError to format them nicely
                if (allErrors.length > 1) {
                    const error = new RPCError(`RPC error: ${data.error.message}`, data.error.code, allErrors);
                    error.debug = debugData;
                    error.requestInfo = { method, params: originalParams };
                    throw error;
                }
                else if (allErrors.length === 1) {
                    // Single error - use the detailed error content if available
                    const error = new RPCError(`RPC error: ${allErrors[0].type}: ${allErrors[0].content}`, data.error.code, allErrors);
                    error.debug = debugData;
                    error.requestInfo = { method, params: originalParams };
                    throw error;
                }
                else {
                    // Fallback to message only
                    const error = new RPCError(`RPC error: ${data.error.message}`, data.error.code);
                    error.debug = debugData;
                    error.requestInfo = { method, params: originalParams };
                    throw error;
                }
            }
            // Extract data and debug from result
            const result = this.extractMCPData(data.result);
            // Add request info to result
            if (result.debug) {
                result.requestInfo = { method, params: originalParams };
            }
            return result;
        }
        catch (error) {
            console.error(`RPC call failed for ${method}:`, error);
            throw error;
        }
    }
    /**
     * Get page data and return as PageData instance.
     * This is the recommended way to fetch page data.
     */
    async getPage(pageId, debugOptions) {
        // Convert to number for schema validation (schema expects integer)
        const id = typeof pageId === 'string' ? parseInt(pageId, 10) : pageId;
        const params = { id };
        if (debugOptions) {
            Object.assign(params, debugOptions);
        }
        const result = await this.call('get_page', params);
        if (!result.data || !result.data.page) {
            throw new Error('Invalid page data response: missing page object');
        }
        // Use factory to create appropriate derived class
        return PageDataFactory.create(result.data);
    }
    /**
     * Display an error message to the user.
     */
    showError(label, error) {
        // Create an overlay window to display the error
        // This replaces the old temporary error box behavior
        const overlayManager = OverlayManager.getInstance();
        // Check if it's an RPCError with multiple errors
        let errorMessages = [];
        if (error && typeof error === 'object' && 'errors' in error && Array.isArray(error.errors) && error.errors.length > 0) {
            // RPCError with multiple errors - extract all of them
            const rpcError = error;
            errorMessages = rpcError.errors.map((err) => ({
                type: 'error',
                text: `${err.type}: ${err.content}`
            }));
            // Also add the main error message if present
            if (rpcError.message) {
                errorMessages.unshift({
                    type: 'error',
                    text: rpcError.message
                });
            }
        }
        else {
            // Single error
            const errorMessage = error instanceof Error ? error.message : String(error);
            errorMessages = [{
                    type: 'error',
                    text: errorMessage
                }];
        }
        // Create error content - each error as a separate red div
        const errorContent = errorMessages.map(msg => {
            return `<div class="overlayError">${this.escapeHtml(msg.text)}</div>`;
        });
        overlayManager.show({
            header: `Error: ${label}`,
            content: errorContent,
            contentHeaders: errorContent.map(() => ''), // Empty headers for each error div
            closable: true,
            cancelLabel: 'Close',
            showSubmit: false // No submit button, just close
        });
    }
    /**
     * Escape HTML to prevent XSS.
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

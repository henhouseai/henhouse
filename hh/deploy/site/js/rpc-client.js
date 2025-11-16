/**
 * RPC Client - custom MCP wrapper for JSON-RPC calls to the backend.
 */
import { PageDataFactory } from './page-data-factory.js';
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
     * @param params - Parameters to pass (can include debug options)
     * @returns Object with data and optional debug info
     */
    async call(method, params = {}) {
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
                    throw error;
                }
                else if (allErrors.length === 1) {
                    // Single error - use the detailed error content if available
                    const error = new RPCError(`RPC error: ${allErrors[0].type}: ${allErrors[0].content}`, data.error.code, allErrors);
                    error.debug = debugData;
                    throw error;
                }
                else {
                    // Fallback to message only
                    const error = new RPCError(`RPC error: ${data.error.message}`, data.error.code);
                    error.debug = debugData;
                    throw error;
                }
            }
            // Extract data and debug from result
            return this.extractMCPData(data.result);
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
        const errorBox = document.createElement('div');
        errorBox.className = 'hh-error';
        errorBox.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #2a1a1a;
      color: #ff6b6b;
      padding: 15px 20px;
      border: 2px solid #ff6b6b;
      border-radius: 4px;
      z-index: 10000;
      font-family: monospace;
      font-size: 13px;
      max-width: 500px;
      white-space: pre-wrap;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;
        const errorMessage = error instanceof Error ? error.message : String(error);
        errorBox.textContent = `[${label}] Error:\n${errorMessage}`;
        const container = document.body || document.documentElement;
        container.appendChild(errorBox);
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (errorBox.parentNode) {
                errorBox.parentNode.removeChild(errorBox);
            }
        }, 10000);
    }
}

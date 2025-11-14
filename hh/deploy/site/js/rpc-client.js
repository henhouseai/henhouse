/**
 * RPC Client - custom MCP wrapper for JSON-RPC calls to the backend.
 */
import { PageDataFactory } from './page-data-factory.js';
export class RPCClient {
    /**
     * Extract and parse MCP response data from the envelope.
     * MCP responses have structure: { content: [{ type: "text", text: "<JSON_STRING>" }] }
     */
    extractMCPData(result) {
        // Handle MCP envelope structure
        if (result && result.content && Array.isArray(result.content) && result.content.length > 0) {
            const contentItem = result.content[0];
            if (contentItem.type === 'text' && typeof contentItem.text === 'string') {
                try {
                    return JSON.parse(contentItem.text);
                }
                catch (e) {
                    throw new Error(`Failed to parse MCP response JSON: ${e}`);
                }
            }
        }
        // Handle case where result is a JSON string (not wrapped in envelope)
        if (typeof result === 'string') {
            try {
                return JSON.parse(result);
            }
            catch (e) {
                // If parsing fails, return as-is
                return result;
            }
        }
        // Return result as-is (for already-parsed data)
        return result;
    }
    /**
     * Make an MCP JSON-RPC call to the backend.
     */
    async call(method, params = {}) {
        const payload = {
            jsonrpc: '2.0',
            id: Date.now(),
            method,
            params: params || {}
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
                throw new Error(`RPC error: ${data.error.message}`);
            }
            return data.result;
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
    async getPage(pageId) {
        const result = await this.call('get_page', { id: String(pageId) });
        const parsedData = this.extractMCPData(result);
        if (!parsedData || !parsedData.page) {
            throw new Error('Invalid page data response: missing page object');
        }
        // Use factory to create appropriate derived class
        return PageDataFactory.create(parsedData);
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

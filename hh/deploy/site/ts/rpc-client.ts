/**
 * RPC Client - custom MCP wrapper for JSON-RPC calls to the backend.
 */

import { PageData, GetPageResponse } from './page-data.js';
import { PageDataFactory } from './page-data-factory.js';

export interface RPCRequest {
  jsonrpc: string;
  id: number;
  method: string;
  params: any;
}

export interface RPCResponse {
  jsonrpc: string;
  id: number;
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: {
      errors?: Array<{
        type: string;
        content: string;
        timestamp?: string;
      }>;
    };
  };
}

/**
 * Custom error class that can hold multiple error messages
 */
export class RPCError extends Error {
  public errors: Array<{ type: string; content: string }>;
  public code: number;

  constructor(message: string, code: number, errors: Array<{ type: string; content: string }> = []) {
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
   */
  extractMCPData(result: any): any {
    if (result && result.content && Array.isArray(result.content) && result.content.length > 0) {
      const contentItem = result.content[0];
      if (contentItem.type === 'text' && typeof contentItem.text === 'string') {
        try {
          return JSON.parse(contentItem.text);
        } catch (e) {
          throw new Error(`Failed to parse MCP response JSON: ${e}`);
        }
      }
    }
    // Fallback: return result as-is (for non-MCP responses or already-parsed data)
    return result;
  }

  /**
   * Make an MCP JSON-RPC call to the backend.
   */
  async call(method: string, params: any = {}): Promise<any> {
    // Always include debug=1 to see debug output in responses
    const argumentsWithDebug = { ...params, debug: 1 };
    
    // Use tools/call structure: method is the tool name, params go in arguments
    const payload: RPCRequest = {
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: {
        name: method,
        arguments: argumentsWithDebug
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

      const data: RPCResponse = await response.json();

      if (data.error) {
        // Extract all errors from error.data.errors if available
        const allErrors: Array<{ type: string; content: string }> = [];
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
        
        // If we have multiple errors, use RPCError to format them nicely
        if (allErrors.length > 1) {
          throw new RPCError(`RPC error: ${data.error.message}`, data.error.code, allErrors);
        } else if (allErrors.length === 1) {
          // Single error - use the detailed error content if available
          throw new RPCError(`RPC error: ${allErrors[0].type}: ${allErrors[0].content}`, data.error.code, allErrors);
        } else {
          // Fallback to message only
          throw new RPCError(`RPC error: ${data.error.message}`, data.error.code);
        }
      }

      return data.result;
    } catch (error) {
      console.error(`RPC call failed for ${method}:`, error);
      throw error;
    }
  }

  /**
   * Get page data and return as PageData instance.
   * This is the recommended way to fetch page data.
   */
  async getPage(pageId: number | string): Promise<PageData> {
    // Convert to number for schema validation (schema expects integer)
    const id = typeof pageId === 'string' ? parseInt(pageId, 10) : pageId;
    const result = await this.call('get_page', { id });
    const parsedData = this.extractMCPData(result) as GetPageResponse;
    
    if (!parsedData || !parsedData.page) {
      throw new Error('Invalid page data response: missing page object');
    }
    
    // Use factory to create appropriate derived class
    return PageDataFactory.create(parsedData);
  }

  /**
   * Display an error message to the user.
   */
  showError(label: string, error: any): void {
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


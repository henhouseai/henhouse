/**
 * RPC Client - custom MCP wrapper for JSON-RPC calls to the backend.
 */

import { PageData, GetPageResponse } from './page-data.js';
import { PageDataFactory } from './page-data-factory.js';
import { DebugData } from './overlay-debug-table.js';
import { OverlayManager } from './overlay-manager.js';

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
      content?: Array<{
        type: string;
        text: string;
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

export interface RPCCallResult {
  data: any;
  debug?: DebugData;
  requestInfo?: {
    method: string;
    params: any;
  };
}

export class RPCClient {
  /**
   * Extract and parse MCP response data from the envelope.
   * MCP responses have structure: { content: [{ type: "text", text: "<JSON_STRING>" }] }
   * Now parses ALL content items to extract both main data and debug data.
   */
  extractMCPData(result: any): RPCCallResult {
    const response: RPCCallResult = { data: null };
    
    if (result && result.content && Array.isArray(result.content)) {
      // Parse all content items
      for (const contentItem of result.content) {
      if (contentItem.type === 'text' && typeof contentItem.text === 'string') {
        try {
            const parsed = JSON.parse(contentItem.text);
            // Check if this is debug data (has "entries" array)
            if (parsed && Array.isArray(parsed.entries)) {
              response.debug = parsed as DebugData;
            } else if (response.data === null) {
              // First non-debug content item is the main data
              response.data = parsed;
            }
        } catch (e) {
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
  async call(method: string, params: any = {}, debugOptions?: any): Promise<RPCCallResult> {
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
    const payload: RPCRequest = {
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
        
        // Also check for debug data in error.data.content
        let debugData: DebugData | undefined;
        if (data.error.data?.content && Array.isArray(data.error.data.content)) {
          for (const contentItem of data.error.data.content) {
            if (contentItem.type === 'text' && typeof contentItem.text === 'string') {
              try {
                const parsed = JSON.parse(contentItem.text);
                if (parsed && Array.isArray(parsed.entries)) {
                  debugData = parsed as DebugData;
                  break;
                }
              } catch (e) {
                // Skip if not valid JSON
              }
            }
          }
        }
        
        // If we have multiple errors, use RPCError to format them nicely
        if (allErrors.length > 1) {
          const error = new RPCError(`RPC error: ${data.error.message}`, data.error.code, allErrors);
          (error as any).debug = debugData;
          (error as any).requestInfo = { method, params: originalParams };
          throw error;
        } else if (allErrors.length === 1) {
          // Single error - use the detailed error content if available
          const error = new RPCError(`RPC error: ${allErrors[0].type}: ${allErrors[0].content}`, data.error.code, allErrors);
          (error as any).debug = debugData;
          (error as any).requestInfo = { method, params: originalParams };
          throw error;
        } else {
          // Fallback to message only
          const error = new RPCError(`RPC error: ${data.error.message}`, data.error.code);
          (error as any).debug = debugData;
          (error as any).requestInfo = { method, params: originalParams };
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
    } catch (error) {
      console.error(`RPC call failed for ${method}:`, error);
      throw error;
    }
  }

  /**
   * Get page data and return as PageData instance.
   * This is the recommended way to fetch page data.
   */
  async getPage(pageId: number | string, debugOptions?: any): Promise<PageData> {
    // Convert to number for schema validation (schema expects integer)
    const id = typeof pageId === 'string' ? parseInt(pageId, 10) : pageId;
    const params: any = { id };
    if (debugOptions) {
      Object.assign(params, debugOptions);
    }
    const result = await this.call('get_page', params);
    
    if (!result.data || !result.data.page) {
      throw new Error('Invalid page data response: missing page object');
    }
    
    // Use factory to create appropriate derived class
    return PageDataFactory.create(result.data as GetPageResponse);
  }

  /**
   * Display an error message to the user.
   */
  showError(label: string, error: any): void {
    const errorBox = document.createElement('div');
    errorBox.className = 'hh-error';
    // Styles are in CSS
    
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


/**
 * RPC Client - custom MCP wrapper for JSON-RPC calls to the backend.
 */

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
    data?: any;
  };
}

export class RPCClient {
  /**
   * Make an MCP JSON-RPC call to the backend.
   */
  async call(method: string, params: any = {}): Promise<any> {
    const payload: RPCRequest = {
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

      const data: RPCResponse = await response.json();

      if (data.error) {
        throw new Error(`RPC error: ${data.error.message}`);
      }

      return data.result;
    } catch (error) {
      console.error(`RPC call failed for ${method}:`, error);
      throw error;
    }
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


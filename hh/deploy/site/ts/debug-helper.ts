/**
 * Helper function to handle RPC responses with debug data.
 * Creates a debug overlay window if debug data is present in the response.
 */

import { OverlayManager } from './overlay-manager.js';
import { OverlayDebugTable, DebugData } from './overlay-debug-table.js';

export interface RPCResponseWithDebug {
  data?: any;
  debug?: DebugData;
  requestInfo?: {
    method: string;
    params: any;
  };
}

/**
 * Check an RPC response for debug data and create a debug overlay if present.
 * @param rpcResult - The result from an RPC call (RPCCallResult or error with debug)
 * @param method - The RPC method name (optional, will use requestInfo if available)
 * @param params - The RPC params (optional, will use requestInfo if available)
 */
export function handleRPCResponseWithDebug(
  rpcResult: RPCResponseWithDebug | any,
  method?: string,
  params?: any
): void {
  // Extract debug data, request info, and response data
  let debugData: DebugData | undefined;
  let requestInfo: { method: string; params: any } | undefined;
  let responseData: any = undefined;

  // Check if it's an RPCCallResult with debug
  if (rpcResult && typeof rpcResult === 'object') {
    // Check for debug data first
    if (rpcResult.debug) {
      debugData = rpcResult.debug;
      responseData = rpcResult.data;
      
      // Extract requestInfo - try multiple sources
      if (rpcResult.requestInfo && rpcResult.requestInfo.method) {
        requestInfo = rpcResult.requestInfo;
      } else if (method) {
        // Always use provided method/params as fallback
        requestInfo = { method, params: params !== undefined ? params : {} };
      }
    }
    // Also check if it's an error with debug attached (RPCError)
    else if ('debug' in rpcResult && rpcResult.debug) {
      debugData = rpcResult.debug;
      responseData = rpcResult.data;
      
      // Extract requestInfo from error - try multiple sources
      if (rpcResult.requestInfo && rpcResult.requestInfo.method) {
        requestInfo = rpcResult.requestInfo;
      } else if (method) {
        // Always use provided method/params as fallback
        requestInfo = { method, params: params !== undefined ? params : {} };
      }
    }
  }

  // If we have debug data, create a debug overlay
  if (debugData) {
    const overlayManager = OverlayManager.getInstance();
    const debugTable = new OverlayDebugTable();
    const debugElement = debugTable.render(debugData);

    // Build arrays for headers and content sections
    const headerArray: string[] = [];
    const contentArray: Array<string | HTMLElement> = [];

    // Box 1: Request info
    if (requestInfo) {
      headerArray.push('Request');
      contentArray.push(`
        <div class="overlay-form-group">
          <label><strong>Tool:</strong></label>
          <div>${escapeHtml(requestInfo.method)}</div>
        </div>
        <div class="overlay-form-group">
          <label><strong>Arguments:</strong></label>
          <pre class="overlay-debug-request-params">${escapeHtml(JSON.stringify(requestInfo.params, null, 2))}</pre>
        </div>
      `);
    }

    // Box 2: Response data
    if (responseData !== undefined) {
      headerArray.push('Response');
      contentArray.push(`
        <div class="overlay-form-group">
          <pre class="overlay-debug-response-params">${escapeHtml(JSON.stringify(responseData, null, 2))}</pre>
        </div>
      `);
    }

    // Box 3: Debug table (no header - blank string means no header div)
    headerArray.push('');
    contentArray.push(debugElement);

    // Create new overlay window for debug info - pass arrays with headers
    overlayManager.show({
      header: 'Debug Information',
      content: contentArray,
      contentHeaders: headerArray,
      closable: true,
      cancelLabel: 'Close',
      showSubmit: false,
      className: 'overlay-debug-window'
    });
  }
}

/**
 * Escape HTML to prevent XSS.
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}


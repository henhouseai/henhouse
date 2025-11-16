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
    if (rpcResult.debug) {
      debugData = rpcResult.debug;
      responseData = rpcResult.data;
      // Prefer requestInfo from result, fall back to provided method/params
      // Always use provided method/params if requestInfo is missing or incomplete
      if (rpcResult.requestInfo && rpcResult.requestInfo.method && rpcResult.requestInfo.params) {
        requestInfo = rpcResult.requestInfo;
      } else if (method && params !== undefined) {
        requestInfo = { method, params };
      }
    }
    // Also check if it's an error with debug attached (RPCError)
    else if ('debug' in rpcResult && rpcResult.debug) {
      debugData = rpcResult.debug;
      responseData = rpcResult.data;
      // Prefer requestInfo from error, fall back to provided method/params
      if (rpcResult.requestInfo && rpcResult.requestInfo.method && rpcResult.requestInfo.params) {
        requestInfo = rpcResult.requestInfo;
      } else if (method && params !== undefined) {
        requestInfo = { method, params };
      }
    }
  }

  // If we have debug data, create a debug overlay
  if (debugData) {
    const overlayManager = OverlayManager.getInstance();
    const debugTable = new OverlayDebugTable();
    const debugElement = debugTable.render(debugData);

    // Build request info display (Box 1)
    let requestInfoHtml = '';
    if (requestInfo) {
      requestInfoHtml = `
        <div class="overlayContent">
          <div class="overlay-form-section">
            <h3 class="overlay-section-title">Request:</h3>
            <div class="overlay-form-group">
              <label><strong>Tool:</strong></label>
              <div>${escapeHtml(requestInfo.method)}</div>
            </div>
            <div class="overlay-form-group">
              <label><strong>Arguments:</strong></label>
              <pre class="overlay-debug-request-params">${escapeHtml(JSON.stringify(requestInfo.params, null, 2))}</pre>
            </div>
          </div>
        </div>
      `;
    }

    // Build response data display (Box 2)
    let responseInfoHtml = '';
    if (responseData !== undefined) {
      responseInfoHtml = `
        <div class="overlayContent">
          <div class="overlay-form-section">
            <h3 class="overlay-section-title">Response:</h3>
            <div class="overlay-form-group">
              <pre class="overlay-debug-response-params">${escapeHtml(JSON.stringify(responseData, null, 2))}</pre>
            </div>
          </div>
        </div>
      `;
    }

    // Debug table (Box 3) - already wrapped in overlayContent by OverlayDebugTable
    // Combine all three sections
    const contentHtml = requestInfoHtml + responseInfoHtml + debugElement.outerHTML;

    // Create new overlay window for debug info
    overlayManager.show({
      header: 'Debug Information',
      content: contentHtml,
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


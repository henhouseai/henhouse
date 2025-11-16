/**
 * Helper function to handle RPC responses with debug data.
 * Creates a debug overlay window if debug data is present in the response.
 */
import { OverlayManager } from './overlay-manager.js';
import { OverlayDebugTable } from './overlay-debug-table.js';
/**
 * Check an RPC response for debug data and create a debug overlay if present.
 * @param rpcResult - The result from an RPC call (RPCCallResult or error with debug)
 * @param method - The RPC method name (optional, will use requestInfo if available)
 * @param params - The RPC params (optional, will use requestInfo if available)
 */
export function handleRPCResponseWithDebug(rpcResult, method, params) {
    // Extract debug data and request info
    let debugData;
    let requestInfo;
    // Check if it's an RPCCallResult with debug
    if (rpcResult && typeof rpcResult === 'object') {
        if (rpcResult.debug) {
            debugData = rpcResult.debug;
            // Prefer requestInfo from result, fall back to provided method/params
            requestInfo = rpcResult.requestInfo || (method && params ? { method, params } : undefined);
        }
        // Also check if it's an error with debug attached (RPCError)
        else if ('debug' in rpcResult && rpcResult.debug) {
            debugData = rpcResult.debug;
            requestInfo = rpcResult.requestInfo || (method && params ? { method, params } : undefined);
        }
    }
    // If we have debug data, create a debug overlay
    if (debugData) {
        const overlayManager = OverlayManager.getInstance();
        const debugTable = new OverlayDebugTable();
        const debugElement = debugTable.render(debugData);
        // Build request info display
        let requestInfoHtml = '';
        if (requestInfo) {
            requestInfoHtml = `
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
      `;
        }
        // Combine request info and debug table
        const contentHtml = requestInfoHtml + debugElement.outerHTML;
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
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

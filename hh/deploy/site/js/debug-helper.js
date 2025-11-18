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
    // Extract debug data, request info, and response data
    let debugData;
    let requestInfo;
    let responseData = undefined;
    // Check if it's an RPCCallResult with debug
    if (rpcResult && typeof rpcResult === 'object') {
        // Check for debug data first
        if (rpcResult.debug) {
            debugData = rpcResult.debug;
            responseData = rpcResult.data;
            // Extract requestInfo - try multiple sources
            if (rpcResult.requestInfo && rpcResult.requestInfo.method) {
                requestInfo = rpcResult.requestInfo;
            }
            else if (method) {
                // Always use provided method/params as fallback
                requestInfo = { method, params: params !== undefined ? params : {} };
            }
            // Debug logging
            console.log('handleRPCResponseWithDebug:', {
                hasDebug: !!debugData,
                hasResponseData: responseData !== undefined,
                responseDataType: typeof responseData,
                hasRequestInfo: !!requestInfo,
                requestInfoSource: rpcResult.requestInfo ? 'rpcResult' : 'fallback',
                rpcResultKeys: Object.keys(rpcResult)
            });
        }
        // Also check if it's an error with debug attached (RPCError)
        else if ('debug' in rpcResult && rpcResult.debug) {
            debugData = rpcResult.debug;
            responseData = rpcResult.data;
            // Extract requestInfo from error - try multiple sources
            if (rpcResult.requestInfo && rpcResult.requestInfo.method) {
                requestInfo = rpcResult.requestInfo;
            }
            else if (method) {
                // Always use provided method/params as fallback
                requestInfo = { method, params: params !== undefined ? params : {} };
            }
        }
    }
    // If we have debug data, create a debug overlay
    // Only create overlay if debug data has entries (prevents empty debug overlays)
    if (debugData && Array.isArray(debugData.entries) && debugData.entries.length > 0) {
        const overlayManager = OverlayManager.getInstance();
        const debugTable = new OverlayDebugTable();
        const debugElement = debugTable.render(debugData);
        // Build arrays for headers and content sections
        const headerArray = [];
        const contentArray = [];
        // Box 1: Request info - always show if we have method/params (even if requestInfo wasn't on rpcResult)
        const shouldShowRequest = requestInfo || (method && params !== undefined);
        console.log('Request section check:', { requestInfo: !!requestInfo, method, hasParams: params !== undefined, shouldShowRequest });
        if (shouldShowRequest) {
            const finalRequestInfo = requestInfo || { method: method, params: params || {} };
            headerArray.push('Request');
            contentArray.push(`
        <div class="overlay-form-group">
          <label><strong>Tool:</strong></label>
          <div>${escapeHtml(finalRequestInfo.method)}</div>
        </div>
        <div class="overlay-form-group">
          <label><strong>Arguments:</strong></label>
          <pre class="overlay-debug-request-params">${escapeHtml(JSON.stringify(finalRequestInfo.params, null, 2))}</pre>
        </div>
      `);
            console.log('Request section added');
        }
        // Box 2: Response data
        // Always show response data if we have debug data (even if null/undefined, show it)
        const shouldShowResponse = responseData !== undefined || debugData;
        console.log('Response section check:', { responseData: responseData !== undefined, hasDebugData: !!debugData, shouldShowResponse });
        if (shouldShowResponse) {
            headerArray.push('Response');
            const responseContent = responseData !== undefined
                ? JSON.stringify(responseData, null, 2)
                : '(no response data)';
            contentArray.push(`
        <div class="overlay-form-group">
          <pre class="overlay-debug-response-params">${escapeHtml(responseContent)}</pre>
        </div>
      `);
            console.log('Response section added');
        }
        // Box 3: Debug table (no header - blank string means no header div)
        headerArray.push('');
        contentArray.push(debugElement);
        console.log('Final arrays:', { headerCount: headerArray.length, contentCount: contentArray.length, headers: headerArray });
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
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

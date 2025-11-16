"""
Response class for MCP (Model Context Protocol) backend output.
Outputs JSON-RPC 2.0 formatted responses.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
import json
import copy
from hh.gateway.response.response import Response
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

class ResponseMCP(Response):
    """
    MCP backend response handler.
    Outputs JSON-RPC 2.0 formatted responses.
    """
    
    def __init__(self):
        super().__init__()
        self.request_id: Optional[Any] = None  # Store request ID for JSON-RPC response
    
    def set_request_id(self, request_id: Any) -> None:
        """Store the JSON-RPC request ID for response formatting."""
        trace_in()
        self.request_id = request_id
        log(f"Set request ID: {request_id}")
        trace_out()
    
    def get_output(self) -> str:
        """Return MCP output - JSON-RPC 2.0 formatted response."""
        trace_in()
        
        # Check if error_output is set (indicates error mode)
        if self.error_output and "errors" in self.error_output:
            # Format error response using pre-set error data
            errors_data = self.error_output["errors"]
            error_count = len(errors_data)
            
            # Build generic error message
            error_message = f"{error_count} error{'s' if error_count != 1 else ''} detected"
            
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,  # Internal error
                    "message": error_message,
                    "data": {
                        "errors": errors_data
                    }
                }
            }
            
            # Include debug output if available - add as content item with type "text"
            if self.debug_output:
                # Add debug as a text content item in error data
                if "content" not in error_response["error"]["data"]:
                    error_response["error"]["data"]["content"] = []
                debug_text = json.dumps(self.debug_output, default=str)
                error_response["error"]["data"]["content"].append({
                    "type": "text",
                    "text": debug_text
                })
            
            if self.request_id is not None:
                error_response["id"] = self.request_id
            else:
                error_response["id"] = None
            
            result = json.dumps(error_response, indent=2, default=str)
            log("MCP error response generated")
            trace_out()
            return result
        
        # Build success response from action response
        # action_response always has content structure from success_payload()
        # Make a deep copy to avoid modifying the original
        response_data = copy.deepcopy(self.action_response)
        
        # Format as JSON-RPC 2.0 response
        jsonrpc_response = {
            "jsonrpc": "2.0",
            "result": response_data
        }
        
        # Include debug output if available - add as content item with type "text"
        if self.debug_output is not None:
            # Ensure content array exists
            if "content" not in response_data:
                response_data["content"] = []
            # Add debug as a text content item with JSON-serialized value
            debug_text = json.dumps(self.debug_output, default=str)
            response_data["content"].append({
                "type": "text",
                "text": debug_text
            })
        
        if self.request_id is not None:
            jsonrpc_response["id"] = self.request_id
        else:
            jsonrpc_response["id"] = None
        
        # Serialize everything as objects first
        result = json.dumps(jsonrpc_response, indent=2, default=str)
        
        # Post-process: if we have MCP content structure, stringify the text field
        if (self.action_response and 
            "content" in response_data and 
            isinstance(response_data["content"], list) and 
            len(response_data["content"]) > 0 and
            response_data["content"][0].get("type") == "text" and
            "text" in response_data["content"][0] and
            isinstance(response_data["content"][0]["text"], dict)):
            # Parse the serialized response
            parsed = json.loads(result)
            # Stringify the text field
            parsed["result"]["content"][0]["text"] = json.dumps(response_data["content"][0]["text"], default=str)
            # Re-serialize
            result = json.dumps(parsed, indent=2, default=str)
        log(f"MCP success response generated: {len(result)} characters")
        trace_out()
        return result


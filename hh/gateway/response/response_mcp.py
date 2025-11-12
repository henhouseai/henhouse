"""
Response class for MCP (Model Context Protocol) backend output.
Outputs JSON-RPC 2.0 formatted responses.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
import json
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
        
        # Check for errors first
        from hh.gateway.error.error_store import is_error, get_errors
        has_errors = is_error()
        
        if has_errors:
            # Format error response
            all_errors = get_errors()
            # Convert ErrorEntry objects to dicts for JSON serialization
            errors_data = [
                {
                    "type": error.error_type.value,
                    "content": error.content,
                    "timestamp": error.timestamp
                }
                for error in all_errors
            ]
            
            # Build a more descriptive error message from the first error
            error_message = "Internal error"
            if errors_data:
                first_error = errors_data[0]
                error_content = first_error.get("content", "")
                error_type = first_error.get("type", "")
                
                # Format error message with actual content
                if isinstance(error_content, str):
                    error_message = f"{error_type}: {error_content}" if error_content else f"{error_type} error"
                elif isinstance(error_content, dict):
                    # Extract useful info from dict
                    error_str = str(error_content).replace("{", "").replace("}", "")[:200]
                    error_message = f"{error_type}: {error_str}"
                else:
                    error_message = f"{error_type}: {str(error_content)[:200]}"
            
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
            if self.request_id is not None:
                error_response["id"] = self.request_id
            else:
                error_response["id"] = None
            
            result = json.dumps(error_response, indent=2, default=str)
            log("MCP error response generated")
            trace_out()
            return result
        
        # Build success response from action response and/or output buffer
        response_data: Dict[str, Any] = {}
        
        # If we have action response, use that as the main result
        if self.action_response:
            # action_response always has content structure from success_payload()
            # Serialize content[0].text (dict) to JSON string for MCP
            response_data = dict(self.action_response)
            response_data["content"][0]["text"] = json.dumps(response_data["content"][0]["text"], default=str)
        # Otherwise, if we have output buffer, use that
        elif self.output_buffer:
            # Join output buffer - might be JSON strings or text
            output_text = "\n".join(self.output_buffer)
            # Try to parse as JSON if it looks like JSON
            try:
                response_data = json.loads(output_text)
            except (json.JSONDecodeError, ValueError):
                # If not JSON, wrap in result object
                response_data = {
                    "output": output_text
                }
        else:
            # Empty response
            response_data = {
                "success": True
            }
        
        # Format as JSON-RPC 2.0 response
        jsonrpc_response = {
            "jsonrpc": "2.0",
            "result": response_data
        }
        
        if self.request_id is not None:
            jsonrpc_response["id"] = self.request_id
        else:
            jsonrpc_response["id"] = None
        
        result = json.dumps(jsonrpc_response, indent=2, default=str)
        log(f"MCP success response generated: {len(result)} characters")
        trace_out()
        return result


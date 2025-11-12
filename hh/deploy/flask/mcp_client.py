#!/usr/bin/env python3
"""
MCP Client Entry Point
Handles MCP (Model Context Protocol) JSON-RPC requests.
Implements core MCP protocol methods and routes tool execution to Gateway.
"""
from __future__ import annotations
import sys
import json

# MCP Protocol Version
MCP_PROTOCOL_VERSION = "2024-11-05"

# Import MCP Tools Whitelist from centralized location
from hh.deploy.conf.mcp_whitelist import MCP_TOOLS_WHITELIST

def get_server_info():
    """Get server information for MCP responses."""
    return {
        "name": "Henhouse MCP Server",
        "version": "1.0.0"
    }

def validate_arguments(arguments: dict, schema: dict) -> tuple[bool, str]:
    """Validate arguments against JSON Schema.
    Returns (is_valid, error_message).
    """
    if not isinstance(arguments, dict):
        return False, "Arguments must be an object"
    
    # Check required fields
    required = schema.get("required", [])
    for field in required:
        if field not in arguments:
            return False, f"Missing required field: {field}"
    
    # Check types for provided fields
    properties = schema.get("properties", {})
    for key, value in arguments.items():
        if key not in properties:
            # Allow extra fields for now (Gateway will handle validation)
            continue
        
        prop_schema = properties[key]
        expected_type = prop_schema.get("type")
        
        if expected_type == "string" and not isinstance(value, str):
            return False, f"Field '{key}' must be a string"
        elif expected_type == "integer" and not isinstance(value, int):
            return False, f"Field '{key}' must be an integer"
        elif expected_type == "number" and not isinstance(value, (int, float)):
            return False, f"Field '{key}' must be a number"
        elif expected_type == "boolean" and not isinstance(value, bool):
            return False, f"Field '{key}' must be a boolean"
        elif expected_type == "array" and not isinstance(value, list):
            return False, f"Field '{key}' must be an array"
        elif expected_type == "object" and not isinstance(value, dict):
            return False, f"Field '{key}' must be an object"
    
    return True, ""

def handle_initialize(params: dict, request_id) -> dict:
    """Handle MCP initialize request."""
    server_capabilities = {
        "tools": {
            "listChanged": True
        },
        "prompts": {
            "listChanged": True
        },
        "resources": {
            "subscribe": True,
            "listChanged": True
        },
        "logging": {}
    }
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": server_capabilities,
            "serverInfo": get_server_info()
        }
    }

def handle_tools_list(request_id) -> dict:
    """Handle MCP tools/list request."""
    tools = []
    
    for tool_name, tool_config in MCP_TOOLS_WHITELIST.items():
        tool = {
            "name": tool_name,
            "description": tool_config["description"],
            "inputSchema": tool_config["inputSchema"]
        }
        tools.append(tool)
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": tools
        }
    }

def handle_prompts_list(request_id) -> dict:
    """Handle MCP prompts/list request."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "prompts": []
        }
    }

def handle_resources_list(request_id) -> dict:
    """Handle MCP resources/list request."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "resources": []
        }
    }

def handle_tools_call(params: dict, request_id) -> dict:
    """Handle MCP tools/call request - validate and route to Gateway."""
    tool_name = params.get("name")
    tool_arguments = params.get("arguments", {})
    
    if not tool_name:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing 'name' parameter"
            }
        }
    
    # Check if tool is in whitelist
    if tool_name not in MCP_TOOLS_WHITELIST:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": "Method not found",
                "data": f"Tool '{tool_name}' is not available"
            }
        }
    
    # Validate arguments against schema
    tool_config = MCP_TOOLS_WHITELIST[tool_name]
    schema = tool_config["inputSchema"]
    is_valid, error_msg = validate_arguments(tool_arguments, schema)
    
    if not is_valid:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": error_msg
            }
        }
    
    # Route to Gateway
    from hh.gateway.gateway import get_gateway
    from hh.gateway.error.error_store import is_error
    
    try:
        # Build argv: command name first, then arguments
        argv = [tool_name]
        
        # Add arguments as-is (Gateway grammar system will parse them)
        if isinstance(tool_arguments, dict):
            for key, value in tool_arguments.items():
                argv.append(f"--{key}")
                if value is not None:
                    argv.append(str(value))
        
        # Also accept query string params from sys.argv[1:] (added by Flask)
        query_params = sys.argv[1:] if len(sys.argv) > 1 else []
        if query_params:
            argv.extend(query_params)
        
        # Initialize gateway and dispatch
        gateway = get_gateway()
        
        # Store request ID for response formatting
        if hasattr(gateway.response, 'set_request_id'):
            gateway.response.set_request_id(request_id)
        
        # Dispatch with mcp backend
        result = gateway.dispatch(argv, "mcp")
        
        # Get output from gateway response
        if gateway and gateway.response:
            output = gateway.response.get_output()
            
            # Try to parse as JSON-RPC response
            try:
                output_data = json.loads(output)
                if isinstance(output_data, dict) and "jsonrpc" in output_data:
                    # Ensure request ID is set correctly
                    output_data["id"] = request_id
                    return output_data
                else:
                    # Wrap in MCP tools/call result format
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": output
                                }
                            ]
                        }
                    }
            except json.JSONDecodeError:
                # Plain text output
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": output
                            }
                        ]
                    }
                }
        
        # Fallback error
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": "No output from gateway"
            }
        }
        
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        }

def main() -> int:
    """Main entry point for MCP client."""
    # Read JSON-RPC request from stdin (POST body from Flask)
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": "Empty request body"
                },
                "id": None
            }), file=sys.stderr)
            return 1
        
        # Parse JSON-RPC request
        mcp_request = json.loads(input_data)
        
        # Validate JSON-RPC structure
        if not isinstance(mcp_request, dict):
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "Request must be a JSON object"
                },
                "id": None
            }), file=sys.stderr)
            return 1
        
        # Extract JSON-RPC fields
        request_id = mcp_request.get("id")
        method = mcp_request.get("method")
        params = mcp_request.get("params", {})
        
        if not method:
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "Missing 'method' field"
                },
                "id": request_id
            }), file=sys.stderr)
            return 1
        
        # Handle MCP protocol methods directly
        response = None
        
        if method == "initialize":
            response = handle_initialize(params, request_id)
        elif method == "tools/list":
            response = handle_tools_list(request_id)
        elif method == "prompts/list":
            response = handle_prompts_list(request_id)
        elif method == "resources/list":
            response = handle_resources_list(request_id)
        elif method == "tools/call":
            response = handle_tools_call(params, request_id)
        elif method == "notifications/initialized":
            # Client notification - no response needed
            return 0
        else:
            # Unknown method - try routing to Gateway as fallback
            from hh.gateway.gateway import get_gateway
            from hh.gateway.error.error_store import is_error
            
            # Build argv from method (command) and params
            argv = [method]
            
            # Convert params dict to command-line arguments
            if isinstance(params, dict):
                for key, value in params.items():
                    argv.append(f"--{key}")
                    if value is not None:
                        argv.append(str(value))
            
            # Also accept query string params from sys.argv[1:] (added by Flask)
            query_params = sys.argv[1:] if len(sys.argv) > 1 else []
            if query_params:
                argv.extend(query_params)
            
            # Initialize gateway and dispatch
            gateway = get_gateway()
            
            # Store request ID for response formatting
            if hasattr(gateway.response, 'set_request_id'):
                gateway.response.set_request_id(request_id)
            
            # Dispatch with mcp backend
            result = gateway.dispatch(argv, "mcp")
            
            # Get output from gateway response
            if gateway and gateway.response:
                output = gateway.response.get_output()
                
                # Try to parse as JSON-RPC response
                try:
                    output_data = json.loads(output)
                    if isinstance(output_data, dict) and "jsonrpc" in output_data:
                        # Ensure request ID is set correctly
                        output_data["id"] = request_id
                        response = output_data
                    else:
                        # Wrap in JSON-RPC response
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": output_data
                        }
                except json.JSONDecodeError:
                    # Plain text - wrap in error
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": "Method not found",
                            "data": f"Unknown method: {method}"
                        }
                    }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found",
                        "data": f"Unknown method: {method}"
                    }
                }
        
        # Output response
        if response:
            print(json.dumps(response))
            return 0
        else:
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": "No response generated"
                }
            }), file=sys.stderr)
            return 1
        
    except json.JSONDecodeError as e:
        print(json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32700,
                "message": "Parse error",
                "data": str(e)
            },
            "id": None
        }), file=sys.stderr)
        return 1
    except Exception as e:
        print(json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            "id": None
        }), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())

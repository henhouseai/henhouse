#!/usr/bin/env python3
"""
API Client Entry Point
Handles API (TypeScript Fetch API) JSON-RPC requests.
Simple tool execution router: validates tool against APIWhitelist, then routes to Gateway.
Only supports tools/call method - no MCP protocol discovery/negotiation.
"""
from __future__ import annotations
import sys
import os
import json

# Import API Whitelist class
from hh.gateway.registry.tool_whitelist import APIWhitelist
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

def get_tier() -> str:
    """Get current tier from environment or Flask app context."""
    # Try to get from environment (set by Flask app)
    tier = os.getenv('USER_TIER', 'guest')
    # Validate tier
    if tier not in HENHOUSE_TIERS:
        tier = 'guest'
    return tier

def handle_tools_call(params: dict, request_id) -> dict:
    """Handle API tools/call request - check if tool allowed, then route to Gateway."""
    tool_name = params.get("name")
    tool_arguments = params.get("arguments", {})
    tier = get_tier()

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

    # Simple membership check - is this tool allowed for this tier?
    if not APIWhitelist.tool_exists(tier, tool_name):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": f"Tool '{tool_name}' not available for tier '{tier}'"
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
        from hh.gateway.gateway import init_gateway
        gateway = init_gateway(argv, "api")

        # Store request ID for response formatting
        if hasattr(gateway.response, 'set_request_id'):
            gateway.response.set_request_id(request_id)

        # Dispatch with api backend
        result = gateway.dispatch()
        
        # Get output from gateway response
        output = gateway.response.get_output()
        
        # Try to parse as JSON-RPC response
        try:
            output_data = json.loads(output)
            if isinstance(output_data, dict) and "jsonrpc" in output_data:
                # Ensure request ID is set correctly
                output_data["id"] = request_id
                return output_data
            else:
                # Wrap in API tools/call result format
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
    """Main entry point for API client."""
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
        api_request = json.loads(input_data)

        # Validate JSON-RPC structure
        if not isinstance(api_request, dict):
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
        request_id = api_request.get("id")
        method = api_request.get("method")
        params = api_request.get("params", {})
        
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
        
        # Handle API protocol methods directly
        response = None

        if method == "tools/call":
            response = handle_tools_call(params, request_id)
        else:
            # Unknown method - return standard JSON-RPC 2.0 error
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": f"Unknown method: {method}. API client only supports tools/call."
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

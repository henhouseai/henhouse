#!/usr/bin/env python3
"""
MCP HTTP Wrapper Script
Reads JSON-RPC from stdin and forwards to HTTP MCP server with Basic Auth.
Reads credentials from ~/.{project_name}.cnf (same format as MySQL config).
"""
from __future__ import annotations
import sys
import json
import os
import base64
import configparser
import requests
from pathlib import Path

def debug_print(message: str) -> None:
    """Debug print function - no-op by default. Uncomment the print line to enable debug output."""
    # Uncomment the line below to enable debug output:
    # print(f"[DEBUG] {message}", file=sys.stderr)
    pass

def detect_project_name() -> str:
    """Detect project name by looking for 'hh' directory starting from script location."""
    # Start from the script's directory (more reliable than cwd)
    script_path = Path(__file__).resolve()
    current_path = script_path.parent
    
    # Walk up from script location looking for 'hh' directory
    while current_path != current_path.parent:
        hh_dir = current_path / 'hh'
        if hh_dir.exists() and hh_dir.is_dir():
            return current_path.name
        current_path = current_path.parent
    
    # Fallback: use script's parent directory name
    return script_path.parent.name

def load_config() -> dict:
    """Load user, password, and host from ~/.{project_name}.cnf"""
    project_name = detect_project_name()
    config = configparser.ConfigParser()
    config_path = Path.home() / f'.{project_name}.cnf'
    
    debug_print(f"Project name: {project_name}")
    debug_print(f"Config file path: {config_path}")
    debug_print(f"Config file exists: {config_path.exists()}")
    
    if not config_path.exists():
        print(json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Configuration file not found",
                "data": f"~/.{project_name}.cnf not found at {config_path}"
            },
            "id": None
        }), file=sys.stderr)
        sys.exit(1)
    
    config.read(config_path)
    
    try:
        user = config.get('client', 'user', fallback=None)
        password = config.get('client', 'password', fallback=None)
        host = config.get('client', 'host', fallback=None)
        
        debug_print(f"Found user: {user}")
        debug_print(f"Found password: {'*' * len(password) if password else 'None'}")
        debug_print(f"Found host: {host}")
        
        if not user or not password or not host:
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Configuration incomplete",
                    "data": f"Missing user, password, or host in ~/.{project_name}.cnf"
                },
                "id": None
            }), file=sys.stderr)
            sys.exit(1)
        
        return {
            'user': user,
            'password': password,
            'host': host
        }
    except Exception as e:
        print(json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Configuration error",
                "data": f"Failed to read ~/.{project_name}.cnf: {str(e)}"
            },
            "id": None
        }), file=sys.stderr)
        sys.exit(1)

def get_auth_header(username: str, password: str) -> str:
    """Generate Basic Auth header."""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

def handle_request(mcp_url: str, config: dict, project_name: str) -> bool:
    """Handle a single JSON-RPC request. Returns True to continue, False to exit."""
    try:
        debug_print("Waiting for JSON-RPC input from stdin...")
        sys.stderr.flush()  # Flush before blocking read
        # Read first line (MCP uses newline-delimited JSON-RPC)
        # Note: readline() will block until a line is received or EOF
        input_data = sys.stdin.readline()
        debug_print(f"Received {len(input_data)} characters from stdin (first line)")
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
            return False  # Exit on EOF
        
        # Parse JSON-RPC request
        debug_print("Parsing JSON-RPC request...")
        debug_print(f"Raw input: {input_data[:200]}")  # First 200 chars for debugging
        input_data = input_data.strip()  # Remove newline
        mcp_request = json.loads(input_data)
        method = mcp_request.get('method', 'N/A')
        params = mcp_request.get('params', {})
        
        # Log the call via debug_print (can be enabled by uncommenting in debug_print function)
        method_str = f"MCP call: {method}"
        if params:
            # Truncate params for readability (avoid huge dumps)
            params_str = json.dumps(params, indent=None)[:200]
            if len(json.dumps(params, indent=None)) > 200:
                params_str += "..."
            debug_print(f"{method_str} | params: {params_str}")
        else:
            debug_print(f"{method_str}")
        
        debug_print(f"JSON-RPC method: {method}")
        
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
        
        # Prepare HTTP request with Basic Auth
        headers = {
            "Content-Type": "application/json",
            "Authorization": get_auth_header(config['user'], config['password'])
        }
        
        # Make HTTP request to MCP server
        try:
            debug_print(f"Making HTTP POST request to {mcp_url}")
            response = requests.post(
                mcp_url,
                json=mcp_request,
                headers=headers,
                timeout=30
            )
            
            debug_print(f"HTTP response status: {response.status_code}")
            
            # Check HTTP status
            if response.status_code == 401:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": "Unauthorized",
                        "data": f"Authentication failed - check credentials in ~/.{project_name}.cnf"
                    },
                    "id": mcp_request.get("id")
                }), file=sys.stderr)
                return True  # Continue even on auth error (let client decide)
            
            response.raise_for_status()
            
            # Handle 204 No Content (used for notifications that don't need a response)
            if response.status_code == 204:
                # 204 responses have no body - this is valid for notifications
                # For stdio-based MCP, we need to handle this carefully
                # Check if the request has a non-null id
                request_id = mcp_request.get("id")
                if request_id is not None:
                    # Request has an id - respond with it (per JSON-RPC 2.0 spec)
                    print(json.dumps({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {}
                    }))
                    sys.stdout.flush()
                # If id is None/null or missing, it's a pure notification - don't output anything
                # This follows JSON-RPC 2.0: notifications don't require responses
                return True
            
            # Parse and output JSON-RPC response
            try:
                response_json = response.json()
                print(json.dumps(response_json))
                sys.stdout.flush()  # Ensure response is sent immediately
                return True  # Continue to handle more requests
            except json.JSONDecodeError as e:
                # Log detailed error info to stderr for debugging
                error_details = {
                    "status_code": response.status_code,
                    "content_type": response.headers.get('Content-Type', 'unknown'),
                    "response_length": len(response.text),
                    "response_preview": response.text[:500],
                    "json_error": str(e)
                }
                print(f"[ERROR] Failed to parse JSON response: {json.dumps(error_details, indent=2)}", file=sys.stderr)
                sys.stderr.flush()
                
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": f"Invalid JSON response from server (status {response.status_code}): {response.text[:200]}"
                    },
                    "id": mcp_request.get("id")
                }), file=sys.stderr)
                return True  # Continue even on error
                
        except requests.exceptions.RequestException as e:
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": f"HTTP request failed: {str(e)}"
                },
                "id": mcp_request.get("id")
            }), file=sys.stderr)
            return True  # Continue even on error
        
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
        return True  # Continue even on error
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
        return True  # Continue even on error

def main() -> int:
    """Main entry point - runs in a loop to handle multiple requests."""
    # Detect project name for error messages
    project_name = detect_project_name()
    
    # Load configuration
    try:
        config = load_config()
    except SystemExit:
        return 1
    
    mcp_url = f"https://{config['host']}/mcp"
    
    debug_print(f"MCP URL: {mcp_url}")
    sys.stderr.flush()  # Ensure debug output is sent immediately
    
    # Run in a loop to handle multiple requests
    while True:
        should_continue = handle_request(mcp_url, config, project_name)
        if not should_continue:
            debug_print("Exiting (EOF or error)")
            break
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


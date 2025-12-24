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
from typing import List, Tuple, Optional

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
            return True
        
        # Check for file attachments in params (can be nested in 'arguments' for tools/call)
        # Look for _files array or file_paths array in params or nested structures
        file_paths = []
        
        def extract_files_from_dict(d: dict, remove: bool = False) -> list:
            """Recursively search for _files or file_paths in dict, return list of file paths."""
            found_files = []
            if not isinstance(d, dict):
                return found_files
            
            # Check current level
            for key in ['_files', 'file_paths']:
                if key in d:
                    files_value = d[key]
                    # Handle both list and string representation of list
                    if isinstance(files_value, list):
                        found_files.extend(files_value)
                    elif isinstance(files_value, str):
                        # Try to parse string representation of list (e.g., "['file1', 'file2']")
                        try:
                            import ast
                            parsed = ast.literal_eval(files_value)
                            if isinstance(parsed, list):
                                found_files.extend(parsed)
                            else:
                                found_files.append(files_value)
                        except:
                            # If parsing fails, treat as single file path
                            if files_value:
                                found_files.append(files_value)
                    
                    # Remove _files from dict if requested
                    if remove:
                        del d[key]
            
            # Recursively check nested dicts (like 'arguments' in tools/call)
            for value in d.values():
                if isinstance(value, dict):
                    found_files.extend(extract_files_from_dict(value, remove=remove))
            
            return found_files
        
        if isinstance(params, dict):
            # Extract files from params (recursively, including nested 'arguments')
            file_paths = extract_files_from_dict(params, remove=True)
            # Update params after removing _files
            mcp_request['params'] = params
        
        # Validate and convert file paths to absolute paths (relative to wrapper script)
        validated_file_paths = []
        if file_paths:
            script_path = Path(__file__).resolve()
            script_dir = script_path.parent
            debug_print(f"Wrapper script directory: {script_dir}")
            
            for file_path in file_paths:
                if not isinstance(file_path, str):
                    continue
                
                # Check for path traversal attempts (..)
                if '..' in file_path:
                    print(json.dumps({
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32602,
                            "message": "Invalid params",
                            "data": f"Path traversal not allowed: {file_path}"
                        },
                        "id": mcp_request.get("id")
                    }), file=sys.stderr)
                    return True  # Continue on error
                
                # Convert to absolute path relative to script directory
                if os.path.isabs(file_path):
                    # If absolute, check if it's within project directory
                    abs_path = Path(file_path)
                    try:
                        abs_path.relative_to(script_dir)
                    except ValueError:
                        # Path is outside project directory
                        print(json.dumps({
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32602,
                                "message": "Invalid params",
                                "data": f"Path outside project directory not allowed: {file_path}"
                            },
                            "id": mcp_request.get("id")
                        }), file=sys.stderr)
                        return True
                    validated_file_paths.append(str(abs_path))
                else:
                    # Relative path - resolve relative to script directory
                    abs_path = (script_dir / file_path).resolve()
                    # Verify it's still within project directory (prevent symlink attacks)
                    try:
                        abs_path.relative_to(script_dir)
                    except ValueError:
                        print(json.dumps({
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32602,
                                "message": "Invalid params",
                                "data": f"Resolved path outside project directory: {file_path}"
                            },
                            "id": mcp_request.get("id")
                        }), file=sys.stderr)
                        return True
                    validated_file_paths.append(str(abs_path))
            
            file_paths = validated_file_paths
        
        # Prepare HTTP request with Basic Auth
        headers = {
            "Authorization": get_auth_header(config['user'], config['password'])
        }
        
        # Make HTTP request to MCP server
        try:
            if file_paths:
                # Use multipart/form-data for file uploads
                debug_print(f"Attaching {len(file_paths)} file(s) to request")
                files = []
                for idx, file_path in enumerate(file_paths):
                    file_path_obj = Path(file_path)
                    if not file_path_obj.exists():
                        print(json.dumps({
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32602,
                                "message": "Invalid params",
                                "data": f"File not found: {file_path}"
                            },
                            "id": mcp_request.get("id")
                        }), file=sys.stderr)
                        return True  # Continue on error
                    
                    # Open file and add to files list
                    # Flask expects files with keys like "file0", "file1", etc.
                    file_obj = open(file_path_obj, 'rb')
                    files.append((f'file{idx}', (file_path_obj.name, file_obj, 'application/octet-stream')))
                    debug_print(f"  - file{idx}: {file_path_obj.name} ({file_path_obj.stat().st_size} bytes)")
                
                # Add JSON-RPC as form data
                data = {
                    'jsonrpc': json.dumps(mcp_request)
                }
                
                debug_print(f"Making HTTP POST request to {mcp_url} with {len(files)} file(s)")
                response = requests.post(
                    mcp_url,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=60  # Longer timeout for file uploads
                )
                
                # Close file handles
                for _, (_, file_obj, _) in files:
                    file_obj.close()
            else:
                # Use JSON for regular requests
                headers["Content-Type"] = "application/json"
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
               
                # Enhance error messages with details from error.data.errors
                if "error" in response_json and isinstance(response_json["error"], dict):
                    error_obj = response_json["error"]
                    error_data = error_obj.get("data", {})
                    errors_list = error_data.get("errors", [])
                    
                    if errors_list:
                        # Extract error messages from errors array
                        error_messages = []
                        for err in errors_list:
                            error_type = err.get("type", "unknown")
                            content = err.get("content", "")
                            
                            # Extract message from content (can be string or dict)
                            if isinstance(content, str):
                                msg = content
                            elif isinstance(content, dict):
                                msg = str(content.get("message") or content.get("error") or content)
                            else:
                                msg = str(content)
                            
                            # Truncate long messages for readability
                            if len(msg) > 100:
                                msg = msg[:97] + "..."
                            
                            error_messages.append(f"{error_type}: {msg}")
                        
                        # Enhance error message with actual error details
                        error_count = len(errors_list)
                        if error_count == 1:
                            error_obj["message"] = error_messages[0]
                        elif error_count <= 3:
                            error_obj["message"] = f"{error_count} errors: {'; '.join(error_messages)}"
                        else:
                            error_obj["message"] = f"{error_count} errors: {'; '.join(error_messages[:3])} (and {error_count - 3} more)"
                
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


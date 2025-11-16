#!/usr/bin/env python3
"""
Universal Flask App for Henhouse
Gets installed with tier suffixes: app_guest.py, app_verified.py, app_admin.py, app_root.py
Each instance runs as its corresponding tier user and serves content with appropriate permissions.
"""

import sys
import os
import logging
import subprocess
import threading
from pathlib import Path
from flask import Flask, send_from_directory, request
import tempfile
import uuid

# Determine project name from /srv path or environment
if os.path.exists('/srv'):
    # Try to detect from cwd
    cwd = Path.cwd()
    if str(cwd).startswith('/srv/'):
        PROJECT_NAME = cwd.name
    else:
        PROJECT_NAME = os.getenv('PROJECT_NAME', 'henhouse')
else:
    PROJECT_NAME = os.getenv('PROJECT_NAME', 'henhouse')

# Determine tier from script name ({project}_root.py → "root", etc.)
SCRIPT_NAME = Path(sys.argv[0]).name
if SCRIPT_NAME.endswith('.py'):
    script_base = SCRIPT_NAME.replace('.py', '')
    # Extract tier from {project}_{tier} format
    if script_base.startswith(f'{PROJECT_NAME}_'):
        TIER_SUFFIX = script_base.replace(f'{PROJECT_NAME}_', '')
    else:
        TIER_SUFFIX = ''  # Default fallback (should always match pattern in practice)
else:
    TIER_SUFFIX = ''  # Default fallback (should always match pattern in practice)

# Setup paths
PROJECT_ROOT = Path(f'/srv/{PROJECT_NAME}')
SITE_DIR = PROJECT_ROOT / 'site'

# Get log file locally (set by deploy script)
LOG_FILE = os.getenv('LOG_FILE', f'/srv/{PROJECT_NAME}/logs/flask_{PROJECT_NAME}_{TIER_SUFFIX}.log')

# Create Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', f'{PROJECT_NAME}-{TIER_SUFFIX}-secret-key-change-in-production')

# Configure Flask's logger to write to our log file
if LOG_FILE:
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )

# Log initialization after logging is configured
logging.info(f"Flask app initialized: SCRIPT_NAME={SCRIPT_NAME}, TIER_SUFFIX={TIER_SUFFIX}")

GATEWAY_MAX_CONCURRENCY = int(os.getenv('GATEWAY_MAX_CONCURRENCY', '4'))
_gateway_semaphore = threading.Semaphore(GATEWAY_MAX_CONCURRENCY)

@app.route('/mcp', methods=['POST', 'GET'])
@app.route('/mcp/<path:path>', methods=['POST', 'GET'])
def mcp_handler(path: str = ""):
    """Handle MCP (Model Context Protocol) JSON-RPC requests."""
    try:
        import json
        
        # Get JSON-RPC request from POST body
        if request.method == 'POST':
            # Handle both JSON and multipart/form-data requests
            if request.is_json:
                # Standard JSON request
                try:
                    mcp_request = request.get_json()
                except Exception as e:
                    return json.dumps({
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                            "data": str(e)
                        },
                        "id": None
                    }), 400, {'Content-Type': 'application/json'}
            elif request.form and 'jsonrpc' in request.form:
                # Multipart request with JSON-RPC in form field
                try:
                    jsonrpc_str = request.form.get('jsonrpc')
                    mcp_request = json.loads(jsonrpc_str)
                except Exception as e:
                    return json.dumps({
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                            "data": f"Failed to parse JSON-RPC from form data: {str(e)}"
                        },
                        "id": None
                    }), 400, {'Content-Type': 'application/json'}
            else:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                        "data": "Content-Type must be application/json or multipart/form-data with 'jsonrpc' field"
                    },
                    "id": None
                }), 400, {'Content-Type': 'application/json'}
        else:
            # GET request - create minimal JSON-RPC from query params
            # This allows testing via GET, but POST is preferred for JSON-RPC
            method = request.args.get('method', '')
            if not method:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request",
                        "data": "Missing 'method' parameter"
                    },
                    "id": None
                }), 400, {'Content-Type': 'application/json'}
            
            # Build params from remaining query params
            params = {}
            request_id = request.args.get('id')
            for key, value in request.args.items():
                if key not in ['method', 'id']:
                    params[key] = value
            
            mcp_request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": request_id
            }
        
        if not mcp_request:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "Empty request body"
                },
                "id": None
            }), 400, {'Content-Type': 'application/json'}
        
        # Validate JSON-RPC structure
        if not isinstance(mcp_request, dict) or mcp_request.get("jsonrpc") != "2.0":
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                    "data": "Invalid JSON-RPC 2.0 request"
                },
                "id": mcp_request.get("id") if isinstance(mcp_request, dict) else None
            }), 400, {'Content-Type': 'application/json'}
        
        # Extract path segments as positional argv (command/subcommands)
        path_argv = []
        if path:
            path_parts = path.split('/')[:50]
            path_argv = [p[:128] for p in path_parts if p]
        
        # Extract query string params as additional argv (for GET/POST arrays)
        query_argv = []
        for key, value in request.args.items():
            if key not in ['method', 'id']:  # Skip JSON-RPC specific params
                k = str(key)[:64]
                v = str(value)[:512]
                query_argv.extend([f'--{k}', v])

        # Extract form fields (application/x-www-form-urlencoded or multipart/form-data)
        form_argv = []
        if request.form:
            for key in request.form.keys():
                try:
                    value = request.form.get(key)
                except Exception:
                    value = None
                k = str(key)[:64]
                if value is not None:
                    v = str(value)[:131072]  # allow large text fields
                    form_argv.extend([f'--{k}', v])

        # Handle file uploads: save to /tmp and pass file metadata via flags
        file_argv = []
        if request.files:
            idx = 0
            for key in request.files.keys():
                file_storage = request.files.get(key)
                if not file_storage:
                    continue
                original_name = os.path.basename(file_storage.filename or '')[:128]
                content_type = (file_storage.mimetype or '')[:128]
                # Create unique temp file in /tmp
                tmp_basename = f"henhouse_mcp_{uuid.uuid4().hex}"
                tmp_dir = "/tmp"
                tmp_path = os.path.join(tmp_dir, tmp_basename)
                try:
                    with open(tmp_path, 'wb') as f:
                        file_storage.save(f)
                except Exception as e:
                    logging.error(f"Failed to save upload to tmp: {e}")
                    continue
                # Append flags for this file
                file_argv.extend([
                    f"--file{idx}_key", key[:64],
                    f"--file{idx}_path", tmp_path,
                    f"--file{idx}_name", original_name,
                    f"--file{idx}_type", content_type
                ])
                idx += 1
        
        # Log MCP request with actual parameter values (truncated for readability)
        method = mcp_request.get('method', 'unknown')
        params = mcp_request.get('params', {})
        
        # Format params for logging (truncate if too long)
        params_str = json.dumps(params, indent=None, default=str)
        if len(params_str) > 500:
            params_str = params_str[:500] + "... (truncated)"
        
        logging.info(f"MCP request: method={method}, params={params_str}, path parts={len(path_argv)}, query params={len(query_argv)//2}, form fields={len(form_argv)//2}, files={len(file_argv)//4}")
        
        # Call MCP Gateway via subprocess
        try:
            mcp_script = PROJECT_ROOT / 'mcp_client.py'
            # Order: path positional args, then query flags, form flags, then file flags
            cmd = ['python3', str(mcp_script)] + path_argv + query_argv + form_argv + file_argv
            
            acquired = _gateway_semaphore.acquire(timeout=10)
            if not acquired:
                logging.error("Gateway concurrency limit reached for MCP request")
                return json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": "Server busy, please retry"
                    },
                    "id": mcp_request.get("id")
                }), 503, {'Content-Type': 'application/json'}
            
            try:
                # Pass JSON-RPC request via stdin and tier via environment
                json_input = json.dumps(mcp_request)
                env = os.environ.copy()
                env['USER_TIER'] = TIER_SUFFIX
                result = subprocess.run(
                    cmd,
                    input=json_input,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(PROJECT_ROOT),
                    env=env
                )
            finally:
                _gateway_semaphore.release()
            
            # Parse JSON response from mcp_client
            if result.stdout and result.stdout.strip():
                try:
                    # Validate it's valid JSON
                    response_json = json.loads(result.stdout)
                    # Log successful response (truncated)
                    response_preview = result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout
                    logging.info(f"MCP response: status={200 if result.returncode == 0 else 500}, preview={response_preview}")
                    return result.stdout, 200 if result.returncode == 0 else 500, {'Content-Type': 'application/json'}
                except json.JSONDecodeError as e:
                    # Log the invalid JSON error
                    logging.error(f"MCP response JSON decode error: {e}, stdout={result.stdout[:500]}, stderr={result.stderr[:500] if result.stderr else 'none'}")
                    # If not JSON, wrap in error
                    return json.dumps({
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": f"Invalid JSON from mcp_client: {result.stdout[:200]}"
                        },
                        "id": mcp_request.get("id")
                    }), 500, {'Content-Type': 'application/json'}
            else:
                # Empty stdout - trust return code
                if result.returncode == 0:
                    # Success with no output (e.g., notifications)
                    return "", 204, {'Content-Type': 'application/json'}
                
                stderr_snippet = (result.stderr or '').strip()
                logging.error(f"mcp_client returned {result.returncode}: {stderr_snippet}")
                return json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": stderr_snippet or "Empty response from gateway"
                    },
                    "id": mcp_request.get("id")
                }), 500, {'Content-Type': 'application/json'}
                
        except subprocess.TimeoutExpired:
            logging.error("mcp_client timeout")
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": "Request timeout"
                },
                "id": mcp_request.get("id")
            }), 504, {'Content-Type': 'application/json'}
        except Exception as e:
            logging.error(f"MCP subprocess error: {e}")
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                },
                "id": mcp_request.get("id") if isinstance(mcp_request, dict) else None
            }), 502, {'Content-Type': 'application/json'}
            
    except Exception as e:
        logging.error(f"Error in MCP handler: {e}")
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            "id": None
        }), 500, {'Content-Type': 'application/json'}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def dynamic_handler(path):
    """Route all requests through Gateway."""
    try:
        # Parse path and query string into command arguments
        # HTTP backend now only supports show-page command
        raw_argv = []
        
        # Always inject "show-page" as the command
        raw_argv.append("show-page")
        
        # Treat empty path as "1" (root/homepage)
        if not path:
            path = "1"
        
        # Determine what to skip from query params based on path type
        skip_params = []
        
        # Check if path is numeric (just digits)
        if path.isdigit():
            # Numeric path: use as page ID
            raw_argv.extend(['--id', path])
            # Skip id and page_id from query string (path takes precedence)
            skip_params = ['id', 'page_id']
        else:
            # Non-numeric path: treat entire path (including slashes) as page name
            # Convert multi-segment paths like "Bob/Sally/Wendy" into single name string
            page_name = path  # Keep entire path as one string, including slashes
            raw_argv.extend(['--name', page_name])
            # Skip id, page_id, link, and name from query string (path takes precedence)
            skip_params = ['id', 'page_id', 'link', 'name']
        
        # Add query parameters as arguments (excluding those we skip)
        added = 0
        for key, value in request.args.items():
            if added >= 100:
                break
            if value is not None:
                k = str(key)[:64]
                k_lower = k.lower()
                # Skip parameters that conflict with path-based arguments
                if k_lower in skip_params:
                    continue
                v = str(value)[:512]
                raw_argv.extend([f'--{k}', v])
                added += 1
        
        logging.info(f"Gateway request: {raw_argv}")
        
        # Call Gateway via subprocess to avoid state persistence
        try:
            http_script = PROJECT_ROOT / 'http_client.py'
            cmd = ['python3', str(http_script)] + raw_argv
            
            acquired = _gateway_semaphore.acquire(timeout=10)
            if not acquired:
                logging.error("Gateway concurrency limit reached")
                return _fallback_response("Server busy, please retry"), 503
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,  # reduced timeout
                    cwd=str(PROJECT_ROOT)
                )
            finally:
                _gateway_semaphore.release()
            
            response = result.stdout
            if response and response.strip():
                if response.strip().startswith('{'):
                    return response, 200 if result.returncode == 0 else 500, {'Content-Type': 'application/json'}
                else:
                    return response, 200 if result.returncode == 0 else 500, {'Content-Type': 'text/html; charset=utf-8'}
            else:
                stderr_snippet = (result.stderr or '').strip()
                logging.error(f"http_client returned {result.returncode}: {stderr_snippet}")
                return f"""
                <html><body>
                    <h1>Gateway Error</h1>
                    <p>Error processing request.</p>
                    <pre>{stderr_snippet}</pre>
                </body></html>
                """, 500
                
        except subprocess.TimeoutExpired:
            logging.error("http_client timeout")
            return _fallback_response("Request timeout"), 504
        except Exception as e:
            logging.error(f"Subprocess error: {e}")
            return _fallback_response(f"Subprocess error: {e}"), 502
            
    except Exception as e:
        logging.error(f"Error in dynamic handler: {e}")
        return f"""
        <html><body>
            <h1>Error</h1>
            <p>Error processing request: {e}</p>
            <p>Path: {path}</p>
        </body></html>
        """, 500

def _fallback_response(message: str):
    """Fallback response when Gateway isn't working."""
    project_cnf_path = Path.home() / f'.{PROJECT_NAME}.cnf'
    project_cnf_content = ""
    
    if project_cnf_path.exists():
        try:
            with open(project_cnf_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                project_cnf_content = ''.join(lines[:2])
        except Exception as e:
            project_cnf_content = f"Error reading .{PROJECT_NAME}.cnf: {e}"
    else:
        project_cnf_content = f".{PROJECT_NAME}.cnf file not found"
    
    return f"""
    <html><body>
        <h1>Henhouse Flask App</h1>
        <h2>TIER: {TIER_SUFFIX.upper()}</h2>
        <p>Project: {PROJECT_NAME}</p>
        <p>Status: {message}</p>
        <h3>Project Configuration (~/.{PROJECT_NAME}.cnf):</h3>
        <pre style="background: #f5f5f5; padding: 10px; border: 1px solid #ddd; white-space: pre-wrap;">{project_cnf_content}</pre>
    </body></html>
    """

@app.route('/status')
def status():
    """Health check endpoint."""
    return {
        'status': 'running',
        'tier': TIER_SUFFIX,
        'project': PROJECT_NAME,
        'site_dir': str(SITE_DIR)
    }

if __name__ == '__main__':
    # Run on all interfaces so Nginx can proxy
    port = int(os.getenv('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=False)


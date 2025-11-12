from __future__ import annotations
import datetime as dt
from typing import Dict, Any
from hh.gateway.connection.decorators import db_write
from hh.gateway.connection.connection import r_query, c_query
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.deploy.utils import detect_project_context
from hh.page.page_registry import get_page, find_page
from hh.image.image_registry import get_image
from hh.page.page import Page
from hh.image.image import Image

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


@db_write
def check_pages_empty(conn) -> bool:
    trace_in()
    query = "SELECT COUNT(*) as count FROM pages"
    results = r_query(conn, query)
    if not results:
        warn("Failed to check pages table")
        trace_out()
        return False
    count = results[0]["count"]
    log(f"Pages table has {count} records")
    trace_out()
    return count == 0


@db_write
def create_homepage(conn, project_name: str) -> Dict[str, Any]:
    trace_in()
    # Check if pages table is empty first
    if not check_pages_empty(conn):
        warn("Pages table is not empty - cannot create homepage")
        trace_out()
        return {"error": "Pages table is not empty. Homepage can only be created when table is empty."}
    # Get current timestamp and database user
    now = dt.datetime.now()
    # Get current database user
    user_results = r_query(conn, "SELECT USER() as db_user")
    db_user = user_results[0]['db_user'] if user_results else 'unknown'
    # Insert homepage record
    query = """
        INSERT INTO pages (id, parent, name, link, class, text, last_modified, username, visibility, displayStyle)
        VALUES (1, 0, %s, NULL, 'page', 'Hello, World!', %s, %s, 1, 1)
    """
    try:
        new_page_id = c_query(conn, query, (project_name, now, db_user))
        log(f"Created homepage: id=1, name='{project_name}', parent=0")
        result = {
            "homepage_id": 1,
            "project_name": project_name,
            "parent": 0,
            "name": project_name,
            "link": None,
            "class": "page",
            "text": "Hello, World!",
            "created_at": now.isoformat(),
            "username": db_user
        }
        trace_out()
        return result
    except Exception as e:
        warn(f"Failed to create homepage: {str(e)}")
        report_error("backend", f"Failed to create homepage: {str(e)}")
        trace_out()
        return {"error": f"Failed to create homepage: {str(e)}"}


@register_action('init_homepage')
@register_command('init_homepage')
def init_homepage() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    try:
        # Get project name
        project_name, project_path = detect_project_context()
        log(f"Detected project: {project_name}")
        # Create homepage
        result = create_homepage(project_name=project_name)
        if "error" in result:
            warn(f"Homepage creation failed: {result['error']}")
            report_error("action", result['error'])
            trace_out()
            return False
        log(f"Homepage created successfully for project: {project_name}")
        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True
    except Exception as e:
        warn(f"Homepage creation failed: {str(e)}")
        report_error("backend", f"Homepage creation failed: {str(e)}")
        trace_out()
        return False

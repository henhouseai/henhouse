"""
Hookified database initialization orchestrator.

Calls module hooks to initialize database schemas in a distributed way.
Each module owns its own schema SQL files and hooks.
"""

import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.registry.module_hooks import run_hooks
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload, get_data
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.install_helpers_config import get_install_config_path
from hh.deploy.db_config import DB_CONFIG
from hh.render.render import render_header_block, finalize_output
import configparser

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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


def _load_install_config(project_name: str) -> Optional[Dict[str, Any]]:
    """Load root install config and return MySQL root passwords."""
    cfg_path = get_install_config_path(project_name)
    if not cfg_path.exists():
        warn(f"Root install config not found: {cfg_path}")
        return None
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if "install" not in parser:
        warn(f"Missing [install] section in {cfg_path}")
        return None
    sec = parser["install"]

    def req(key: str) -> str:
        val = sec.get(key, "").strip()
        if not val:
            raise ValueError(f"Missing required field {key} in {cfg_path}")
        return val

    data: Dict[str, Any] = {
        "mysql_root_password_main": req("mysql_root_password_main"),
        "mysql_root_password_cache": req("mysql_root_password_cache"),
    }

    # MySQL TLS settings
    mysql_tls_enabled_str = sec.get("mysql_tls_enabled", "0").strip()
    try:
        data["mysql_tls_enabled"] = int(mysql_tls_enabled_str) != 0
    except ValueError:
        data["mysql_tls_enabled"] = False

    data["mysql_ssl_dir"] = sec.get("mysql_ssl_dir", "/etc/mysql/ssl").strip()
    data["ssl_ca_path"] = sec.get("ssl_ca_path", "").strip()
    data["cache_ssl_ca_path"] = sec.get("cache_ssl_ca_path", "").strip()
    data["db_host"] = sec.get("db_host", "").strip()

    # Read ssl_verify_mode from root user's .{project}.cnf file
    root_config_path = Path('/root') / f'.{project_name}.cnf'
    ssl_verify_mode = 2  # default
    if root_config_path.exists():
        root_config = configparser.ConfigParser()
        root_config.read(root_config_path)
        if 'client' in root_config:
            try:
                ssl_verify_mode = int(root_config.get('client', 'ssl_verify_mode', fallback='2'))
            except (ValueError, configparser.NoOptionError):
                ssl_verify_mode = 2
    data["ssl_verify_mode"] = ssl_verify_mode

    return data


@register_action('init_db')
@register_command('init_db')
def init_db(args: Optional[List[str]] = None) -> bool:
    """Initialize database schemas using module hooks."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False

    # Validate privileges
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        warn("init_db requires sudo/root privileges")
        report_error("action", "init_db requires sudo/root privileges")
        trace_out()
        return False

    if not gateway.get_arg('root'):
        warn("Root flag (-root) is required for init_db")
        report_error("action", "Root flag (-root) is required for init_db")
        trace_out()
        return False

    confirm = gateway.get_arg('confirm')
    if not confirm:
        warn("--confirm flag is required for init_db")
        report_error("action", "--confirm flag is required for init_db")
        trace_out()
        return False

    project_name, project_path = detect_project_context()
    log(f"Starting hookified database initialization for project: {project_name}")

    # Load root passwords from install config
    cfg = _load_install_config(project_name)
    if not cfg:
        warn("Failed to load root install config")
        report_error("action", "Failed to load root install config")
        trace_out()
        return False

    # Populate global DB_CONFIG for hooks to access
    DB_CONFIG["project_name"] = project_name
    DB_CONFIG["project_path"] = str(project_path)
    DB_CONFIG["main_db"] = project_name
    DB_CONFIG["cache_db"] = f"{project_name}_cache"
    DB_CONFIG["root_password_main"] = str(cfg["mysql_root_password_main"])
    DB_CONFIG["root_password_cache"] = str(cfg["mysql_root_password_cache"])
    DB_CONFIG["mysql_tls_enabled"] = bool(cfg.get("mysql_tls_enabled", False))
    DB_CONFIG["ssl_ca_path"] = str(cfg.get("ssl_ca_path", ""))
    DB_CONFIG["cache_ssl_ca_path"] = str(cfg.get("cache_ssl_ca_path", ""))
    DB_CONFIG["ssl_verify_mode"] = int(cfg.get("ssl_verify_mode", 2))
    DB_CONFIG["db_host"] = str(cfg.get("db_host", ""))

    hook_results: List[Dict[str, Any]] = []

    # Phase 00: Pre-validation (load config, create credential files)
    if not is_error():
        log("Running pre-validation hooks")
        results = run_hooks('init_db_00_pre_validate')
        if results:
            hook_results.extend(results)

    # Phase 05: Create main database
    if not is_error():
        log("Creating main database")
        results = run_hooks('init_db_05_create_main_db')
        if results:
            hook_results.extend(results)

    # Phase 10: Create cache database
    if not is_error():
        log("Creating cache database")
        results = run_hooks('init_db_10_create_cache_db')
        if results:
            hook_results.extend(results)

    # Phase 15: Initialize page tables in main DB
    if not is_error():
        log("Initializing page tables in main database")
        results = run_hooks('init_db_15_init_page_main')
        if results:
            hook_results.extend(results)

    # Phase 20: Initialize page cache tables in cache DB
    if not is_error():
        log("Initializing page cache tables")
        results = run_hooks('init_db_20_init_page_cache')
        if results:
            hook_results.extend(results)

    # Phase 25: Initialize media tables in main DB (all media types parallel)
    if not is_error():
        log("Initializing media tables in main database")
        results = run_hooks('init_db_25_init_media_main')
        if results:
            hook_results.extend(results)

    # Phase 30: Initialize media cache tables in cache DB (all media types parallel)
    if not is_error():
        log("Initializing media cache tables")
        results = run_hooks('init_db_30_init_media_cache')
        if results:
            hook_results.extend(results)

    # Phase 90: Cleanup (remove credential files)
    if not is_error():
        log("Running cleanup hooks")
        results = run_hooks('init_db_90_cleanup')
        if results:
            hook_results.extend(results)

    if not is_error():
        result_data = {
            "hook_results": hook_results,
            "project_name": project_name
        }
        gateway.response.set_action_response(success_payload(result_data))
    else:
        log("Database initialization encountered problems")

    return trace_out(not is_error())


@register_parser('init_db')
def render_init_db() -> bool:
    """
    Hookified renderer for init_db action.

    Processes init_db_95_render hooks from modules to build summary table.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_init_db")
        trace_out()
        return False

    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    # Get project name from action response
    json_data = gateway.response.get_action_response()
    debug(json_data)
    source_data = get_data(json_data if json_data is not None else {})
    project_name = source_data.get('project_name', 'Unknown')

    lines = []
    lines.append(render_header_block('l_init_db_header'))
    log(f"Processing hookified init_db data for project: {project_name}")

    # Call init_db_95_render hooks from all modules
    from hh.render.render import render_block, FieldConfig, TableData
    from hh.render.config.config import break_section

    render_instructions = run_hooks('init_db_95_render')

    # Separate pieces for summary table vs full tables
    summary_table_data = TableData()
    summary_field_config = FieldConfig()
    full_tables = []  # List of (instruction_index, render_block) tuples

    # Add project name as first row of summary table
    summary_table_data.add_row('project_header', value=project_name)

    # Process each render instruction and collect pieces
    for i, instruction in enumerate(render_instructions):
        if 'render_block' in instruction:
            # Full table - collect for insertion at this position
            full_tables.append((i, instruction['render_block']))
        elif 'table_data' in instruction and 'field_config' in instruction:
            # Piece for summary table - aggregate it
            piece_table_data = instruction['table_data']
            piece_field_config = instruction['field_config']

            # Merge table data (add all rows)
            for row in piece_table_data.rows:
                summary_table_data.rows.append(row)

            # Merge field configs (add all simple fields - hooks should NOT define headers)
            summary_field_config.configs.extend(piece_field_config.configs)

    # Build output: summary table first, then full tables
    if summary_table_data.num_rows() > 0:
        # Add project_header field to config
        project_config = FieldConfig()
        project_config.add_simple(['project_header'])
        summary_field_config.configs.extend(project_config.configs)

        # Add summary header since we have content (hooks only provide simple fields)
        summary_field_config.add_header('init_db_summary')
        summary_block = render_block(summary_table_data, summary_field_config, table_overrides={'margin_l': 4}, block_type='init_db_summary')
        lines.append(summary_block)
        break_section(lines)

    # Add full tables in the order they appeared
    for _, full_table_html in full_tables:
        lines.append(full_table_html)
        break_section(lines)

    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Hookified parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

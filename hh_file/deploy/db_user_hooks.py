"""
Database user permission hooks for hh_image module.

Grants and revokes tier user permissions on image tables.
"""

from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.error.error_store import is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway
from hh.deploy.db_config import DB_CONFIG
from hh.deploy.db_user_helpers import get_tier_permissions, grant_permissions, revoke_permissions
from hh.render.render import TableData, FieldConfig

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


@register_module_hook('add_db_users_20_grant_media_main', 'Grant image permissions on main DB')
def grant_image_main_permissions():
    """Grant tier user permissions on image tables in main database."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    gateway = get_gateway()
    if not gateway or not gateway.conn or not gateway.conn.main:
        warn("No gateway or connection available")
        return trace_out({"success": False, "message": "No connection available"})

    conn = gateway.conn.main
    project_name = DB_CONFIG.get("project_name")
    main_db = DB_CONFIG.get("main_db")
    tier_list = DB_CONFIG.get("tier_list", [])

    if not tier_list:
        warn("Tier list not found in DB_CONFIG")
        return trace_out({"success": False, "message": "Tier list not loaded"})

    for tier in tier_list:
        username = f"{project_name}_{tier}"
        permissions = get_tier_permissions(tier)
        grant_permissions(conn, username, main_db, permissions)

    log(f"Granted image permissions on {main_db} for all tiers")

    return trace_out({"success": True, "message": "Granted image permissions on main DB"})


@register_module_hook('add_db_users_25_grant_media_cache', 'Grant file permissions on cache DB')
def grant_file_cache_permissions():
    """Grant tier user permissions on file tables in cache database."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    gateway = get_gateway()
    if not gateway or not gateway.conn or not gateway.conn.main:
        warn("No gateway or connection available")
        return trace_out({"success": False, "message": "No connection available"})

    conn = gateway.conn.main
    project_name = DB_CONFIG.get("project_name")
    cache_db = DB_CONFIG.get("cache_db")
    tier_list = DB_CONFIG.get("tier_list", [])

    if not tier_list:
        warn("Tier list not found in DB_CONFIG")
        return trace_out({"success": False, "message": "Tier list not loaded"})

    for tier in tier_list:
        username = f"{project_name}_{tier}"
        permissions = get_tier_permissions(tier)
        grant_permissions(conn, username, cache_db, permissions)

    log(f"Granted file permissions on {cache_db} for all tiers")

    return trace_out({"success": True, "message": "Granted file permissions on cache DB"})


@register_module_hook('remove_db_users_15_revoke_media_main', 'Revoke file permissions on main DB')
def revoke_file_main_permissions():
    """Revoke tier user permissions on file tables in main database."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    gateway = get_gateway()
    if not gateway or not gateway.conn or not gateway.conn.main:
        warn("No gateway or connection available")
        return trace_out({"success": False, "message": "No connection available"})

    conn = gateway.conn.main
    project_name = DB_CONFIG.get("project_name")
    main_db = DB_CONFIG.get("main_db")
    tier_list = DB_CONFIG.get("tier_list", [])

    if not tier_list:
        warn("Tier list not found in DB_CONFIG")
        return trace_out({"success": False, "message": "Tier list not loaded"})

    for tier in tier_list:
        username = f"{project_name}_{tier}"
        permissions = get_tier_permissions(tier)
        revoke_permissions(conn, username, main_db, permissions)

    log(f"Revoked file permissions on {main_db} for all tiers")

    return trace_out({"success": True, "message": "Revoked file permissions on main DB"})


@register_module_hook('remove_db_users_05_revoke_media_cache', 'Revoke file permissions on cache DB')
def revoke_file_cache_permissions():
    """Revoke tier user permissions on file tables in cache database."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    gateway = get_gateway()
    if not gateway or not gateway.conn or not gateway.conn.main:
        warn("No gateway or connection available")
        return trace_out({"success": False, "message": "No connection available"})

    conn = gateway.conn.main
    project_name = DB_CONFIG.get("project_name")
    cache_db = DB_CONFIG.get("cache_db")
    tier_list = DB_CONFIG.get("tier_list", [])

    if not tier_list:
        warn("Tier list not found in DB_CONFIG")
        return trace_out({"success": False, "message": "Tier list not loaded"})

    for tier in tier_list:
        username = f"{project_name}_{tier}"
        permissions = get_tier_permissions(tier)
        revoke_permissions(conn, username, cache_db, permissions)

    log(f"Revoked file permissions on {cache_db} for all tiers")

    return trace_out({"success": True, "message": "Revoked file permissions on cache DB"})


@register_module_hook('add_db_users_95_render', 'Render file permissions summary')
def render_file_permissions():
    """Contribute file permission info to add_db_users summary table."""
    trace_in()

    table_data = TableData()
    field_config = FieldConfig()

    table_data.add_row('hh_file_permissions', value='main DB (files), cache DB')

    field_config.add_simple(['hh_file_permissions'])

    return trace_out({
        'table_data': table_data,
        'field_config': field_config
    })


@register_module_hook('remove_db_users_95_render', 'Render file permissions revocation summary')
def render_file_permissions_revoked():
    """Contribute file permission revocation info to remove_db_users summary table."""
    trace_in()

    table_data = TableData()
    field_config = FieldConfig()

    table_data.add_row('hh_file_revoked', value='main DB, cache DB')

    field_config.add_simple(['hh_file_revoked'])

    return trace_out({
        'table_data': table_data,
        'field_config': field_config
    })

"""
Database user permission hooks for hh_page module.

Grants and revokes tier user permissions on page tables.
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


@register_module_hook('add_db_users_10_grant_page_main', 'Grant page permissions on main DB')
def grant_page_main_permissions():
    """Grant tier user permissions on page tables in main database."""
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

    grant_results = []

    for tier in tier_list:
        username = f"{project_name}_{tier}"
        permissions = get_tier_permissions(tier)

        success = grant_permissions(conn, username, main_db, permissions)

        grant_results.append({
            "tier": tier,
            "database": main_db,
            "permissions": permissions,
            "status": "granted" if success else "failed"
        })

    log(f"Granted page permissions on {main_db} for {len(tier_list)} tiers")

    return trace_out({
        "success": True,
        "message": f"Granted page permissions on main DB",
        "grant_results": grant_results
    })


@register_module_hook('add_db_users_15_grant_page_cache', 'Grant page permissions on cache DB')
def grant_page_cache_permissions():
    """Grant tier user permissions on page tables in cache database."""
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

    grant_results = []

    for tier in tier_list:
        username = f"{project_name}_{tier}"
        permissions = get_tier_permissions(tier)

        success = grant_permissions(conn, username, cache_db, permissions)

        grant_results.append({
            "tier": tier,
            "database": cache_db,
            "permissions": permissions,
            "status": "granted" if success else "failed"
        })

    log(f"Granted page permissions on {cache_db} for {len(tier_list)} tiers")

    return trace_out({
        "success": True,
        "message": f"Granted page permissions on cache DB",
        "grant_results": grant_results
    })


@register_module_hook('remove_db_users_20_revoke_page_main', 'Revoke page permissions on main DB')
def revoke_page_main_permissions():
    """Revoke tier user permissions on page tables in main database."""
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

    revoke_results = []

    for tier in tier_list:
        username = f"{project_name}_{tier}"
        permissions = get_tier_permissions(tier)

        success = revoke_permissions(conn, username, main_db, permissions)

        revoke_results.append({
            "tier": tier,
            "database": main_db,
            "permissions": permissions,
            "status": "revoked" if success else "failed"
        })

    log(f"Revoked page permissions on {main_db} for {len(tier_list)} tiers")

    return trace_out({
        "success": True,
        "message": f"Revoked page permissions on main DB",
        "revoke_results": revoke_results
    })


@register_module_hook('remove_db_users_10_revoke_page_cache', 'Revoke page permissions on cache DB')
def revoke_page_cache_permissions():
    """Revoke tier user permissions on page tables in cache database."""
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

    revoke_results = []

    for tier in tier_list:
        username = f"{project_name}_{tier}"
        permissions = get_tier_permissions(tier)

        success = revoke_permissions(conn, username, cache_db, permissions)

        revoke_results.append({
            "tier": tier,
            "database": cache_db,
            "permissions": permissions,
            "status": "revoked" if success else "failed"
        })

    log(f"Revoked page permissions on {cache_db} for {len(tier_list)} tiers")

    return trace_out({
        "success": True,
        "message": f"Revoked page permissions on cache DB",
        "revoke_results": revoke_results
    })


@register_module_hook('add_db_users_95_render', 'Render page permissions summary')
def render_page_permissions():
    """Contribute page permission info to add_db_users summary table."""
    trace_in()

    table_data = TableData()
    field_config = FieldConfig()

    table_data.add_row('hh_page_permissions', value='main DB (pages, links), cache DB')

    field_config.add_simple(['hh_page_permissions'])

    return trace_out({
        'table_data': table_data,
        'field_config': field_config
    })


@register_module_hook('remove_db_users_95_render', 'Render page permissions revocation summary')
def render_page_permissions_revoked():
    """Contribute page permission revocation info to remove_db_users summary table."""
    trace_in()

    table_data = TableData()
    field_config = FieldConfig()

    table_data.add_row('hh_page_revoked', value='main DB, cache DB')

    field_config.add_simple(['hh_page_revoked'])

    return trace_out({
        'table_data': table_data,
        'field_config': field_config
    })

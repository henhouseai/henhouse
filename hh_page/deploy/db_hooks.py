"""
Database hooks for hh_page module.

Initializes and cleans page and link tables in main and cache databases.
"""

from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.error.error_store import is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init
from hh.deploy.db_helpers import execute_sql_file
from hh.deploy.db_config import DB_CONFIG
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


@register_module_hook('init_db_15_init_page_main', 'Initialize page and link tables')
def init_main_db():
    """Initialize page tables in main database."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    sql_file = Path(__file__).parent / "db" / "init.sql"

    success = execute_sql_file(
        sql_file,
        DB_CONFIG["main_db"],
        DB_CONFIG["main_credentials_file"],
        "hh_page init.sql"
    )

    if not success or is_error():
        return trace_out({"success": False, "message": "Failed to execute hh_page init.sql"})

    return trace_out({
        "success": True,
        "message": "hh_page main database tables created",
        "tables": ["pages", "links"]
    })


@register_module_hook('init_db_20_init_page_cache', 'Initialize page cache table')
def init_cache_db():
    """Initialize page cache table in cache database."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    sql_file = Path(__file__).parent / "db" / "init_cache.sql"

    success = execute_sql_file(
        sql_file,
        DB_CONFIG["cache_db"],
        DB_CONFIG["cache_credentials_file"],
        "hh_page init_cache.sql"
    )

    if not success or is_error():
        return trace_out({"success": False, "message": "Failed to execute hh_page init_cache.sql"})

    return trace_out({
        "success": True,
        "message": "hh_page cache database tables created",
        "tables": ["pages (cache)"]
    })


@register_module_hook('clean_db_10_clean_page_cache', 'Drop page cache tables')
def clean_cache_db():
    """Clean page cache tables from cache database."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    sql_file = Path(__file__).parent / "db" / "clean_cache.sql"

    success = execute_sql_file(
        sql_file,
        DB_CONFIG["cache_db"],
        DB_CONFIG["cache_credentials_file"],
        "hh_page clean_cache.sql"
    )

    if not success or is_error():
        return trace_out({"success": False, "message": "Failed to execute hh_page clean_cache.sql"})

    return trace_out({
        "success": True,
        "message": "hh_page cache tables dropped",
        "tables": ["pages (cache)"]
    })


@register_module_hook('clean_db_20_clean_page_main', 'Drop page and link tables')
def clean_main_db():
    """Clean page tables from main database."""
    trace_in()

    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    sql_file = Path(__file__).parent / "db" / "clean.sql"

    success = execute_sql_file(
        sql_file,
        DB_CONFIG["main_db"],
        DB_CONFIG["main_credentials_file"],
        "hh_page clean.sql"
    )

    if not success or is_error():
        return trace_out({"success": False, "message": "Failed to execute hh_page clean.sql"})

    return trace_out({
        "success": True,
        "message": "hh_page main database tables dropped",
        "tables": ["pages", "links"]
    })


@register_module_hook('init_db_95_render', 'Render page module summary')
def render_init_summary():
    """Contribute page module info to init_db summary table."""
    trace_in()

    table_data = TableData()
    field_config = FieldConfig()

    table_data.add_row('hh_page_tables', value='pages, links')

    field_config.add_simple(['hh_page_tables'])

    return trace_out({
        'table_data': table_data,
        'field_config': field_config
    })


@register_module_hook('clean_db_95_render', 'Render page module cleanup summary')
def render_clean_summary():
    """Contribute page module cleanup info to clean_db summary table."""
    trace_in()

    table_data = TableData()
    field_config = FieldConfig()

    table_data.add_row('hh_page_dropped', value='pages, links')

    field_config.add_simple(['hh_page_dropped'])

    return trace_out({
        'table_data': table_data,
        'field_config': field_config
    })


@register_module_hook('init_db_40_homepage', 'Create the home page (id 1, parent 0) if pages is empty')
def init_homepage():
    """
    Create the root page every other page hangs under.

    Restores the old init_homepage behaviour: page 1, parent 0, named after the project,
    created only when the pages table is empty.
    """
    trace_in()
    if is_error():
        return trace_out({"success": False, "message": "Error state detected"})

    import tempfile
    from hh.deploy.user_accounts import detect_project_owner

    project_name = DB_CONFIG["main_db"]
    owner = detect_project_owner(Path(DB_CONFIG.get("project_path") or ".")) or "root"
    sql = (
        "INSERT INTO pages (id, parent, name, link, class, text, last_modified, username, visibility, displayStyle) "
        "SELECT 1, 0, '{name}', NULL, 'page', 'Hello, World!', NOW(), '{user}', 1, 1 "
        "FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM pages);\n"
    ).format(name=project_name.replace("'", "''"), user=owner.replace("'", "''"))

    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as tmp:
        tmp.write(sql)
        tmp_path = Path(tmp.name)
    try:
        success = execute_sql_file(tmp_path, DB_CONFIG["main_db"], DB_CONFIG["main_credentials_file"], "hh_page homepage")
    finally:
        tmp_path.unlink(missing_ok=True)

    if not success or is_error():
        return trace_out({"success": False, "message": "Failed to create homepage"})
    DB_CONFIG["homepage_checked"] = True
    return trace_out({"success": True, "message": "Homepage present (id 1)"})

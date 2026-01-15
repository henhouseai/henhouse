"""
Users module deployment hooks.

Example hooks for testing the module hooks system.
"""

from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.gateway import get_gateway
from hh.gateway.connection.root_connection import RootConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
import datetime

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


@register_module_hook('deploy_before_schema')
def setup_database_users(project_name: str, config: dict):
    """
    Hook that runs before schema deployment.

    Example hook for users module that could set up database users
    with appropriate permissions before schema is deployed.

    Args:
        project_name: Name of the project being deployed
        config: Configuration dict for deployment
    """
    print(f"[users] deploy_before_schema: Setting up database users for {project_name}")
    # In real implementation, this would create DB users, grant permissions, etc.
    return True


@register_module_hook('deploy_after_schema')
def verify_user_tables(project_name: str, config: dict):
    """
    Hook that runs after schema deployment.

    Verifies that user-related tables were created successfully.

    Args:
        project_name: Name of the project being deployed
        config: Configuration dict for deployment
    """
    print(f"[users] deploy_after_schema: Verifying user tables for {project_name}")
    # In real implementation, this would query tables to verify they exist
    return True


@register_module_hook('install_config')
def write_user_config(project_name: str, config_path: str):
    """
    Hook that runs during installation to write module-specific config.

    Args:
        project_name: Name of the project being installed
        config_path: Path to config file
    """
    print(f"[users] install_config: Writing user module config to {config_path}")
    # In real implementation, this would write user module config sections
    return True


@register_module_hook('test-deploy-start')
def test_hook_log_to_database():
    """
    Test hook that writes to page 1782's metadata log to prove hooks execute during deployment.

    This is a smoke test hook - writes execution timestamp to work page 1782.
    """
    trace_in("test_hook_log_to_database")
    debug("Starting test-deploy-start hook execution")

    try:
        from hh.page.page_registry import get_page

        timestamp = datetime.datetime.utcnow().isoformat()
        debug(f"Hook executing at timestamp: {timestamp}")
        print(f"[users] test-deploy-start: Executing at {timestamp}")

        # Get page 1782
        debug("Loading page 1782 via get_page()")
        page = get_page(page_id=1782)
        if not page:
            warn("Could not load page 1782 - get_page returned None")
            print("[users] test-deploy-start: ERROR - Could not load page 1782")
            return trace_out(False)

        debug(f"Successfully loaded page 1782: class={page.class_name}, name={page.name}")

        # Add log entry using proper work page method
        log_data = {
            "message": "users test hook executed successfully during deployment",
            "timestamp": timestamp,
            "hook_name": "test-deploy-start"
        }

        debug(f"Calling page.work_add_log() with data: {log_data}")
        success = page.work_add_log(log_data)
        debug(f"page.work_add_log() returned: {success}")

        if success:
            log("Successfully logged hook execution to page 1782")
            print(f"[users] test-deploy-start: Successfully logged to page 1782")
        else:
            warn("page.work_add_log() returned False - log entry may not have been added")
            print(f"[users] test-deploy-start: work_add_log returned False")

        return trace_out(success)

    except Exception as e:
        warn(f"Exception in test hook: {e}")
        print(f"[users] test-deploy-start: ERROR - {e}")
        import traceback
        traceback.print_exc()
        return trace_out(False)


@register_module_hook('test-error-handling')
def test_hook_returns_false():
    """
    Test hook that returns False to test error handling.

    This hook intentionally returns False to verify that:
    1. run_hooks() catches the False return
    2. Error is logged appropriately
    3. Subsequent hooks (if any) are not executed
    4. Deployment script handles the failure correctly
    """
    trace_in("test_hook_returns_false")
    log("Test hook intentionally returning False")
    print("[users] test-error-handling: Intentionally returning False")
    return trace_out(False)


@register_module_hook('test-error-handling')
def test_hook_raises_exception():
    """
    Test hook that raises an exception to test error handling.

    This hook intentionally raises an exception to verify that:
    1. run_hooks() catches the exception
    2. Error is logged with exception details
    3. Subsequent hooks (if any) are not executed
    4. Deployment script handles the failure correctly
    """
    trace_in("test_hook_raises_exception")
    log("Test hook intentionally raising exception")
    print("[users] test-error-handling: About to raise exception")
    raise RuntimeError("Intentional test exception from hook")


@register_module_hook('test-error-handling')
def test_hook_should_not_execute():
    """
    Test hook that should never execute due to earlier failure.

    If this hook executes, it means error handling is not working correctly
    because the earlier hooks should have failed and stopped execution.
    """
    trace_in("test_hook_should_not_execute")
    warn("THIS HOOK SHOULD NOT HAVE EXECUTED - error handling failed!")
    print("[users] test-error-handling: ERROR - This hook should not have executed!")
    return trace_out(True)

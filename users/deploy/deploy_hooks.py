"""
Users module deployment hooks.

Example hooks for testing the module hooks system.
"""

from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.gateway import get_gateway
from hh.gateway.connection.root_connection import RootConnection
import datetime


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
    try:
        timestamp = datetime.datetime.utcnow().isoformat()
        print(f"[users] test-deploy-start: Executing at {timestamp}")

        # Get gateway to access connection
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            print("[users] test-deploy-start: WARNING - No gateway/connection available")
            return False

        # Write to page 1782's log metadata
        log_entry = f'{{"message": "users test hook executed successfully", "timestamp": "{timestamp}"}}'

        # Use direct SQL since we're in deployment context with root connection
        query = """
            UPDATE pages
            SET metadata = JSON_SET(
                COALESCE(metadata, '{}'),
                '$.log',
                JSON_ARRAY_APPEND(
                    COALESCE(JSON_EXTRACT(metadata, '$.log'), '[]'),
                    '$',
                    CAST(%s AS JSON)
                )
            )
            WHERE id = 1782
        """

        gateway.conn.update(query, (log_entry,))
        print(f"[users] test-deploy-start: Successfully logged to page 1782")

        return True

    except Exception as e:
        print(f"[users] test-deploy-start: ERROR - {e}")
        import traceback
        traceback.print_exc()
        return False

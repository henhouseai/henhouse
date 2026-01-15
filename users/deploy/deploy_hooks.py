"""
Users module deployment hooks.

Example hooks for testing the module hooks system.
"""

from hh.gateway.registry.module_hooks import register_module_hook


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

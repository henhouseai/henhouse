"""
History module deployment hooks.

Example hooks for testing the module hooks system.
"""

from hh.gateway.registry.module_hooks import register_module_hook


@register_module_hook('deploy_before_schema')
def create_history_database(project_name: str, config: dict):
    """
    Hook that runs before schema deployment.

    Creates the separate history database before schema deployment.

    Args:
        project_name: Name of the project being deployed
        config: Configuration dict for deployment
    """
    print(f"[history] deploy_before_schema: Creating history database for {project_name}")
    # In real implementation, this would create the history database
    return True


@register_module_hook('deploy_after_schema')
def verify_history_tables(project_name: str, config: dict):
    """
    Hook that runs after schema deployment.

    Verifies that history tables were created successfully in the history database.

    Args:
        project_name: Name of the project being deployed
        config: Configuration dict for deployment
    """
    print(f"[history] deploy_after_schema: Verifying history tables for {project_name}")
    # In real implementation, this would verify page_history and media_history tables exist
    return True

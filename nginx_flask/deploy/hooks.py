"""
NGINX/Flask deployment hooks
"""
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.flask.flask_start import run_flask_start
from hh.deploy.flask.flask_stop import run_flask_stop
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn

log = lambda message: None
warn = lambda message: None

def _init_debug():
    global log, warn
    log = get_log(True)
    warn = get_warn(True)

try:
    _init_debug()
except:
    pass

@register_module_hook('deploy_stop_daemons')
def stop_flask_daemons() -> bool:
    """Stop Flask tier daemons before deployment."""
    try:
        project_name, _ = detect_project_context()
        if not project_name:
            warn("nginx_flask hook: Could not detect project name")
            return False

        log(f"nginx_flask hook: Stopping Flask daemons for {project_name}")
        run_flask_stop(project_name)
        log(f"nginx_flask hook: Flask daemons stopped")

        return True
    except Exception as e:
        warn(f"nginx_flask hook: Failed to stop Flask daemons: {e}")
        return False


@register_module_hook('deploy_restart_daemons')
def restart_flask_daemons() -> bool:
    """Restart Flask tier daemons after deployment."""
    try:
        project_name, _ = detect_project_context()
        if not project_name:
            warn("nginx_flask hook: Could not detect project name")
            return False

        # Get start_port from install config
        from hh.deploy.users.install import _install_config_path
        import configparser
        cfg_path = _install_config_path(project_name)
        start_port = 5001
        if cfg_path.exists():
            parser = configparser.ConfigParser()
            parser.read(cfg_path)
            if "install" in parser:
                port_str = parser["install"].get("flask_start_port", "5001").strip()
                try:
                    start_port = int(port_str)
                except ValueError:
                    start_port = 5001

        log(f"nginx_flask hook: Starting Flask daemons for {project_name}")
        flask_restart_info = run_flask_start(project_name, start_port)
        log(f"nginx_flask hook: Flask restart summary: {flask_restart_info.get('summary')}")

        return True
    except Exception as e:
        warn(f"nginx_flask hook: Failed to restart Flask daemons: {e}")
        return False

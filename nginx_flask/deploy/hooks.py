"""
NGINX/Flask deployment hooks
"""
from typing import Dict, Any, Union, List
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.flask.flask_start import run_flask_start
from hh.deploy.flask.flask_stop import run_flask_stop
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn
from hh.gateway.error.error_store import report_error

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
def stop_flask_daemons() -> Union[Dict[str, Any], bool]:
    """Stop Flask tier daemons before deployment."""
    try:
        project_name, _ = detect_project_context()
        if not project_name:
            warn("nginx_flask hook: Could not detect project name")
            return False

        log(f"nginx_flask hook: Stopping Flask daemons for {project_name}")
        run_flask_stop(project_name)
        log(f"nginx_flask hook: Flask daemons stopped")

        return {"module": "nginx_flask", "action": "stop", "status": "stopped"}
    except Exception as e:
        warn(f"nginx_flask hook: Failed to stop Flask daemons: {e}")
        return False


@register_module_hook('deploy_restart_daemons')
def restart_flask_daemons() -> Union[Dict[str, Any], bool]:
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

        return {"module": "nginx_flask", "action": "restart", "flask_restart": flask_restart_info}
    except Exception as e:
        warn(f"nginx_flask hook: Failed to restart Flask daemons: {e}")
        return False


@register_module_hook('deploy_flask_apps')
def deploy_flask_apps() -> Union[Dict[str, Any], bool]:
    """Deploy Flask tier applications and media server."""
    try:
        project_name, current_path = detect_project_context()
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

        from hh.deploy.conf.deploy_whitelist import FLASK_APP_SOURCE, MEDIA_SERVER_SOURCE
        from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

        source = current_path
        dest = Path("/srv") / project_name
        flask_deployed = []

        # Deploy Flask tier apps
        app_source = source / FLASK_APP_SOURCE
        if app_source.exists():
            for i, tier in enumerate(HENHOUSE_TIERS):
                app_name = f'{project_name}_{tier}.py'
                app_dest = dest / app_name

                # Read the app.py content
                with open(app_source, 'r') as f:
                    content = f.read()

                # Replace the port with the tier-specific port
                port = start_port + i
                content = content.replace('port = int(os.getenv(\'PORT\', 5000))', f'port = {port}')

                # Replace the log file path with tier-specific path
                log_file = f'/srv/{project_name}/logs/flask_{project_name}_{tier}.log'
                content = content.replace('LOG_FILE = os.getenv(\'LOG_FILE\',', f'LOG_FILE = \'{log_file}\'  # LOG_FILE = os.getenv(\'LOG_FILE\',')

                # Write the modified content
                with open(app_dest, 'w') as f:
                    f.write(content)

                flask_deployed.append(app_name)
                log(f"nginx_flask hook: Deployed Flask app: {app_name} (port {port})")
            log(f"nginx_flask hook: Flask deployment complete: {len(flask_deployed)} instances")
        else:
            log("nginx_flask hook: Flask app.py not found, skipping Flask deployment")

        # Deploy media server Flask app
        media_source = source / MEDIA_SERVER_SOURCE
        media_deployed = False
        if media_source.exists():
            media_dest = dest / f'{project_name}_media.py'

            # Read the media_server.py content
            with open(media_source, 'r') as f:
                content = f.read()

            # Replace the port with media server port (after all tier apps)
            media_port = start_port + len(HENHOUSE_TIERS)
            content = content.replace('port = int(os.getenv(\'PORT\', 5000))', f'port = {media_port}')

            # Replace the log file path with media server path
            log_file = f'/srv/{project_name}/logs/flask_{project_name}_media.log'
            content = content.replace('LOG_FILE = os.getenv(\'LOG_FILE\',', f'LOG_FILE = \'{log_file}\'  # LOG_FILE = os.getenv(\'LOG_FILE\',')

            # Write the modified content
            with open(media_dest, 'w') as f:
                f.write(content)

            media_deployed = True
            log(f"nginx_flask hook: Deployed Media Server Flask app: {project_name}_media.py (port {media_port})")
        else:
            log("nginx_flask hook: Media server media_server.py not found, skipping media server deployment")

        return {
            "module": "nginx_flask",
            "action": "deploy_apps",
            "flask_deployed": flask_deployed,
            "media_deployed": media_deployed
        }
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy Flask apps: {e}")
        report_error("backend", f"nginx_flask hook: Failed to deploy Flask apps: {e}")
        return False

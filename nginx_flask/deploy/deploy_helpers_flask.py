"""
Flask deployment hooks for nginx_flask module.

These functions handle Flask tier daemon and application deployment operations.
"""
import os
from pathlib import Path
from typing import Dict, Any, List
from hh.deploy.flask.flask_start import run_flask_start
from hh.deploy.flask.flask_stop import run_flask_stop
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.gateway.registry.debug import get_log, get_warn, get_trace_in, get_trace_out, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.module_hooks import register_module_hook

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


@register_module_hook('deploy_stop_daemons')
def stop_flask_daemons() -> Dict[str, Any]:
    """Stop Flask tier daemons before deployment."""
    trace_in()

    project_name, _ = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    log(f"nginx_flask: Stopping Flask daemons for {project_name}")
    run_flask_stop(project_name)
    log(f"nginx_flask: Flask daemons stopped")

    return trace_out({"module": "nginx_flask", "action": "stop", "status": "stopped"})


@register_module_hook('deploy_restart_daemons')
def restart_flask_daemons() -> Dict[str, Any]:
    """Restart Flask tier daemons after deployment."""
    trace_in()

    project_name, _ = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

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

    log(f"nginx_flask: Starting Flask daemons for {project_name}")
    flask_restart_info = run_flask_start(project_name, start_port)
    log(f"nginx_flask: Flask restart summary: {flask_restart_info.get('summary')}")

    return trace_out({"module": "nginx_flask", "action": "restart", "flask_restart": flask_restart_info})


@register_module_hook('deploy_flask_apps')
def deploy_flask_apps() -> Dict[str, Any]:
    """Deploy Flask tier applications and media server."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

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

    # Load app sources from aggregated whitelist
    from hh.deploy.deploy_utils import load_tuple_whitelist_with_extensions
    app_whitelist = load_tuple_whitelist_with_extensions('deploy_whitelist', 'APP_WHITELIST')

    source = current_path
    dest = Path("/srv") / project_name
    flask_deployed: List[str] = []

    # Deploy Flask tier apps
    flask_source_path = None
    for app_item in app_whitelist:
        if isinstance(app_item, tuple) and len(app_item) == 2:
            app_name, source_path = app_item
            if app_name == 'flask':
                flask_source_path = source_path
                break

    if flask_source_path:
        app_source = source / flask_source_path
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
                log(f"nginx_flask: Deployed Flask app: {app_name} (port {port})")
            log(f"nginx_flask: Flask deployment complete: {len(flask_deployed)} instances")
        else:
            log("nginx_flask: Flask app.py not found, skipping Flask deployment")

    # Deploy media server Flask app
    media_source_path = None
    for app_item in app_whitelist:
        if isinstance(app_item, tuple) and len(app_item) == 2:
            app_name, source_path = app_item
            if app_name == 'media':
                media_source_path = source_path
                break

    media_deployed = False
    if media_source_path:
        media_source = source / media_source_path
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
            log(f"nginx_flask: Deployed Media Server Flask app: {project_name}_media.py (port {media_port})")
        else:
            log("nginx_flask: Media server media_server.py not found, skipping media server deployment")
    else:
        log("nginx_flask: Media server source path not found in APP_WHITELIST")

    return trace_out({
        "module": "nginx_flask",
        "action": "deploy_apps",
        "flask_deployed": flask_deployed,
        "media_deployed": media_deployed
    })

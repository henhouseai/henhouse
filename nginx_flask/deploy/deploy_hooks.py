"""
NGINX/Flask deployment hooks
"""
import os
import subprocess
from typing import Dict, Any, Union, List
from pathlib import Path
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.flask.flask_start import run_flask_start
from hh.deploy.flask.flask_stop import run_flask_stop
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_log, get_warn
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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


@register_module_hook('deploy_permissions_special')
def set_flask_logs_permissions() -> Dict[str, Any]:
    """Set special permissions for Flask daemon logs directory."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask permissions hook: Could not detect project name")
            return {"status": "error", "component": "flask_logs", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        import shutil
        gateway = get_gateway()
        dest = Path("/srv") / project_name
        logs_dir = dest / 'logs'

        # Clear existing logs directory and recreate
        if logs_dir.exists():
            shutil.rmtree(logs_dir)
            log(f"nginx_flask permissions hook: Cleared existing logs directory: {logs_dir}")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Set group write permissions for logs (2775)
        gateway.files.chmod(str(logs_dir), 0o2775)

        # Set ownership so Flask daemons can write logs
        project_highest_user = f"{project_name}_{HENHOUSE_TIERS[-1]}"
        user_info = gateway.os.get_user_by_name(project_highest_user)
        if not user_info:
            warn(f"nginx_flask permissions hook: User not found: {project_highest_user}")
            return {"status": "error", "component": "flask_logs", "error": "user_not_found"}

        project_highest_uid = user_info["uid"]
        deploy_group_name = f"{project_name}_deploy"
        subprocess.run(['chown', f'{project_highest_uid}:{deploy_group_name}', str(logs_dir)], check=True)

        log(f"nginx_flask permissions hook: Created fresh logs directory with group write: {logs_dir}")
        log(f"nginx_flask permissions hook: Set logs directory ownership: {project_highest_user}:{deploy_group_name}")

        return {
            "status": "completed",
            "component": "flask_logs",
            "permissions": "2775",
            "ownership": f"{project_highest_user}:{deploy_group_name}",
            "directory": str(logs_dir)
        }

    except Exception as e:
        warn(f"nginx_flask permissions hook: Failed to set Flask logs permissions: {e}")
        report_error("backend", f"nginx_flask permissions hook: Failed to set Flask logs permissions: {e}")
        return {"status": "error", "component": "flask_logs", "error": str(e)}


@register_module_hook('deploy_permissions_special')
def set_site_permissions() -> Dict[str, Any]:
    """Set special permissions for site files (HTML, JS, CSS, etc.)."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask permissions hook: Could not detect project name")
            return {"status": "error", "component": "site", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name
        site_dir = dest / 'site'

        if not site_dir.exists():
            log("nginx_flask permissions hook: Site directory does not exist, skipping site permissions")
            return {"status": "skipped", "component": "site", "reason": "no_site_dir"}

        # Ensure web-accessible files have proper permissions for nginx
        # Site files should be readable by web server (644 for files, 755 for dirs)
        import subprocess

        # Set directory permissions (755 - readable/executable by all, writable by owner)
        subprocess.run(['find', str(site_dir), '-type', 'd', '-exec', 'chmod', '755', '{}', ';'], check=True)

        # Set file permissions (644 - readable by all, writable by owner)
        subprocess.run(['find', str(site_dir), '-type', 'f', '-exec', 'chmod', '644', '{}', ';'], check=True)

        log(f"nginx_flask permissions hook: Set site directory permissions: 755/644 for {site_dir}")

        return {
            "status": "completed",
            "component": "site",
            "permissions": "755/644",
            "directory": str(site_dir),
            "note": "web_accessible_permissions"
        }

    except Exception as e:
        warn(f"nginx_flask permissions hook: Failed to set site permissions: {e}")
        report_error("backend", f"nginx_flask permissions hook: Failed to set site permissions: {e}")
        return {"status": "error", "component": "site", "error": str(e)}


@register_module_hook('deploy_site_prepare')
def prepare_site_directory() -> Dict[str, Any]:
    """Prepare the site directory by clearing and recreating it."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask site prepare hook: Could not detect project name")
            return {"status": "error", "component": "site_prepare", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        dest = Path("/srv") / project_name
        site_dest = dest / 'site'

        # Clear existing site directory and recreate
        if site_dest.exists():
            import shutil
            shutil.rmtree(site_dest)
            log(f"nginx_flask site prepare hook: Cleared existing site directory: {site_dest}")
        site_dest.mkdir(parents=True, exist_ok=True)
        log(f"nginx_flask site prepare hook: Created fresh site directory: {site_dest}")

        return {
            "status": "completed",
            "component": "site_prepare",
            "directory": str(site_dest),
            "action": "cleared_and_created"
        }

    except Exception as e:
        warn(f"nginx_flask site prepare hook: Failed to prepare site directory: {e}")
        report_error("backend", f"nginx_flask site prepare hook: Failed to prepare site directory: {e}")
        return {"status": "error", "component": "site_prepare", "error": str(e)}


@register_module_hook('deploy_site')
def deploy_site_css() -> Dict[str, Any]:
    """Deploy CSS files to the site directory."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask site css hook: Could not detect project name")
            return {"status": "error", "component": "site_css", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        source = current_path
        dest = Path("/srv") / project_name
        site_dest = dest / 'site'
        css_dest = site_dest / 'css'
        css_dest.mkdir(exist_ok=True)

        # Get CSS whitelist
        from hh.deploy.conf.css_whitelist import CSS_WHITELIST

        css_count = 0
        css_deployed = []

        for css_file in CSS_WHITELIST:
            source_css = source / css_file
            if source_css.exists():
                dest_css = css_dest / source_css.name
                if dest_css.exists():
                    dest_css.unlink()
                import shutil
                shutil.copy2(source_css, dest_css)
                css_deployed.append(f"css/{source_css.name}")
                css_count += 1
                log(f"nginx_flask site css hook: Deployed CSS file: {css_file} -> site/css/{source_css.name}")
            else:
                log(f"nginx_flask site css hook: CSS file not found: {css_file}")

        return {
            "status": "completed",
            "component": "site_css",
            "count": css_count,
            "files": css_deployed
        }

    except Exception as e:
        warn(f"nginx_flask site css hook: Failed to deploy CSS files: {e}")
        report_error("backend", f"nginx_flask site css hook: Failed to deploy CSS files: {e}")
        return {"status": "error", "component": "site_css", "error": str(e)}


@register_module_hook('deploy_site')
def deploy_site_js() -> Dict[str, Any]:
    """Deploy JavaScript files and generate registry."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask site js hook: Could not detect project name")
            return {"status": "error", "component": "site_js", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        source = current_path
        dest = Path("/srv") / project_name
        site_dest = dest / 'site'
        js_dest = site_dest / 'js'
        js_dest.mkdir(exist_ok=True)

        # Get JS whitelist
        from hh.deploy.conf.js_whitelist import JS_WHITELIST
        from hh.deploy.conf.js_page_classes_whitelist import JS_PAGE_CLASSES_WHITELIST

        js_count = 0
        js_deployed = []

        # Deploy JS files
        for js_item in JS_WHITELIST:
            source_item = source / js_item
            if source_item.exists():
                if source_item.is_dir():
                    # Deploy all .js files in directory preserving structure
                    for js_file in source_item.rglob('*.js'):
                        relative_path = js_file.relative_to(source_item)
                        dest_js = js_dest / relative_path
                        dest_js.parent.mkdir(parents=True, exist_ok=True)
                        if dest_js.exists():
                            dest_js.unlink()
                        import shutil
                        shutil.copy2(js_file, dest_js)
                        js_deployed.append(f"js/{relative_path.as_posix()}")
                        js_count += 1
                        log(f"nginx_flask site js hook: Deployed JS file from folder: {js_file} -> site/js/{relative_path.as_posix()}")
                else:
                    # Deploy single JS file
                    dest_js = js_dest / source_item.name
                    if dest_js.exists():
                        dest_js.unlink()
                    import shutil
                    shutil.copy2(source_item, dest_js)
                    js_deployed.append(f"js/{source_item.name}")
                    js_count += 1
                    log(f"nginx_flask site js hook: Deployed JS file: {js_item} -> site/js/{source_item.name}")
            else:
                log(f"nginx_flask site js hook: JS file/folder not found: {js_item}")

        # Generate page-classes-registry.js
        registry_deployed = []
        try:
            log("nginx_flask site js hook: Generating page-classes-registry.js")

            def kebab_to_pascal(kebab: str) -> str:
                parts = kebab.split('-')
                return ''.join(word.capitalize() for word in parts)

            def kebab_to_snake(kebab: str) -> str:
                return kebab.replace('-', '_')

            # Find page class files
            page_class_files = []
            registry_file_dir = source / 'hh' / 'deploy' / 'site' / 'js' / 'hh' / 'deploy' / 'site' / 'ts'
            hh_page_classes_dir = source / 'hh' / 'deploy' / 'site' / 'js' / 'hh' / 'deploy' / 'site' / 'ts' / 'page-classes'
            ext_page_classes_dir = source / 'hh' / 'deploy' / 'site' / 'js' / 'ext' / 'deploy' / 'site' / 'ts' / 'page-classes'

            ext_dir_exists = ext_page_classes_dir.exists() and ext_page_classes_dir.is_dir()
            if not ext_dir_exists:
                log("nginx_flask site js hook: Extension page-classes directory not found (this is normal if ext/ folder doesn't exist)")

            # Get active modules
            from hh.deploy.deploy_utils import get_active_modules
            modules = get_active_modules()
            log(f"nginx_flask site js hook: Found {len(modules)} active modules for page-classes discovery")

            for filename in JS_PAGE_CLASSES_WHITELIST:
                file_found = False

                # Check hh/
                hh_file = hh_page_classes_dir / filename
                if hh_file.exists() and hh_file.is_file():
                    relative_path = hh_file.relative_to(registry_file_dir)
                    relative_path_str = str(relative_path).replace('\\', '/')
                    if relative_path_str not in page_class_files:
                        page_class_files.append(relative_path_str)
                        log(f"nginx_flask site js hook: Found page class file in hh/: {relative_path_str}")
                        file_found = True

                # Check ext/
                if not file_found and ext_dir_exists:
                    ext_file = ext_page_classes_dir / filename
                    if ext_file.exists() and ext_file.is_file():
                        relative_path = ext_file.relative_to(registry_file_dir.parent.parent.parent.parent)
                        relative_path_str = str(relative_path).replace('\\', '/')
                        if relative_path_str not in page_class_files:
                            page_class_files.append(relative_path_str)
                            log(f"nginx_flask site js hook: Found page class file in ext/: {relative_path_str}")
                            file_found = True

                # Check modules
                if not file_found:
                    for module in modules:
                        module_page_classes_dir = source / 'hh' / 'deploy' / 'site' / 'js' / module.path / 'deploy' / 'site' / 'ts' / 'page-classes'
                        module_file = module_page_classes_dir / filename
                        if module_file.exists() and module_file.is_file():
                            relative_parts = ['..', '..', '..', '..', module.path, 'deploy', 'site', 'ts', 'page-classes', filename]
                            relative_path_str = '/'.join(relative_parts)
                            if relative_path_str not in page_class_files:
                                page_class_files.append(relative_path_str)
                                log(f"nginx_flask site js hook: Found page class file in module {module.name}: {relative_path_str}")
                                file_found = True
                                break

                if not file_found:
                    log(f"nginx_flask site js hook: Page class file not found (whitelisted but missing): {filename}")

            # Generate registry
            if page_class_files:
                registry_lines = []
                registry_lines.append("// Auto-generated during deployment - do not edit manually")
                registry_lines.append("")

                import_lines = []
                registry_entries = []

                for relative_path_str in sorted(page_class_files):
                    filename = os.path.basename(relative_path_str)
                    base_name = filename.replace('.js', '')
                    if base_name.endswith('-page-data'):
                        base_name = base_name[:-10]

                    class_name = kebab_to_snake(base_name) + '_page_data'
                    registry_key = kebab_to_snake(base_name)

                    if relative_path_str.startswith('ext/'):
                        import_path = f"../../../../{relative_path_str}"
                    else:
                        import_path = f"./{relative_path_str}"
                    import_lines.append(f"import {{ {class_name} }} from '{import_path}';")
                    registry_entries.append(f"  '{registry_key}': {class_name},")

                registry_lines.extend(import_lines)
                registry_lines.append("")
                registry_lines.append("export const PAGE_CLASS_REGISTRY = {")
                registry_lines.extend(registry_entries)
                registry_lines.append("};")

                registry_file = dest / 'site' / 'js' / 'hh' / 'deploy' / 'site' / 'ts' / 'page-classes-registry.js'
                registry_content = '\n'.join(registry_lines) + '\n'
                try:
                    registry_file.write_text(registry_content, encoding='utf-8')
                except Exception as e:
                    warn(f"nginx_flask site js hook: Failed to write page-classes-registry.js: {e}")
                    raise
                registry_deployed.append("js/hh/deploy/site/ts/page-classes-registry.js")
                log(f"nginx_flask site js hook: Generated page-classes-registry.js with {len(page_class_files)} page classes")
            else:
                log("nginx_flask site js hook: No page class files found in whitelist, skipping registry generation")

        except Exception as e:
            warn(f"nginx_flask site js hook: Failed to generate page-classes-registry.js: {e}")

        return {
            "status": "completed",
            "component": "site_js",
            "js_count": js_count,
            "js_files": js_deployed,
            "registry_files": registry_deployed
        }

    except Exception as e:
        warn(f"nginx_flask site js hook: Failed to deploy JS files: {e}")
        report_error("backend", f"nginx_flask site js hook: Failed to deploy JS files: {e}")
        return {"status": "error", "component": "site_js", "error": str(e)}


@register_module_hook('deploy_site')
def deploy_site_misc() -> Dict[str, Any]:
    """Deploy miscellaneous files to the site directory."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask site misc hook: Could not detect project name")
            return {"status": "error", "component": "site_misc", "error": "no_project"}

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        source = current_path
        dest = Path("/srv") / project_name
        site_dest = dest / 'site'

        # Get misc whitelist
        from hh.deploy.conf.misc_whitelist import MISC_WHITELIST

        misc_count = 0
        misc_deployed = []

        for misc_file in MISC_WHITELIST:
            source_misc = source / misc_file
            if source_misc.exists():
                if source_misc.is_dir():
                    # Deploy entire directory
                    dest_misc = site_dest / source_misc.name
                    if dest_misc.exists():
                        import shutil
                        shutil.rmtree(dest_misc)
                    shutil.copytree(source_misc, dest_misc)
                    misc_deployed.append(misc_file)
                    misc_count += 1
                    log(f"nginx_flask site misc hook: Deployed misc directory: {misc_file} -> site/{source_misc.name}")
                else:
                    # Deploy single file
                    dest_misc = site_dest / source_misc.name
                    if dest_misc.exists():
                        dest_misc.unlink()
                    import shutil
                    shutil.copy2(source_misc, dest_misc)
                    misc_deployed.append(misc_file)
                    misc_count += 1
                    log(f"nginx_flask site misc hook: Deployed misc file: {misc_file} -> site/{source_misc.name}")
            else:
                log(f"nginx_flask site misc hook: Misc file not found: {misc_file}")

        return {
            "status": "completed",
            "component": "site_misc",
            "count": misc_count,
            "files": misc_deployed
        }

    except Exception as e:
        warn(f"nginx_flask site misc hook: Failed to deploy misc files: {e}")
        report_error("backend", f"nginx_flask site misc hook: Failed to deploy misc files: {e}")
        return {"status": "error", "component": "site_misc", "error": str(e)}


@register_module_hook('deploy_nginx_and_ssl')
def deploy_nginx_and_ssl() -> Union[Dict[str, Any], bool]:
    """Deploy NGINX configuration and SSL certificates."""
    try:
        project_name, current_path = detect_project_context()
        if not project_name:
            warn("nginx_flask hook: Could not detect project name")
            return False

        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()

        # Get deployment parameters from install config
        from hh.deploy.users.install import _install_config_path
        import configparser
        cfg_path = _install_config_path(project_name)
        if not cfg_path.exists():
            warn(f"nginx_flask hook: Install config not found: {cfg_path}")
            return False

        parser = configparser.ConfigParser()
        parser.read(cfg_path)
        if "install" not in parser:
            warn(f"nginx_flask hook: Missing [install] section in {cfg_path}")
            return False

        sec = parser["install"]
        domain = sec.get("domain", "").strip()
        if not domain:
            warn("nginx_flask hook: No domain configured")
            return False

        ssl_enabled = sec.get("ssl_enabled", "").strip().lower() in ("true", "1", "yes")
        ssl_cert_dir_self_signed = Path("/etc/ssl/self-signed")
        ssl_cert_dir_letsencrypt = Path("/etc/letsencrypt/live")
        nginx_sites_available = Path("/etc/nginx/sites-available")
        nginx_sites_enabled = Path("/etc/nginx/sites-enabled")

        # Detect if local deployment
        is_local = (domain.startswith('192.168.') or
                    domain.startswith('10.') or
                    (domain.startswith('172.') and len(domain.split('.')) >= 2 and
                     domain.split('.')[1].isdigit() and 16 <= int(domain.split('.')[1]) <= 31))

        # Get local_allow_block if local
        local_allow_block = ""
        if is_local:
            local_allow_block = f"{'.'.join(domain.split('.')[:-1])}.0/24"

        from hh.deploy.http.deploy import (
            get_server_ip,
            create_nginx_ssl_config_local,
            create_nginx_config_local,
            install_nginx_ssl_config,
            install_nginx_config,
            create_local_decoy,
            check_nginx_status
        )

        nginx_deployed = False
        certificate_created = False
        server_ip = get_server_ip()
        log(f"nginx_flask hook: Detected server IP: {server_ip}")
        deployment_mode = "https" if ssl_enabled else "http"

        if ssl_enabled:
            log(f"nginx_flask hook: Starting HTTPS deployment for domain: {domain}")
            deployment_mode = "https" if not is_local else "https_local"

            # Check for certificate creation flags
            create_mode = None
            if gateway.get_arg('self_cert') or gateway.get_arg('self-cert'):
                create_mode = "self-cert"
            elif gateway.get_arg('get_cert') or gateway.get_arg('get-cert'):
                create_mode = "get-cert"
                if is_local:
                    warn("nginx_flask hook: Cannot obtain Let's Encrypt certificate for local domain")
                    report_error("action", "Cannot obtain Let's Encrypt certificate for local domain")
                    return False

            # Determine certificate path
            if create_mode == "self-cert":
                certificate_path = ssl_cert_dir_self_signed / domain
            elif create_mode == "get-cert":
                certificate_path = ssl_cert_dir_letsencrypt / domain
            else:
                # Try to detect existing certificate
                letsencrypt_path = ssl_cert_dir_letsencrypt / domain / "fullchain.pem"
                self_signed_path = ssl_cert_dir_self_signed / domain / "fullchain.pem"
                if letsencrypt_path.exists():
                    certificate_path = ssl_cert_dir_letsencrypt / domain
                    log(f"nginx_flask hook: Found existing Let's Encrypt certificate at {certificate_path}")
                elif self_signed_path.exists():
                    certificate_path = ssl_cert_dir_self_signed / domain
                    log(f"nginx_flask hook: Found existing self-signed certificate at {certificate_path}")
                else:
                    certificate_path = ssl_cert_dir_letsencrypt / domain
                    warn(f"nginx_flask hook: Certificate not found")
                    report_error("action", f"Certificate not found for domain {domain}")
                    return False

            cert_file_path = certificate_path / "fullchain.pem"

            # Create self-signed certificate if needed
            if create_mode == "self-cert":
                log("nginx_flask hook: Creating self-signed certificate...")
                from hh.deploy.deploy_utils import generate_self_signed_certificate, ensure_certificate_exists
                cert_name = domain.replace('.', '_')

                if generate_self_signed_certificate(certificate_path, cert_name, "root", "root"):
                    certificate_created = True
                    log(f"nginx_flask hook: Self-signed certificate generated at {certificate_path}")

                    if cert_file_path.exists():
                        if not ensure_certificate_exists(str(cert_file_path), "root", "root", None):
                            warn("nginx_flask hook: Certificate verification failed after creation")
                            report_error("action", "Certificate verification failed after creation")
                else:
                    warn("nginx_flask hook: Failed to generate self-signed certificate")
                    report_error("action", "Failed to generate self-signed certificate")
                    return False

            # Verify certificate exists
            if create_mode is None and not cert_file_path.exists():
                warn(f"nginx_flask hook: Certificate file not found at {cert_file_path}")
                report_error("action", f"Certificate file not found at {cert_file_path}")
                return False

            # Install NGINX SSL configuration
            log("nginx_flask hook: Installing NGINX SSL configuration...")

            if is_local:
                log(f"nginx_flask hook: Local deployment with access control: {local_allow_block}")
                config_content = create_nginx_ssl_config_local(domain, project_name, local_allow_block, server_ip, str(certificate_path))
                if not config_content:
                    warn("nginx_flask hook: Failed to generate local NGINX SSL configuration")
                    report_error("action", "Failed to generate local NGINX SSL configuration")
                else:
                    # Write config
                    config_file = nginx_sites_available / domain
                    config_file.write_text(config_content)
                    log(f"nginx_flask hook: Local NGINX SSL config written to: {config_file}")

                    # Symlink to sites-enabled
                    enabled_file = nginx_sites_enabled / domain
                    if enabled_file.exists():
                        enabled_file.unlink()
                    enabled_file.symlink_to(config_file)
                    log(f"nginx_flask hook: Symlink created: {enabled_file}")

                    # Test and reload NGINX
                    test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                    if test_result.returncode != 0:
                        warn(f"nginx_flask hook: Nginx configuration test failed: {test_result.stderr}")
                        report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
                    else:
                        log("nginx_flask hook: Nginx SSL configuration test passed")
                        reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                        if reload_result.returncode != 0:
                            restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                            if restart_result.returncode != 0:
                                warn(f"nginx_flask hook: Failed to reload/restart Nginx: {restart_result.stderr}")
                                report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
                            else:
                                log("nginx_flask hook: Nginx restarted successfully")
                                nginx_deployed = True
                        else:
                            log("nginx_flask hook: Nginx reloaded successfully")
                            nginx_deployed = True

                        # Create decoy server
                        if nginx_deployed:
                            if not create_local_decoy(server_ip, nginx_sites_available, nginx_sites_enabled):
                                warn("nginx_flask hook: Failed to create local decoy server")
            else:
                # Public deployment
                if install_nginx_ssl_config(domain, project_name, str(certificate_path), nginx_sites_available, nginx_sites_enabled):
                    nginx_deployed = True
                    log("nginx_flask hook: NGINX SSL configuration installed successfully")
                else:
                    warn("nginx_flask hook: NGINX SSL configuration installation failed")
                    report_error("action", "NGINX SSL configuration installation failed")

            # Get Let's Encrypt certificate if needed
            if not is_error() and create_mode == "get-cert":
                log("nginx_flask hook: Obtaining Let's Encrypt certificate...")
                from hh.deploy.deploy_utils import get_certificate_from_letsencrypt, ensure_certificate_exists
                if get_certificate_from_letsencrypt(domain, certificate_path):
                    certificate_created = True
                    log(f"nginx_flask hook: Let's Encrypt certificate obtained for {domain}")

                    if cert_file_path.exists():
                        if not ensure_certificate_exists(str(cert_file_path), "root", "root", None):
                            warn("nginx_flask hook: Certificate verification failed after creation")
                            report_error("action", "Certificate verification failed after creation")
                else:
                    warn("nginx_flask hook: Failed to obtain Let's Encrypt certificate")
                    report_error("action", "Failed to obtain Let's Encrypt certificate")

        else:
            # HTTP-only deployment
            log("nginx_flask hook: Installing NGINX HTTP-only configuration...")
            deployment_mode = "http" if not is_local else "http_local"

            if is_local:
                log(f"nginx_flask hook: Local deployment with access control: {local_allow_block}")
                config_content = create_nginx_config_local(domain, project_name, local_allow_block, server_ip)
                if not config_content:
                    warn("nginx_flask hook: Failed to generate local NGINX HTTP configuration")
                    report_error("action", "Failed to generate local NGINX HTTP configuration")
                else:
                    # Write config
                    config_file = nginx_sites_available / domain
                    config_file.write_text(config_content)
                    log(f"nginx_flask hook: Local NGINX HTTP config written to: {config_file}")

                    # Symlink to sites-enabled
                    enabled_file = nginx_sites_enabled / domain
                    if enabled_file.exists():
                        enabled_file.unlink()
                    enabled_file.symlink_to(config_file)
                    log(f"nginx_flask hook: Symlink created: {enabled_file}")

                    # Test and reload NGINX
                    test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                    if test_result.returncode != 0:
                        warn(f"nginx_flask hook: Nginx configuration test failed: {test_result.stderr}")
                        report_error("action", f"Nginx configuration test failed: {test_result.stderr}")
                    else:
                        log("nginx_flask hook: Nginx HTTP configuration test passed")
                        reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                        if reload_result.returncode != 0:
                            restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
                            if restart_result.returncode != 0:
                                warn(f"nginx_flask hook: Failed to reload/restart Nginx: {restart_result.stderr}")
                                report_error("action", f"Failed to reload/restart Nginx: {restart_result.stderr}")
                            else:
                                log("nginx_flask hook: Nginx restarted successfully")
                                nginx_deployed = True
                        else:
                            log("nginx_flask hook: Nginx reloaded successfully")
                            nginx_deployed = True

                        # Create decoy server
                        if nginx_deployed:
                            if not create_local_decoy(server_ip, nginx_sites_available, nginx_sites_enabled):
                                warn("nginx_flask hook: Failed to create local decoy server")
            else:
                # Public deployment
                if install_nginx_config(domain, project_name, nginx_sites_available, nginx_sites_enabled):
                    nginx_deployed = True
                    log("nginx_flask hook: NGINX HTTP configuration installed successfully")
                else:
                    warn("nginx_flask hook: NGINX HTTP configuration installation failed")
                    report_error("action", "NGINX HTTP configuration installation failed")

        # Get final NGINX status
        try:
            nginx_status = check_nginx_status()
            log(f"nginx_flask hook: NGINX status: active={nginx_status.get('is_active', False)}")
        except Exception:
            nginx_status = {'is_active': False, 'enabled_sites': []}

        return {
            "module": "nginx_flask",
            "action": "deploy_nginx_ssl",
            "nginx_deployed": nginx_deployed,
            "certificate_created": certificate_created,
            "certificate_path": str(certificate_path) if ssl_enabled and 'certificate_path' in locals() else None,
            "deployment_mode": deployment_mode,
            "nginx_active": nginx_status.get('is_active', False),
            "nginx_enabled_sites": nginx_status.get('enabled_sites', [])
        }
    except Exception as e:
        warn(f"nginx_flask hook: Failed to deploy NGINX/SSL: {e}")
        report_error("action", f"nginx_flask hook: Failed to deploy NGINX/SSL: {e}")
        return False

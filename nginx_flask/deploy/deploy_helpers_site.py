"""
Site deployment hooks for nginx_flask module.

These functions handle site directory setup and deployment of CSS, JS, and misc files.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
from hh.deploy.deploy_utils import detect_project_context, get_active_modules
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


@register_module_hook('deploy_site_prepare')
def prepare_site_directory() -> Dict[str, Any]:
    """Prepare the site directory by clearing and recreating it."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    dest = Path("/srv") / project_name
    site_dest = dest / 'site'

    # Clear existing site directory and recreate
    if site_dest.exists():
        shutil.rmtree(site_dest)
        log(f"nginx_flask site prepare: Cleared existing site directory: {site_dest}")
    site_dest.mkdir(parents=True, exist_ok=True)
    log(f"nginx_flask site prepare: Created fresh site directory: {site_dest}")

    return trace_out({
        "status": "completed",
        "component": "site_prepare",
        "directory": str(site_dest),
        "action": "cleared_and_created"
    })


@register_module_hook('deploy_site')
def deploy_site_css(pre_validated_whitelists: Dict[str, List[str]]) -> Dict[str, Any]:
    """Deploy CSS files to the site directory."""
    trace_in()

    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    source = current_path
    dest = Path("/srv") / project_name
    site_dest = dest / 'site'
    css_dest = site_dest / 'css'
    css_dest.mkdir(exist_ok=True)

    # Get CSS whitelist (pre-validated)
    CSS_WHITELIST = pre_validated_whitelists.get('CSS_WHITELIST', [])
    if not CSS_WHITELIST:
        raise ValueError("CSS_WHITELIST not pre-validated")

    css_count = 0
    css_deployed = []

    for css_file in CSS_WHITELIST:
        source_css = source / css_file
        if source_css.exists():
            dest_css = css_dest / source_css.name
            if dest_css.exists():
                dest_css.unlink()
            shutil.copy2(source_css, dest_css)
            css_deployed.append(f"css/{source_css.name}")
            css_count += 1
            log(f"nginx_flask site css: Deployed CSS file: {css_file} -> site/css/{source_css.name}")
        else:
            log(f"nginx_flask site css: CSS file not found: {css_file}")

    return trace_out({
        "status": "completed",
        "component": "site_css",
        "count": css_count,
        "files": css_deployed,
        "render_css_deployed": css_count,
        "render_css_files": css_deployed
    })


@register_module_hook('deploy_site')
def deploy_site_js(pre_validated_whitelists: Dict[str, List[str]]) -> Dict[str, Any]:
    """Deploy JavaScript files and generate registry."""
    trace_in()
    """Deploy JavaScript files and generate registry."""
    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    source = current_path
    dest = Path("/srv") / project_name
    site_dest = dest / 'site'
    js_dest = site_dest / 'js'
    js_dest.mkdir(exist_ok=True)

    # Get JS whitelists (pre-validated)
    JS_WHITELIST = pre_validated_whitelists.get('JS_WHITELIST', [])
    JS_PAGE_CLASSES_WHITELIST = pre_validated_whitelists.get('JS_PAGE_CLASSES_WHITELIST', [])
    if not JS_WHITELIST or not JS_PAGE_CLASSES_WHITELIST:
        raise ValueError("JS whitelists not pre-validated")

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
                    shutil.copy2(js_file, dest_js)
                    js_deployed.append(f"js/{relative_path.as_posix()}")
                    js_count += 1
                    log(f"nginx_flask site js: Deployed JS file from folder: {js_file} -> site/js/{relative_path.as_posix()}")
            else:
                # Deploy single JS file
                dest_js = js_dest / source_item.name
                if dest_js.exists():
                    dest_js.unlink()
                shutil.copy2(source_item, dest_js)
                js_deployed.append(f"js/{source_item.name}")
                js_count += 1
                log(f"nginx_flask site js: Deployed JS file: {js_item} -> site/js/{source_item.name}")
        else:
            log(f"nginx_flask site js: JS file/folder not found: {js_item}")

    # Generate page-classes-registry.js
    registry_deployed = []
    try:
        log("nginx_flask site js: Generating page-classes-registry.js")

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
            log("nginx_flask site js: Extension page-classes directory not found (this is normal if ext/ folder doesn't exist)")

        # Get active modules
        modules = get_active_modules()
        log(f"nginx_flask site js: Found {len(modules)} active modules for page-classes discovery")

        for filename in JS_PAGE_CLASSES_WHITELIST:
            file_found = False

            # Check hh/
            hh_file = hh_page_classes_dir / filename
            if hh_file.exists() and hh_file.is_file():
                relative_path = hh_file.relative_to(registry_file_dir)
                relative_path_str = str(relative_path).replace('\\', '/')
                if relative_path_str not in page_class_files:
                    page_class_files.append(relative_path_str)
                    log(f"nginx_flask site js: Found page class file in hh/: {relative_path_str}")
                    file_found = True

            # Check ext/
            if not file_found and ext_dir_exists:
                ext_file = ext_page_classes_dir / filename
                if ext_file.exists() and ext_file.is_file():
                    relative_path = ext_file.relative_to(registry_file_dir.parent.parent.parent.parent)
                    relative_path_str = str(relative_path).replace('\\', '/')
                    if relative_path_str not in page_class_files:
                        page_class_files.append(relative_path_str)
                        log(f"nginx_flask site js: Found page class file in ext/: {relative_path_str}")
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
                            log(f"nginx_flask site js: Found page class file in module {module.name}: {relative_path_str}")
                            file_found = True
                            break

            if not file_found:
                log(f"nginx_flask site js: Page class file not found (whitelisted but missing): {filename}")

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
            registry_file.write_text(registry_content, encoding='utf-8')
            registry_deployed.append("js/hh/deploy/site/ts/page-classes-registry.js")
            log(f"nginx_flask site js: Generated page-classes-registry.js with {len(page_class_files)} page classes")
        else:
            log("nginx_flask site js: No page class files found in whitelist, skipping registry generation")

    except Exception as e:
        warn(f"nginx_flask site js: Failed to generate page-classes-registry.js: {e}")

    return trace_out({
        "status": "completed",
        "component": "site_js",
        "js_count": js_count,
        "js_files": js_deployed,
        "registry_files": registry_deployed,
        "render_js_deployed": js_count,
        "render_js_files": js_deployed,
        "render_registry_generated": len(registry_deployed)
    })


@register_module_hook('deploy_site')
def deploy_site_misc(pre_validated_whitelists: Dict[str, List[str]]) -> Dict[str, Any]:
    """Deploy miscellaneous files to the site directory."""
    trace_in()
    """Deploy miscellaneous files to the site directory."""
    project_name, current_path = detect_project_context()
    if not project_name:
        raise ValueError("Could not detect project name")

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    source = current_path
    dest = Path("/srv") / project_name
    site_dest = dest / 'site'

    # Get misc whitelist (pre-validated)
    MISC_WHITELIST = pre_validated_whitelists.get('MISC_WHITELIST', [])
    if not MISC_WHITELIST:
        raise ValueError("MISC_WHITELIST not pre-validated")

    misc_count = 0
    misc_deployed = []

    for misc_file in MISC_WHITELIST:
        source_misc = source / misc_file
        if source_misc.exists():
            if source_misc.is_dir():
                # Deploy entire directory
                dest_misc = site_dest / source_misc.name
                if dest_misc.exists():
                    shutil.rmtree(dest_misc)
                shutil.copytree(source_misc, dest_misc)
                misc_deployed.append(misc_file)
                misc_count += 1
                log(f"nginx_flask site misc: Deployed misc directory: {misc_file} -> site/{source_misc.name}")
            else:
                # Deploy single file
                dest_misc = site_dest / source_misc.name
                if dest_misc.exists():
                    dest_misc.unlink()
                shutil.copy2(source_misc, dest_misc)
                misc_deployed.append(misc_file)
                misc_count += 1
                log(f"nginx_flask site misc: Deployed misc file: {misc_file} -> site/{source_misc.name}")
        else:
            log(f"nginx_flask site misc: Misc file not found: {misc_file}")

    return trace_out({
        "status": "completed",
        "component": "site_misc",
        "count": misc_count,
        "files": misc_deployed,
        "render_misc_deployed": misc_count,
        "render_misc_files": misc_deployed
    })

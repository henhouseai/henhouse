"""Nginx whitelist generation for static file serving."""
from pathlib import Path
from typing import Set, List, Dict
from hh.deploy.conf.js_whitelist import JS_WHITELIST
from hh.deploy.conf.css_whitelist import CSS_WHITELIST
from hh.deploy.conf.misc_whitelist import MISC_WHITELIST
from hh.deploy.conf.context_whitelist import CONTEXT_WHITELIST

def generate_nginx_static_locations(project_name: str) -> Dict:
    """Generate Nginx location blocks for static file serving based on whitelist configuration."""
    # Collect all directories that need static serving
    static_dirs = set()
    
    # From JS_WHITELIST: extract directories (all go to site/js/)
    if JS_WHITELIST:
        static_dirs.add('site/js/')
    
    # From CSS_WHITELIST: extract directories (all go to site/css/)
    if CSS_WHITELIST:
        static_dirs.add('site/css/')
    
    # From MISC_WHITELIST: extract directories/filenames
    # These are deployed to site/ top level
    for misc_item in MISC_WHITELIST:
        if '/css/' in misc_item:
            static_dirs.add('site/css/')
        elif '/js/' in misc_item:
            static_dirs.add('site/js/')
        else:
            # Top level in site/
            static_dirs.add('site/')
    
    # From CONTEXT_WHITELIST: these folders are deployed to root
    for context_folder in CONTEXT_WHITELIST:
        static_dirs.add(f'{context_folder}/')
    
    # Generate location blocks
    config = _generate_location_blocks(static_dirs, project_name)
    
    # Track summary counts
    summary = {
        'js_files': len(JS_WHITELIST),
        'css_files': len(CSS_WHITELIST),
        'misc_files': len(MISC_WHITELIST),
        'context_folders': len(CONTEXT_WHITELIST),
        'always_static': 1  # images directory
    }
    
    return {
        'config': config,
        'summary': summary
    }

def _generate_location_blocks(static_dirs: Set[str], project_name: str) -> str:
    """Generate location blocks from set of static directories."""
    blocks = []
    
    # Always include images directory (from Architecture docs)
    blocks.append(f"""    location /srv/images/ {{
        alias /srv/images/{project_name}/;
        expires off;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }}""")
    
    # Generate location blocks for each static directory
    for static_dir in sorted(static_dirs):
        # Remove trailing slash for cleaner paths
        dir_clean = static_dir.rstrip('/')
        
        # Determine the alias path
        if dir_clean.startswith('site'):
            alias_path = f'/srv/{project_name}/{dir_clean}/'
        else:
            alias_path = f'/srv/{project_name}/{dir_clean}/'
        
        blocks.append(f"""    location /{dir_clean}/ {{
        alias {alias_path};
        expires off;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }}""")
    
    return '\n\n'.join(blocks)

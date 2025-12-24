"""
Response class for HTTP backend output.
Wraps output buffer content in full HTML document shell.
"""
from __future__ import annotations
from typing import List, Optional
import json
import os
from hh.gateway.response.response import Response
from hh.deploy.deploy_utils import (
    load_whitelist_with_extensions,
    load_dict_whitelist_with_extensions,
)
from hh.render.config.config import safe_str
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
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

class ResponseHTTP(Response):
    """
    HTTP backend response handler.
    Wraps output buffer in full HTML document with head, CSS links, and body.
    Uses header metadata for HTML title generation.
    Dynamically generates CSS and JS includes from whitelists.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._site_link_groups: dict[str, List[tuple[int, str]]] = {}
        self._application_action_groups: dict[str, List[tuple[str, str]]] = {}
        self._prepared_title: str = ""
        self._prepared_css_section: str = ""
        self._prepared_js_section: str = ""
        self._prepared_seed_script: str = ""
    
    def _prepare_output(self) -> None:
        """Prepare HTTP output by populating menu content and building HTML sections."""
        trace_in()
        log("Preparing HTTP output")
        
        self._populate_menu_content()
        
        debug("Generating page title")
        title = self.title
        try:
            seed_title = None
            if self.seed_data and isinstance(self.seed_data, dict):
                page_obj = self.seed_data.get('page') if isinstance(self.seed_data.get('page'), dict) else None
                if page_obj and page_obj.get('title'):
                    seed_title = page_obj.get('title')
            if seed_title:
                title = seed_title
                debug(f"Using seed title: {title}")
            else:
                debug(f"Using default title: {title}")
        except Exception as e:
            warn(f"Error generating title: {e}")
        self._prepared_title = title
        log(f"Prepared title: {title}")
        
        debug("Building CSS links")
        tier_level = self.user_tier_level
        tier_css_map = {
            1: 'site-guest.css',
            2: 'site-verified.css',
            3: 'site-admin.css',
            4: 'site-root.css',
        }
        tier_css = tier_css_map.get(tier_level, 'site-guest.css')
        debug(f"Tier level: {tier_level}, CSS: {tier_css}")
        css_links = [f'    <link rel="stylesheet" href="/site/css/{tier_css}">']
        
        debug("Loading CSS whitelist")
        CSS_ALWAYS_INCLUDE = load_whitelist_with_extensions('css_whitelist', 'CSS_ALWAYS_INCLUDE')
        debug(f"CSS whitelist loaded: {len(CSS_ALWAYS_INCLUDE)} items")
        for css_path in CSS_ALWAYS_INCLUDE:
            filename = os.path.basename(css_path)
            css_links.append(f'    <link rel="stylesheet" href="/site/css/{filename}">')
            debug(f"Added CSS link: {filename}")
        
        for css_path in self.header_css_links:
            css_links.append(f'    <link rel="stylesheet" href="{css_path}">')
            debug(f"Added custom CSS link: {css_path}")
        
        self._prepared_css_section = "\n".join(css_links) if css_links else ""
        log(f"Prepared CSS section: {len(css_links)} links")
        
        debug("Building JS scripts")
        debug("Loading JS whitelist")
        JS_ALWAYS_INCLUDE = load_whitelist_with_extensions('js_whitelist', 'JS_ALWAYS_INCLUDE')
        debug(f"JS whitelist loaded: {len(JS_ALWAYS_INCLUDE)} items")
        js_scripts = []
        for js_path in JS_ALWAYS_INCLUDE:
            if js_path.startswith('hh/deploy/site/js/'):
                site_path = js_path.replace('hh/deploy/site/js/', '/site/js/', 1)
            else:
                site_path = f'/site/js/{os.path.basename(js_path)}'
            js_scripts.append(f'    <script type="module" src="{site_path}"></script>')
            debug(f"Added JS script: {site_path}")
        
        for js_path in self.header_js_links:
            js_scripts.append(f'    <script src="{js_path}"></script>')
            debug(f"Added custom JS link: {js_path}")
        
        self._prepared_js_section = "\n".join(js_scripts) if js_scripts else ""
        log(f"Prepared JS section: {len(js_scripts)} scripts")
        
        debug("Building seed data JSON")
        seed = self.seed_data or {}
        seed_json = json.dumps(seed)
        self._prepared_seed_script = f'    <script type="application/json" id="hh-seed-data">{seed_json}</script>'
        debug(f"Prepared seed script: {len(seed_json)} characters")
        log("HTTP output preparation complete")
        trace_out()
    
    def get_output(self) -> str:
        """Return HTTP output - wraps body content in full HTML document."""
        
        # Build body content from multiple sources
        body_parts = []
        
        # Add error output if present
        if self.error_output and "rendered" in self.error_output:
            body_parts.append(self.error_output["rendered"])
        
        # Get body content from output buffer
        if self.output_buffer:
            body_parts.append("\n".join(self.output_buffer))
        
        # Add debug output if present
        if self.debug_output:
            if isinstance(self.debug_output, dict):
                if "text" in self.debug_output:
                    # HTTP/Parser debug format (text)
                    body_parts.append(self.debug_output["text"])
                elif "entries" in self.debug_output:
                    # MCP debug format (JSON entries) - convert to text for display
                    debug_text = json.dumps(self.debug_output, indent=2)
                    body_parts.append(f"<pre>{debug_text}</pre>")
            elif isinstance(self.debug_output, str):
                body_parts.append(self.debug_output)
        
        body_content = "\n".join(body_parts)

        # Build body structure inline
        legacy_body = self._render_body(title=self._prepared_title, body_content=body_content)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover">
    <title>{self._prepared_title}</title>
{self._prepared_css_section}
{self._prepared_seed_script}
{self._prepared_js_section}
</head>
<body>
{legacy_body}
</body>
</html>"""
        
        return html

    # ---- Internal layout helpers (no external deps) ----

    def _render_header(self, path_html: str, title: str) -> str:
        display = path_html if path_html else title
        return f"<div id=\"header\">{display}</div>"

    def _render_menu(self, *, admin: bool, user_info_html: str, site_links_html: str, application_action_links_html: str, user_action_links_html: str) -> str:
        parts: List[str] = []
        if admin:
            if user_info_html:
                parts.append(user_info_html)
            if site_links_html:
                parts.append(site_links_html)
            if application_action_links_html:
                parts.append(application_action_links_html)
        else:
            if user_action_links_html:
                parts.append(user_action_links_html)
            if site_links_html:
                parts.append(site_links_html)
        inner = "\n".join(parts)
        return "<div id=\"menu\">\n" + inner + "\n</div>"

    def _render_content_wrapper_header(self, title: str) -> str:
        # Use custom header content if set, otherwise use title
        header_content = self.content_wrapper_header if self.content_wrapper_header else title
        return f"<div class=\"contentWrapperHeader\">{header_content}</div>"

    def _render_content_wrapper(self, content_divs: List[str], content_wrapper_class: str) -> str:
        class_attr = (
            f"contentWrapper {content_wrapper_class}".strip()
            if content_wrapper_class
            else "contentWrapper"
        )
        inner = "\n".join(content_divs)
        return f"<div class=\"{class_attr}\">\n{inner}\n</div>"

    def _render_content_holder(self, title: str, content_wrapper_html: str) -> str:
        return (
            "<div id=\"contentHolder\">\n"
            + self._render_content_wrapper_header(title)
            + "\n"
            + content_wrapper_html
            + "\n</div>"
        )

    def _render_footer(self) -> str:
        return "<div id=\"footer\"></div>"

    def _render_wrapper(self, *, header_html: str, menu_html: str, content_holder_html: str, footer_html: str) -> str:
        return (
            "<div id=\"wrapper\">\n"
            + header_html
            + "\n"
            + menu_html
            + "\n"
            + content_holder_html
            + "\n"
            + footer_html
            + "\n</div>"
        )

    def _render_body(self, *, title: str, body_content: str) -> str:
        path_html = self.path or ""
        admin = bool(self.admin)
        # Render menu content from collected data
        user_info_html = self._render_user_info()
        site_links_html = self._render_site_links()
        application_action_links_html = self._render_application_action_links()
        user_action_links_html = self.user_action_links_html or ""
        content_wrapper_class = self.content_wrapper_class or ""

        header_html = self._render_header(path_html, title)
        menu_html = self._render_menu(
            admin=admin,
            user_info_html=user_info_html,
            site_links_html=site_links_html,
            application_action_links_html=application_action_links_html,
            user_action_links_html=user_action_links_html,
        )
        
        # Build content divs in order: upper_content, page_text, lower_content, child_pages, image_group, file_group, then backend response
        content_divs = []
        if self.upper_content:
            upper_content_html = "\n".join(self.upper_content)
            if upper_content_html:
                content_divs.append(upper_content_html)
        if self.page_text:
            # Get page_id from seed_data for ID attribute
            page_id = None
            try:
                if self.seed_data and isinstance(self.seed_data, dict):
                    page_obj = self.seed_data.get('page') if isinstance(self.seed_data.get('page'), dict) else None
                    if page_obj and page_obj.get('id'):
                        page_id = str(page_obj.get('id'))
            except Exception:
                pass
            id_attr = f' id="page-text-{page_id}"' if page_id else ''
            wrapped_text = f'<div class="content pageText"{id_attr}>{safe_str(self.page_text)}</div>'
            content_divs.append(wrapped_text)
        if self.lower_content:
            lower_content_html = "\n".join(self.lower_content)
            if lower_content_html:
                content_divs.append(lower_content_html)
        if self.child_pages:
            child_pages_html = "\n".join(self.child_pages)
            if child_pages_html:
                content_divs.append(child_pages_html)
        # Get page_id from seed_data for header generation
        page_id = None
        try:
            if self.seed_data and isinstance(self.seed_data, dict):
                page_obj = self.seed_data.get('page') if isinstance(self.seed_data.get('page'), dict) else None
                if page_obj and page_obj.get('id'):
                    page_id = str(page_obj.get('id'))
        except Exception:
            pass
        
        # Add media groups with automatic headers for HTTP backend
        if self.image_group and page_id:
            header_id = f"pageImageGroupHeader_{page_id}"
            image_header_html = f'<div id="{header_id}" class="contentHeader">\n  <a class="updatePageView_{page_id}" data-section="images">IMAGES</a>\n</div>'
            content_divs.append(image_header_html + self.image_group)
        elif self.image_group:
            content_divs.append(self.image_group)
        
        if self.file_group and page_id:
            header_id = f"fileGroupHeader_{page_id}"
            file_header_html = f'<div id="{header_id}" class="contentHeader">\n  <a class="updatePageView_{page_id}" data-section="files">FILES</a>\n</div>'
            content_divs.append(file_header_html + self.file_group)
        elif self.file_group:
            content_divs.append(self.file_group)
        
        if self.audio_group and page_id:
            header_id = f"audioGroupHeader_{page_id}"
            audio_header_html = f'<div id="{header_id}" class="contentHeader">\n  <a class="updatePageView_{page_id}" data-section="audio">AUDIO</a>\n</div>'
            content_divs.append(audio_header_html + self.audio_group)
        elif self.audio_group:
            content_divs.append(self.audio_group)
        
        if self.video_group and page_id:
            header_id = f"videoGroupHeader_{page_id}"
            video_header_html = f'<div id="{header_id}" class="contentHeader">\n  <a class="updatePageView_{page_id}" data-section="video">VIDEO</a>\n</div>'
            content_divs.append(video_header_html + self.video_group)
        elif self.video_group:
            content_divs.append(self.video_group)
        if body_content:
            content_divs.append(body_content)
        
        content_wrapper_html = self._render_content_wrapper(content_divs, content_wrapper_class)
        content_holder_html = self._render_content_holder(title, content_wrapper_html)
        footer_html = self._render_footer()
        return self._render_wrapper(
            header_html=header_html,
            menu_html=menu_html,
            content_holder_html=content_holder_html,
            footer_html=footer_html,
        )
    
    # ---- Menu content population ----
    
    def _populate_menu_content(self) -> None:
        """Populate menu content (site links, app actions, user info) based on tier level."""
        # Always populate site links
        try:
            debug("Loading site links whitelist")
            SITE_LINKS = load_dict_whitelist_with_extensions('site_links', 'SITE_LINKS')
            log(f"Site links loaded: {len(SITE_LINKS)} groups")
            debug(f"Site links data: {SITE_LINKS}")
            for idx, group_data in enumerate(SITE_LINKS):
                debug(f"Processing site link group {idx}: {group_data}")
                group_name = group_data.get('group')
                header_page_id = group_data.get('header_page_id')
                header_text = group_data.get('header_text')
                links = group_data.get('links', [])
                
                debug(f"Group name: {group_name}, header_page_id: {header_page_id}, header_text: {header_text}, links count: {len(links)}")
                
                if group_name and header_page_id is not None and header_text:
                    debug(f"Adding site link group: {group_name}")
                    self.add_site_link_group(group_name, header_page_id, header_text)
                    for link_idx, link in enumerate(links):
                        page_id = link.get('page_id')
                        text = link.get('text')
                        debug(f"Processing link {link_idx}: page_id={page_id}, text={text}")
                        if page_id is not None and text:
                            debug(f"Adding site link: {group_name} -> page_id={page_id}, text={text}")
                            self.add_site_link(group_name, page_id, text)
                        else:
                            warn(f"Skipping invalid link in group {group_name}: page_id={page_id}, text={text}")
                else:
                    warn(f"Skipping invalid site link group: group_name={group_name}, header_page_id={header_page_id}, header_text={header_text}")
            log(f"Site links populated: {len(self._site_link_groups)} groups")
        except Exception as e:
            warn(f"Failed to populate site links: {e}")
            import traceback
            debug(f"Site links exception traceback: {traceback.format_exc()}")
        
        # Only populate app actions and user info for tier > 1 (verified, admin, root)
        if self.user_tier_level > 1:
            # Set admin flag for menu rendering
            self.admin = True
            
            # Populate application action links (persistent from conf file)
            try:
                debug("Loading application actions whitelist")
                APPLICATION_ACTIONS = load_dict_whitelist_with_extensions('application_actions', 'APPLICATION_ACTIONS')
                log(f"Application actions loaded: {len(APPLICATION_ACTIONS)} groups")
                for group_data in APPLICATION_ACTIONS:
                    group_name = group_data.get('group')
                    group_label = group_data.get('group_label')
                    actions = group_data.get('actions', [])
                    
                    if group_name and group_label:
                        self.add_application_action_group(group_name, group_label)
                        for action in actions:
                            action_id = action.get('action_id')
                            label = action.get('label')
                            if action_id and label:
                                self.add_application_action_link(group_name, action_id, label)
            except Exception as e:
                warn(f"Failed to populate application actions: {e}")
                import traceback
                debug(f"Application actions exception traceback: {traceback.format_exc()}")
            
            # Populate hot-cache app actions (dynamic from MCP whitelist)
            try:
                from hh.gateway.registry.mcp_whitelist import MCPWhitelist
                app_actions = MCPWhitelist.get_app_actions(self.user_tier_level)
                if app_actions:
                    if not hasattr(self, '_hot_cache_action_ids'):
                        self._hot_cache_action_ids = set()
                    for action in app_actions:
                        group_name = action.get('group', 'default')
                        action_id = action.get('id', action.get('tool_name', ''))
                        label = action.get('label', action.get('tool_name', ''))
                        # Track hot-cache action IDs
                        self._hot_cache_action_ids.add(action_id)
                        # Add to menu groups (duplicate check happens in add_application_action_link)
                        if group_name not in self._application_action_groups:
                            # Group doesn't exist, create it with human-readable header
                            header_text = group_name.replace('_', ' ').upper()
                            self.add_application_action_group(group_name, header_text)
                        self.add_application_action_link(group_name, action_id, label)
            except Exception as e:
                warn(f"Failed to populate hot-cache app actions: {e}")
            
            # Populate user info
            # Get username from seed_data if available, otherwise use default
            try:
                seed_data = self.get_seed_data()
                username = "user"  # Default
                if seed_data and isinstance(seed_data, dict):
                    # Could get from page context or other seed data
                    # For now, use default
                    username = "user"
                self.set_user_info(username)
            except Exception:
                pass
    
    # ---- Menu content builders ----
    
    def add_site_link_group(self, group_name: str, page_id: int, link_text: str) -> None:
        """Create a new site link group with header link."""
        # First link in group is the header
        self._site_link_groups[group_name] = [(page_id, link_text)]
    
    def add_site_link(self, group_name: str, page_id: int, link_text: str) -> None:
        """Add a site link to an existing group."""
        if group_name not in self._site_link_groups:
            # Group doesn't exist, create it (first link becomes header)
            self._site_link_groups[group_name] = [(page_id, link_text)]
        else:
            # Add to existing group
            self._site_link_groups[group_name].append((page_id, link_text))
    
    def add_application_action_group(self, group_name: str, header_text: str) -> None:
        """Create a new application action group with header text."""
        # First item in group is header (empty action_id marks it as header)
        self._application_action_groups[group_name] = [('', header_text)]
    
    def add_application_action_link(self, group_name: str, action_id: str, label: str) -> None:
        """Add an application action link to an existing group."""
        if group_name not in self._application_action_groups:
            # Group doesn't exist, create it (first item becomes header with empty action_id)
            self._application_action_groups[group_name] = [('', group_name)]
        # Check for duplicates before adding (skip empty action_ids which are headers)
        existing_action_ids = {aid for aid, _ in self._application_action_groups[group_name] if aid}
        if action_id and action_id not in existing_action_ids:
            # Add to existing group
            self._application_action_groups[group_name].append((action_id, label))
    
    def set_user_info(self, username: str) -> None:
        """Set user info for display."""
        self._user_info_username = username
    
    def _render_site_links(self) -> str:
        """Render site links HTML with grouping."""
        if not hasattr(self, '_site_link_groups') or not self._site_link_groups:
            return ""
        
        html_parts: List[str] = []
        for group_name, links in self._site_link_groups.items():
            if not links:
                continue
            html_parts.append('<ul class="siteLinks menuGroup">')
            # First link is header
            header_page_id, header_text = links[0]
            html_parts.append(f'    <li class="header"><a href="/{header_page_id}">{header_text}</a></li>')
            # Remaining links are regular items
            for page_id, link_text in links[1:]:
                html_parts.append(f'    <li><a href="/{page_id}">{link_text}</a></li>')
            html_parts.append('</ul>')
        
        return "\n".join(html_parts)
    
    def _render_application_action_links(self) -> str:
        """Render application action links HTML with grouping."""
        if not hasattr(self, '_application_action_groups') or not self._application_action_groups:
            return ""
        
        html_parts: List[str] = []
        for group_name, actions in self._application_action_groups.items():
            if not actions:
                continue
            html_parts.append(f'<ul class="applicationActions menuGroup" data-group="{group_name}">')
            # First item is header (empty action_id marks it as header)
            header_action_id, header_text = actions[0]
            html_parts.append(f'    <li class="header">{header_text}</li>')
            # Remaining items are action links (with IDs, no hrefs)
            for action_id, label in actions[1:]:
                # Mark hot-cache actions with data-source attribute
                hot_cache_attr = ''
                if hasattr(self, '_hot_cache_action_ids') and action_id in self._hot_cache_action_ids:
                    hot_cache_attr = ' data-source="hot_cache"'
                html_parts.append(f'    <li><a id="{action_id}"{hot_cache_attr}>{label}</a></li>')
            html_parts.append('</ul>')
        
        return "\n".join(html_parts)
    
    def _render_user_info(self) -> str:
        """Render user info HTML."""
        if not hasattr(self, '_user_info_username'):
            return ""
        
        username = self._user_info_username
        return (
            '<ul class="userInfo menuGroup">\n'
            '    <li class="header">LOGIN</li>\n'
            f'    <li>"{username}"</li>\n'
            '    <li>Quit browser to logout</li>\n'
            '</ul>'
        )


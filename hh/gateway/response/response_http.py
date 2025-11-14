"""
Response class for HTTP backend output.
Wraps output buffer content in full HTML document shell.
"""
from __future__ import annotations
from typing import List, Optional
import json
import os
from hh.gateway.response.response import Response
from hh.deploy.conf.css_whitelist import CSS_ALWAYS_INCLUDE
from hh.deploy.conf.js_whitelist import JS_ALWAYS_INCLUDE
from hh.render.config.config import safe_str

class ResponseHTTP(Response):
    """
    HTTP backend response handler.
    Wraps output buffer in full HTML document with head, CSS links, and body.
    Uses header metadata for HTML title generation.
    Dynamically generates CSS and JS includes from whitelists.
    """
    
    def get_output(self) -> str:
        """Return HTTP output - wraps body content in full HTML document."""
        # Populate menu content based on tier level
        self._populate_menu_content()
        
        # Get body content from output buffer
        body_content = "\n".join(self.output_buffer) if self.output_buffer else ""
        
        # Generate page title: start with explicit field default, override from seeds if present
        title = self.title  # Default set by base class
        try:
            seed_title = None
            if self.seed_data and isinstance(self.seed_data, dict):
                page_obj = self.seed_data.get('page') if isinstance(self.seed_data.get('page'), dict) else None
                if page_obj and page_obj.get('title'):
                    seed_title = page_obj.get('title')
            if seed_title:
                title = seed_title
        except Exception:
            pass
        
        # Add tier-specific color theme CSS FIRST (before component CSS that references these variables)
        tier_level = self.user_tier_level
        tier_css_map = {
            1: 'site-guest.css',    # guest
            2: 'site-verified.css', # verified
            3: 'site-admin.css',    # admin
            4: 'site-root.css',     # root
        }
        tier_css = tier_css_map.get(tier_level, 'site-guest.css')  # Default to guest for unknown (0)
        css_links = [f'    <link rel="stylesheet" href="/site/css/{tier_css}">']
        
        # Always-include CSS files (site.css, ansi-colors.css, tables.css, etc.)
        # These come after tier CSS so they can reference the color variables
        for css_path in CSS_ALWAYS_INCLUDE:
            # Extract filename from path like 'hh/gateway/deploy/site/css/site.css'
            filename = os.path.basename(css_path)
            css_links.append(f'    <link rel="stylesheet" href="/site/css/{filename}">')
        
        # Add custom CSS links (added by decorators/modules via gateway.add_css_link())
        for css_path in self.header_css_links:
            css_links.append(f'    <link rel="stylesheet" href="{css_path}">')
        
        # Always-include JS files (site.js)
        # TypeScript compiled files are ES6 modules, legacy files are regular scripts
        module_files = {'seed.js', 'rpc-client.js', 'app.js'}
        js_scripts = []
        for js_path in JS_ALWAYS_INCLUDE:
            # Extract filename from path like 'hh/gateway/deploy/site/js/site.js'
            filename = os.path.basename(js_path)
            if filename in module_files:
                js_scripts.append(f'    <script type="module" src="/site/js/{filename}"></script>')
            else:
                js_scripts.append(f'    <script src="/site/js/{filename}"></script>')
        
        # Add custom JS links (added by decorators/modules via gateway.add_js_link())
        for js_path in self.header_js_links:
            js_scripts.append(f'    <script src="{js_path}"></script>')
        
        # Build seed data as JSON script tag for TypeScript client
        seed = self.seed_data or {}
        seed_json = json.dumps(seed)
        seed_script = f'    <script type="application/json" id="hh-seed-data">{seed_json}</script>'

        # Build full HTML document
        css_section = "\n".join(css_links) if css_links else ""
        js_section = "\n".join(js_scripts) if js_scripts else ""

        # Build body structure inline
        legacy_body = self._render_body(title=title, body_content=body_content)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
{css_section}
{seed_script}
{js_section}
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
        
        # Build content divs in order: upper_content, page_text, lower_content, then backend response
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
            from hh.deploy.conf.site_links import populate_site_links
            populate_site_links()
        except Exception:
            pass  # If site_links.py doesn't exist or fails, continue
        
        # Only populate app actions and user info for tier > 1 (verified, admin, root)
        if self.user_tier_level > 1:
            # Set admin flag for menu rendering
            self.admin = True
            
            # Populate application action links (persistent from conf file)
            try:
                from hh.deploy.conf.application_actions import populate_application_action_links
                populate_application_action_links()
            except Exception:
                pass
            
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
                # Log error but don't fail
                from hh.gateway.registry.debug import get_warn
                warn = get_warn(True)
                warn(f"Failed to populate hot-cache app actions: {e}")
            
            # Populate user info
            try:
                from hh.deploy.conf.user_info import populate_user_info
                populate_user_info()
            except Exception:
                pass
    
    # ---- Menu content builders ----
    
    def add_site_link_group(self, group_name: str, page_id: int, link_text: str) -> None:
        """Create a new site link group with header link."""
        if not hasattr(self, '_site_link_groups'):
            self._site_link_groups: dict[str, List[tuple[int, str]]] = {}
        # First link in group is the header
        self._site_link_groups[group_name] = [(page_id, link_text)]
    
    def add_site_link(self, group_name: str, page_id: int, link_text: str) -> None:
        """Add a site link to an existing group."""
        if not hasattr(self, '_site_link_groups'):
            self._site_link_groups: dict[str, List[tuple[int, str]]] = {}
        if group_name not in self._site_link_groups:
            # Group doesn't exist, create it (first link becomes header)
            self._site_link_groups[group_name] = [(page_id, link_text)]
        else:
            # Add to existing group
            self._site_link_groups[group_name].append((page_id, link_text))
    
    def add_application_action_group(self, group_name: str, header_text: str) -> None:
        """Create a new application action group with header text."""
        if not hasattr(self, '_application_action_groups'):
            self._application_action_groups: dict[str, List[tuple[str, str]]] = {}
        # First item in group is header (empty action_id marks it as header)
        self._application_action_groups[group_name] = [('', header_text)]
    
    def add_application_action_link(self, group_name: str, action_id: str, label: str) -> None:
        """Add an application action link to an existing group."""
        if not hasattr(self, '_application_action_groups'):
            self._application_action_groups: dict[str, List[tuple[str, str]]] = {}
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
            html_parts.append(f'    <li class="header"><a href="/show-page?id={header_page_id}">{header_text}</a></li>')
            # Remaining links are regular items
            for page_id, link_text in links[1:]:
                html_parts.append(f'    <li><a href="/show-page?id={page_id}">{link_text}</a></li>')
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


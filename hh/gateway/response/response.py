from __future__ import annotations
import os
from typing import List, Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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

class Response:
    def __init__(self):
        trace_in()
        self.output_buffer: List[str] = []
        self.action_response: Optional[dict] = None
        # Error and debug output storage (set by error handlers and flush_debug)
        self.error_output: Optional[dict] = None
        self.debug_output: Optional[dict] = None
        # header_metadata removed; seeds are used instead
        # Arbitrary client seed payload (emitted to HTML/clients by backends)
        self.seed_data: Optional[dict] = None
        # Custom header CSS and JS links (added by decorators/modules)
        self.header_css_links: List[str] = []
        self.header_js_links: List[str] = []
        # Explicit fields for HTML layout (legacy-structure compatibility)
        self.title: str = "Henhouse"
        self.path: str = ""
        self.page_text: str = ""
        self.upper_content: List[str] = []
        self.lower_content: List[str] = []
        self.admin: bool = False
        self.user_info_html: str = ""
        self.site_links_html: str = ""
        self.application_action_links_html: str = ""
        self.user_action_links_html: str = ""
        self.content_wrapper_class: str = ""
        self.content_wrapper_header: str = ""
        # User tier level (0 = unknown, 1 = guest, 2 = verified, 3 = admin, 4 = root)
        # Check USER_TIER environment variable (set by Flask for MCP requests)
        user_tier = os.getenv('USER_TIER')
        if user_tier and user_tier in HENHOUSE_TIERS:
            try:
                tier_index = HENHOUSE_TIERS.index(user_tier)
                # Convert 0-based index to 1-based level (index 0 → level 1, etc.)
                self.user_tier_level = tier_index + 1
                log(f"Detected user tier from USER_TIER env: {user_tier} (level {self.user_tier_level})")
            except ValueError:
                self.user_tier_level = 0
                log(f"USER_TIER env var '{user_tier}' not found in HENHOUSE_TIERS")
        else:
            self.user_tier_level = 0
        log("Response initialized with empty buffer")
        trace_out()
    
    # Header metadata helpers removed; use seed_data instead
    
    def add_output(self, text: str) -> None:
        trace_in()
        if text:
            self.output_buffer.append(text)
            if len(text) > 1000:
                # Find next newline after 1000 chars, or show full text if none found
                newline_pos = text.find('\n', 1000)
                if newline_pos != -1:
                    log(f"Added output: {text[:newline_pos]}\n...")
                else:
                    log(f"Added output: {text}")
            else:
                log(f"Added output: {text}")
        trace_out()

    # ---- Seed data helpers ----

    def set_seed_data(self, seed: dict) -> None:
        """Replace seed_data with provided dict."""
        trace_in()
        if not isinstance(seed, dict):
            warn("set_seed_data called with non-dict argument")
            trace_out()
            return
        self.seed_data = dict(seed)
        log(f"Set seed data: keys={list(self.seed_data.keys())}")
        trace_out()

    def add_seed_data(self, seed: dict) -> None:
        """Merge provided dict into existing seed_data (create if missing)."""
        trace_in()
        if not isinstance(seed, dict):
            warn("add_seed_data called with non-dict argument")
            trace_out()
            return
        if self.seed_data:
            self.seed_data.update(seed)
            log(f"Merged seed data: keys={list(seed.keys())}")
        else:
            self.set_seed_data(seed)
        trace_out()

    def get_seed_data(self) -> Optional[dict]:
        """Return current seed data (or None)."""
        return self.seed_data
    
    # ---- Header CSS/JS link helpers ----
    
    def add_css_link(self, css_path: str) -> None:
        """Add a CSS link to the header."""
        trace_in()
        if not isinstance(css_path, str) or not css_path:
            warn("add_css_link called with invalid argument")
            trace_out()
            return
        if css_path not in self.header_css_links:
            self.header_css_links.append(css_path)
            log(f"Added CSS link: {css_path}")
        trace_out()
    
    def add_js_link(self, js_path: str) -> None:
        """Add a JS script link to the header."""
        trace_in()
        if not isinstance(js_path, str) or not js_path:
            warn("add_js_link called with invalid argument")
            trace_out()
            return
        if js_path not in self.header_js_links:
            self.header_js_links.append(js_path)
            log(f"Added JS link: {js_path}")
        trace_out()
    
    def get_css_links(self) -> List[str]:
        """Return list of custom CSS links."""
        return self.header_css_links.copy()
    
    def get_js_links(self) -> List[str]:
        """Return list of custom JS links."""
        return self.header_js_links.copy()
    
    # ---- Content setters ----
    
    def set_content_wrapper_header(self, header: str) -> None:
        """Set the content wrapper header content."""
        trace_in()
        self.content_wrapper_header = header
        log(f"Set content wrapper header: {len(header)} characters")
        trace_out()
    
    def set_path(self, path: str) -> None:
        """Set the path HTML content."""
        trace_in()
        self.path = path
        log(f"Set path: {len(path)} characters")
        trace_out()
    
    def set_page_text(self, page_text: str) -> None:
        """Set the page text HTML content."""
        trace_in()
        self.page_text = page_text
        log(f"Set page text: {len(page_text)} characters")
        trace_out()
    
    def set_upper_content(self, content: str) -> None:
        """Add content to the upper content section."""
        trace_in()
        # Filter out empty content - only add if content has non-whitespace or is exactly "\n"
        if content and (content.strip() or content == "\n"):
            # Convert "\n" to empty string, otherwise use content as-is
            processed_content = "" if content == "\n" else content
            self.upper_content.append(processed_content)
            log(f"Added upper content: {len(processed_content)} characters")
        else:
            log("Skipped empty upper content")
        trace_out()
    
    def set_lower_content(self, content: str) -> None:
        """Add content to the lower content section."""
        trace_in()
        # Filter out empty content - only add if content has non-whitespace or is exactly "\n"
        if content and (content.strip() or content == "\n"):
            # Convert "\n" to empty string, otherwise use content as-is
            processed_content = "" if content == "\n" else content
            self.lower_content.append(processed_content)
            log(f"Added lower content: {len(processed_content)} characters")
        else:
            log("Skipped empty lower content")
        trace_out()
    
    def has_action_response(self) -> bool:
        trace_in()
        result = self.action_response is not None
        log(f"Has action response: {result}")
        trace_out()
        return result

    def set_action_response(self, data: dict) -> None:
        trace_in()
        self.action_response = data
        log(f"Set action response: {len(str(data))} characters")
        trace_out()
    
    def get_action_response(self) -> Optional[dict]:
        trace_in()
        result = self.action_response
        log(f"Retrieved action response: {type(result)}")
        trace_out()
        return result
    
    # ---- User tier level helpers ----
    
    def set_user_tier_level(self, level: int) -> None:
        """Set the user tier level (0 = unknown, 1 = guest, 2 = verified, 3 = admin, 4 = root)."""
        trace_in()
        if not isinstance(level, int) or level < 0:
            warn(f"set_user_tier_level called with invalid argument: {level}")
            trace_out()
            return
        # Only set if tier level is currently 0 (unknown) - allow setting only once
        if self.user_tier_level != 0:
            trace_out()
            return
        self.user_tier_level = level
        tier_names = {0: 'unknown', 1: 'guest', 2: 'verified', 3: 'admin', 4: 'root'}
        tier_name = tier_names.get(level, 'unknown')
        debug(f"User tier level detected: {level} ({tier_name})")
        log(f"Set user tier level: {level}")
        trace_out()
    
    def get_user_tier_level(self) -> int:
        """Return current user tier level (0 = unknown, 1 = guest, 2 = verified, 3 = admin, 4 = root)."""
        return self.user_tier_level
    
    def get_output(self) -> str:
        if self.output_buffer:
            result = "\n".join(self.output_buffer)
        else:
            result = ""
        return result


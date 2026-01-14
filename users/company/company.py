from __future__ import annotations
from typing import Dict, Any, List, Optional
from users.user.user import UserPage
from hh.page.page_class_registry import register_page_class
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_company_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('company')
class CompanyPage(UserPage):
    """
    Page class for company/business accounts.

    Extends UserPage with "Instagram-style upgrade to business account" pattern.
    Inherits all UserPage behavior and validation rules.

    Additional metadata fields (extracted automatically by Page.__init__):
    - company_name: Official company name
    - tax_id: Tax identification number
    - business_type: Type of business
    - (other company-specific fields as needed)
    """

    def __init__(self, id: int):
        """Initialize CompanyPage by calling parent constructor."""
        super().__init__(id)

    # Inherits all validation methods from UserPage:
    # - allow_null_names() = False (must have username)
    # - allow_duplicate_names() = False (unique usernames)
    # - auto_link_name() = True (username becomes URL)
    # - allow_inside_of() restricts to users_container

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return section header links for company pages."""
        return ['Companies']

    def _get_child_row_field_type(self) -> str:
        """Return field type for company pages in table displays."""
        return 'company'

    def _get_display_name(self) -> str:
        """
        Return display name for the company.
        Uses company_name metadata if available, falls back to username.
        """
        # Check if company_name was extracted from metadata
        if hasattr(self, 'company_name') and self.company_name:
            return self.company_name
        # Fall back to UserPage display name logic
        return super()._get_display_name()

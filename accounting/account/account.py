"""
Account page class for accounting system.
Extends Page with account type information.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from accounting.ocr_page.ocr_page import OcrPage
from hh_page.page_registry import get_page
from hh_page.page_class_registry import register_page_class

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_account_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('account')
class Account(OcrPage):
    """
    Account page class for managing financial accounts (cash, checking, savings, etc.).
    """
    
    # Type annotations for metadata-extracted attributes
    type: str
    
    def __init__(self, id: int):
        """Initialize Account by calling parent constructor."""
        super().__init__(id)
        # Initialize metadata-extracted attributes with defaults
        if not hasattr(self, 'type'):
            self.type = 'cash'
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Accounts do not allow null names."""
        return False
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Accounts do not allow duplicate names."""
        return False
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Accounts auto-link names."""
        return True
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Accounts can only contain statements."""
        return target_class == 'statement'
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Accounts can be inside pages."""
        return parent_class == 'page'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for account section headers."""
        return ['Accounts', 'grouped']

    @classmethod
    def get_section_html(cls, parent_id: int, section: str, view_type: str, class_name: Optional[str] = None) -> Optional[str]:
        """
        Custom HTML rendering for account children section content.
        Returns HTML content with grouped tables by account type when view_type is 'grouped accounts'.
        """
        trace_in()

        # Only handle 'children' section for 'account' class
        if section != 'children' or class_name != 'account':
            trace_out()
            return None

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            trace_out()
            return None

        parent_page = get_page(parent_id)
        if not parent_page:
            warn(f"Parent page {parent_id} not found")
            trace_out()
            return None

        if view_type == 'grouped accounts':
            # Get raw children data grouped by type
            query, params = cls.get_browser_sort_query(parent_id, 'grouped')
            if not query:
                warn("Failed to build grouped accounts query")
                trace_out()
                return None

            results = gateway.conn.read(query, params)
            log(f"get_section_html: grouped accounts query returned {len(results) if results else 0} rows")

            if not results:
                # Return empty content with proper wrapper
                page_id_str = str(parent_id)
                content_id = f"child_pages_account_{page_id_str}"
                trace_out()
                return f'<div id="{content_id}"></div>'

            # Build grouped HTML content
            page_id_str = str(parent_id)
            content_id = f"child_pages_account_{page_id_str}"

            # Group results by account type
            grouped_data: Dict[str, List[Dict[str, Any]]] = {}
            for row in results:
                account_type = row.get('groupBy', 'unknown')
                if account_type not in grouped_data:
                    grouped_data[account_type] = []

                # Get full account data
                child_page = get_page(page_id=row['id'])
                if child_page:
                    child_data = child_page._get_child_page_data()
                    child_count = child_page.get_child_count()
                    child_data['num_children'] = child_count
                    child_data['field_type'] = child_page._get_child_row_field_type()
                    grouped_data[account_type].append(child_data)

            # Start the wrapper div
            html = f'<div id="{content_id}">'

            # Render each group
            for account_type, accounts in grouped_data.items():
                # Calculate group total
                group_total = sum(float(acc.get('balance', 0)) for acc in accounts)
                html += cls._render_account_table(accounts, group_total, account_type)

            # Close the wrapper div
            html += '</div>'

            trace_out()
            return html

        trace_out()
        return None

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Query for account children of a parent page."""
        # Order by type first (matching legacy FIELD ordering), then name
        return (
            """SELECT id FROM pages 
               WHERE parent = %s AND class = 'account' 
               ORDER BY 
                 FIELD(JSON_EXTRACT(metadata, '$.type'), 'cash', 'checking', 'savings', 'online', 'credit', 'loan', 'service', 'person', 'open order', 'lease', 'sublet', 'house fund'),
                 name""",
            [parent_id]
        )
    
    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'table') -> List[Dict[str, Any]]:
        """
        Override to query for account pages with default table view.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return []
        
        query, params = cls._get_children_query(parent_id)
        results = gateway.conn.read(query, params)
        children_data = []
        
        if view_type == 'grouped accounts':
            debug(f"getChildrenOf: calling get_browser_sort_query for grouped accounts")
            query, params = cls.get_browser_sort_query(parent_id, 'grouped')
            debug(f"getChildrenOf: get_browser_sort_query returned query: {query}")
            if not query:
                warn("Failed to build query for grouped accounts view")
                trace_out()
                return []

            debug(f"getChildrenOf: executing grouped query: {query}")
            results = gateway.conn.read(query, params)
            log(f"getChildrenOf: grouped query returned {len(results) if results else 0} rows")

            if results:
                for row in results:
                    debug(f"getChildrenOf: processing row with keys: {list(row.keys())}, groupBy: {row.get('groupBy', 'NOT_PRESENT')}")
                    child_page = get_page(page_id=row['id'])
                    if child_page:
                        child_data = child_page._get_child_page_data()
                        child_count = child_page.get_child_count()
                        child_data['num_children'] = child_count
                        child_data['field_type'] = child_page._get_child_row_field_type()
                        child_data['_format'] = 'table'
                        # Add groupBy field for grouped views
                        if 'groupBy' in row:
                            child_data['groupBy'] = str(row['groupBy']) if row['groupBy'] is not None else ''
                            debug(f"getChildrenOf: added groupBy '{child_data['groupBy']}' to child_data")
                        children_data.append(child_data)
            log(f"Loaded {len(children_data)} children for class 'account' (grouped accounts)")
        elif view_type == 'table':
            if results:
                for row in results:
                    child_page = get_page(page_id=row['id'])
                    if child_page:
                        child_data = child_page._get_child_page_data()
                        child_count = child_page.get_child_count()
                        child_data['num_children'] = child_count
                        child_data['field_type'] = child_page._get_child_row_field_type()
                        child_data['_format'] = 'table'
                        children_data.append(child_data)
            log(f"Loaded {len(children_data)} children for class 'account' (table format)")
        else:  # view_type == 'tile'
            if results:
                for row in results:
                    child_page = get_page(page_id=row['id'])
                    if child_page:
                        child_data = child_page._get_child_page_data()
                        display_name = child_page._get_display_name()
                        child_data['display_name'] = display_name
                        images_data = child_page.get_images_data()
                        if images_data and len(images_data) > 0:
                            child_data['images'] = [images_data[0]]
                        else:
                            child_data['images'] = []
                        child_data['_format'] = 'tile'
                        children_data.append(child_data)
            log(f"Loaded {len(children_data)} children for class 'account' (tile format)")
        
        trace_out()
        return children_data

    @classmethod
    def get_browser_sort_query(cls, parent_id: int, view_type: str) -> tuple[str, list]:
        """
        Build query string for account browser sorting based on view_type.
        For 'grouped' view_type, groups by account type with proper ordering.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            trace_out()
            return ("", [])

        if view_type == 'grouped':
            # Group by account type with FIELD() ordering like legacy PHP
            query = """
                SELECT pages.id as id,
                       COALESCE(JSON_EXTRACT(pages.metadata, '$.type'), 'unknown') as groupBy
                FROM pages
                WHERE pages.parent = %s
                  AND pages.class = 'account'
                ORDER BY FIELD(COALESCE(JSON_EXTRACT(pages.metadata, '$.type'), 'unknown'),
                              'cash','checking','savings','online','credit','loan','service','person','open order','lease','sublet','house fund'),
                       pages.name
            """
            params = [parent_id]
        else:
            # Default fallback
            query = ""
            params = []

        trace_out()
        debug(f"get_browser_sort_query: returning query='{query[:100]}...', params={params}")
        return (query, params)

    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return data for account rows in table view."""
        trace_in()
        data = {
            "id": self.id,
            "name": self.name,
            "type": self.type if hasattr(self, 'type') else 'cash',
        }
        trace_out()
        return data
    
    def _get_child_row_field_type(self) -> str:
        """Return field type for account rows."""
        return 'account'
    
    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize account metadata.
        Sets default account type to 'cash'.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for add_page_class_information")
            trace_out()
            return
        
        # Get type from gateway arguments (optional, defaults to 'cash')
        account_type = gateway.get_arg('type') or 'cash'
        
        page = get_page(new_page_id)
        if not page:
            warn(f"Failed to load page {new_page_id} for metadata initialization")
            trace_out()
            return
        
        page.set_metadata_value('type', account_type)
        page.type = account_type
        
        log(f"Initialized metadata for account page {new_page_id} with type '{account_type}'")
        trace_out()
    
    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add account-specific fields to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['type'] = self.type if self.type else None
        else:
            warn(f"Account._add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers
    
    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """Account keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge
    
    def modify_account_type(self, account_type: str) -> bool:
        """Modify the account type."""
        trace_in()
        self.set_metadata_value('type', account_type)
        self.type = account_type
        self.flag_page_modification("account type changed")
        log(f"Modified account type for page {self.id} to '{account_type}'")
        trace_out()
        return not is_error()
    
    def _get_display_name(self) -> str:
        """Return formatted display name for account."""
        if self.name:
            return self.name

        # Format like legacy: just return the name, fallback to base
        return super()._get_display_name()

    def get_page_data(self) -> Dict[str, Any]:
        """Override to add account-specific fields to full page data."""
        trace_in()
        data = super().get_page_data()
        data['type'] = self.type
        trace_out()
        return data

    @classmethod
    def _render_account_table(cls, accounts: List[Dict[str, Any]], group_total: float, account_type: str) -> str:
        """Render a single account table with header, rows, and footer for a specific account type."""
        html = f'<div class="contentHeader">{account_type.title()}</div>'
        html += '<div class="content tableViewDiv">'
        html += '<table class="pageTableView accountTableView" cellpadding="0" cellspacing="0">'
        html += '<thead><tr>'
        html += '<th>&nbsp;</th>'
        html += '<th class="name">Account Name</th>'
        html += '<th class="type">Type</th>'
        html += '<th class="balance">Balance</th>'
        html += '</tr></thead><tbody>'

        row_ctr = 0
        for account_data in accounts:
            account_id = account_data.get('id')
            name = account_data.get('name', '')
            account_type_display = account_data.get('type', 'unknown')
            balance = account_data.get('balance', 0.0)
            num_children = account_data.get('num_children', 0)

            row_class = 'odd' if (row_ctr % 2) == 0 else 'even'
            html += f'<tr class="{row_class}">'
            html += f'<td class="num_children">({num_children})</td>'
            html += f'<td class="name"><a href="{account_id}">{name}</a></td>'
            html += f'<td class="type">{account_type_display}</td>'
            html += f'<td class="balance">{balance:.2f}</td>'
            html += '</tr>'
            row_ctr += 1

        html += '</tbody><tfoot><tr class="totalFooter">'
        html += '<td>&nbsp;</td>'
        html += f'<td colspan="2">{row_ctr} {account_type.title()} Accounts Total</td>'
        html += f'<td class="balance">{group_total:.2f}</td>'
        html += '</tr></tfoot></table></div>'

        return html


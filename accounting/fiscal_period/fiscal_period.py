"""
FiscalPeriod page class for accounting system.
Extends Page with fiscal period date range information.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from ext.ocr_page.ocr_page import OcrPage
from hh.page.page_registry import get_page
from hh.page.page_class_registry import register_page_class

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_fiscal_period_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('fiscalPeriod')
class FiscalPeriod(OcrPage):
    """
    Fiscal Period page class for organizing accounting data by time periods.
    """
    
    # Type annotations for metadata-extracted attributes
    startDate: str
    endDate: str
    
    def __init__(self, id: int):
        """Initialize FiscalPeriod by calling parent constructor."""
        super().__init__(id)
        # Initialize metadata-extracted attributes with defaults
        if not hasattr(self, 'startDate'):
            self.startDate = ''
        if not hasattr(self, 'endDate'):
            self.endDate = ''
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Fiscal periods allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Fiscal periods allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Fiscal periods do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Fiscal periods cannot contain any child pages."""
        return False
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Fiscal periods can be inside pages."""
        return parent_class == 'page'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for fiscal period section headers."""
        return ['Fiscal Periods']

    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'table') -> List[Dict[str, Any]]:
        """
        Override to query for fiscal period pages with default table view.
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

        if view_type == 'table':
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
            log(f"Loaded {len(children_data)} children for class 'fiscalPeriod' (table format)")
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
            log(f"Loaded {len(children_data)} children for class 'fiscalPeriod' (tile format)")

        trace_out()
        return children_data

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Query for fiscal period children of a parent page."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'fiscalPeriod' ORDER BY name",
            [parent_id]
        )
    
    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize fiscal period metadata.
        Sets default values for fiscal period fields.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for add_page_class_information")
            trace_out()
            return
        
        page = get_page(new_page_id)
        if not page:
            warn(f"Failed to load page {new_page_id} for metadata initialization")
            trace_out()
            return
        
        # Initialize fiscal period fields with defaults
        page.set_metadata_value('startDate', '')
        page.set_metadata_value('endDate', '')
        
        # Also set attributes directly
        page.startDate = ''
        page.endDate = ''
        
        log(f"Initialized metadata for fiscal period page {new_page_id}")
        trace_out()
    
    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add fiscal period-specific fields to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['startDate'] = self.startDate if self.startDate else None
            badge_headers['page_summary']['endDate'] = self.endDate if self.endDate else None
        else:
            warn(f"FiscalPeriod._add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers
    
    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """FiscalPeriod keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge
    
    def modify_fiscal_period_info(self, start_date: str, end_date: str) -> bool:
        """Modify fiscal period date range information."""
        trace_in()
        self.set_metadata_value('startDate', start_date)
        self.set_metadata_value('endDate', end_date)
        self.startDate = start_date
        self.endDate = end_date
        self.flag_page_modification("fiscal period info changed")
        log(f"Modified fiscal period info for page {self.id}: startDate={start_date}, endDate={end_date}")
        trace_out()
        return not is_error()
    
    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return data for fiscal period rows in table view."""
        trace_in()
        data = {
            "id": self.id,
            "name": self.name,
            "startDate": self.startDate if hasattr(self, 'startDate') else '',
            "endDate": self.endDate if hasattr(self, 'endDate') else '',
        }
        trace_out()
        return data

    def _get_display_name(self) -> str:
        """Return formatted display name for fiscal period, following legacy getNameString pattern."""
        if self.name:
            return self.name

        # Format like legacy: "2023 (Jan - Dec)"
        if hasattr(self, 'startDate') and hasattr(self, 'endDate') and self.startDate and self.endDate:
            try:
                from datetime import datetime
                start_date = datetime.strptime(self.startDate, '%Y-%m-%d')
                end_date = datetime.strptime(self.endDate, '%Y-%m-%d')

                start_month = start_date.strftime('%b')
                end_month = end_date.strftime('%b')
                end_year = end_date.strftime('%Y')

                if start_date.year == end_date.year:
                    return f"{end_year} ({start_month} - {end_month})"
                else:
                    return f"{start_date.year}-{end_year} ({start_month} - {end_month})"
            except (ValueError, AttributeError):
                pass

        # Fallback to base class behavior
        return super()._get_display_name()

    def _get_child_row_field_type(self) -> str:
        """Return field type for fiscal period rows."""
        return 'fiscalPeriod'

    def get_page_data(self) -> Dict[str, Any]:
        """Override to add fiscal period-specific fields to full page data."""
        trace_in()
        data = super().get_page_data()
        data['startDate'] = self.startDate
        data['endDate'] = self.endDate
        trace_out()
        return data


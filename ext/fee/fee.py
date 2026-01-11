"""
Fee page class for accounting system.
Extends Page with fee date and amount information.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from ext.ocr_page.ocr_page import OcrPage
from hh.page.page_registry import get_page
from hh.page.page_class_registry import register_page_class
from ext.currency_math import DecimalMath

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_fee_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('fee')
class Fee(OcrPage):
    """
    Fee page class for recording fees charged on statements.
    """
    
    # Type annotations for metadata-extracted attributes
    date: str
    fee: str
    
    def __init__(self, id: int):
        """Initialize Fee by calling parent constructor."""
        super().__init__(id)
        # Initialize metadata-extracted attributes with defaults
        if not hasattr(self, 'date'):
            self.date = ''
        if not hasattr(self, 'fee'):
            self.fee = ''
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Fees allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Fees allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Fees do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Fees cannot contain any child pages."""
        return False
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Fees can only be inside statements."""
        return parent_class == 'statement'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for fee section headers."""
        return ['Fees']

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Query for fee children of a parent page."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'fee' ORDER BY JSON_EXTRACT(metadata, '$.date'), id",
            [parent_id]
        )
    
    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'table') -> List[Dict[str, Any]]:
        """
        Override to query for fee pages with default table view.
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
            log(f"Loaded {len(children_data)} children for class 'fee' (table format)")
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
            log(f"Loaded {len(children_data)} children for class 'fee' (tile format)")
        
        trace_out()
        return children_data
    
    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return data for fee rows in table view."""
        trace_in()
        data = {
            "id": self.id,
            "name": self.name,
            "date": self.date if hasattr(self, 'date') else '',
            "fee": self.fee if hasattr(self, 'fee') else 0.0,
            "text": self.text if hasattr(self, 'text') else '',
        }
        trace_out()
        return data
    
    def _get_child_row_field_type(self) -> str:
        """Return field type for fee rows."""
        return 'fee'
    
    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize fee metadata.
        Sets default values for fee fields.
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
        
        # Initialize fee fields with defaults
        page.set_metadata_value('date', '')
        page.set_metadata_value('fee', 0.0)
        
        # Also set attributes directly
        page.date = ''
        page.fee = 0.0
        
        log(f"Initialized metadata for fee page {new_page_id}")
        trace_out()
    
    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add fee-specific fields to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['date'] = self.date if self.date else None
            badge_headers['page_summary']['fee'] = f"{self.fee:.2f}" if self.fee else "0.00"
        else:
            warn(f"Fee._add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers
    
    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """Fee keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge
    
    def modify_fee_info(self, fee: str, date: str = '') -> bool:
        """Modify fee information (fee amount and date). Matches legacy modifyFeeInfo."""
        trace_in()
        # Normalize to 2 decimal places for currency
        normalized_fee = DecimalMath.normalize(fee)
        self.set_metadata_value('fee', normalized_fee)
        self.set_metadata_value('date', date)
        self.fee = normalized_fee
        self.date = date
        self.flag_page_modification("fee info changed")
        log(f"Modified fee info for page {self.id}: fee={normalized_fee}, date={date}")
        trace_out()
        return not is_error()
    
    def recalculateGeneratedValues(self) -> bool:
        """
        Propagate recalculation to parent page (statement).
        Matches legacy Fee::recalculateGeneratedValues().
        """
        trace_in()
        # Recalculate parent page (statement)
        if self.parent:
            parent_page = get_page(self.parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        
        log(f"Propagated recalculation from fee {self.id} to parent={self.parent}")
        trace_out()
        return not is_error()
    
    def _after_copy_page(self, new_page_id: int) -> None:
        """Hook called after copying a fee page. Recalculates new parent."""
        trace_in()
        # Recalculate the new parent (statement)
        if self.parent:
            parent_page = get_page(self.parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        trace_out()
    
    def _after_move_page(self, old_parent_id: Optional[int], new_parent_id: int) -> None:
        """Hook called after moving a fee page. Recalculates old parent and new parent."""
        trace_in()
        # Recalculate old parent
        if old_parent_id and old_parent_id != 0:
            old_parent = get_page(old_parent_id)
            if old_parent and hasattr(old_parent, 'recalculateGeneratedValues'):
                old_parent.recalculateGeneratedValues()
        # Recalculate new parent
        if new_parent_id and new_parent_id != 0:
            new_parent = get_page(new_parent_id)
            if new_parent and hasattr(new_parent, 'recalculateGeneratedValues'):
                new_parent.recalculateGeneratedValues()
        trace_out()
    
    def _before_delete_page(self) -> None:
        """Hook called before deleting a fee page. Captures parent for later recalculation."""
        trace_in()
        # Store parent for use in _after_delete_page
        self._deleted_parent = self.parent
        trace_out()
    
    def _after_delete_page(self) -> None:
        """Hook called after deleting a fee page. Recalculates old parent."""
        trace_in()
        # Recalculate old parent
        if hasattr(self, '_deleted_parent') and self._deleted_parent:
            parent_page = get_page(self._deleted_parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        trace_out()
    
    def _get_display_name(self) -> str:
        """Return formatted display name for fee, following legacy getNameString pattern."""
        if self.name:
            return self.name

        # Format like legacy: "Fee #123"
        return f"Fee #{self.id}"

    def get_page_data(self) -> Dict[str, Any]:
        """Override to add fee-specific fields to full page data."""
        trace_in()
        data = super().get_page_data()
        data['date'] = self.date
        data['fee'] = self.fee
        trace_out()
        return data


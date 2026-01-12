"""
Transfer page class for accounting system.
Extends Page with transfer amount, date, fee, and target information.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from accounting.ocr_page.ocr_page import OcrPage
from hh.page.page_registry import get_page
from hh.page.page_class_registry import register_page_class
from accounting.currency_math import DecimalMath

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_transfer_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('transfer')
class Transfer(OcrPage):
    """
    Transfer page class for recording money transfers between accounts.
    """
    
    # Type annotations for metadata-extracted attributes
    transferTo: Optional[int]
    date: str
    amount: str
    fee: str
    
    def __init__(self, id: int):
        """Initialize Transfer by calling parent constructor."""
        super().__init__(id)
        # Initialize metadata-extracted attributes with defaults
        if not hasattr(self, 'transferTo'):
            self.transferTo = None
        if not hasattr(self, 'date'):
            self.date = ''
        if not hasattr(self, 'amount'):
            self.amount = ''
        if not hasattr(self, 'fee'):
            self.fee = ''
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Transfers allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Transfers allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Transfers do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Transfers cannot contain any child pages."""
        return False
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Transfers can be inside statements, sales, or invoices."""
        return parent_class in ['statement', 'sale', 'invoice']

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for transfer section headers."""
        return ['Transfers']

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Query for transfer children of a parent page."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'transfer' ORDER BY JSON_EXTRACT(metadata, '$.date'), id",
            [parent_id]
        )
    
    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'table') -> List[Dict[str, Any]]:
        """
        Override to query for transfer pages with default table view.
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
            log(f"Loaded {len(children_data)} children for class 'transfer' (table format)")
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
            log(f"Loaded {len(children_data)} children for class 'transfer' (tile format)")
        
        trace_out()
        return children_data
    
    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return data for transfer rows in table view."""
        trace_in()
        # Calculate net amount (amount - fee)
        amount = str(self.amount or '')
        fee = str(self.fee or '')
        net = DecimalMath.subtract(amount, fee)
        
        # Get reference from parent page
        reference = ''
        if self.parent:
            parent_page = get_page(self.parent)
            if parent_page:
                if parent_page.class_name == 'statement':
                    # For statement transfers, reference is the account name
                    if parent_page.parent:
                        account_page = get_page(parent_page.parent)
                        if account_page:
                            reference = account_page.name or ''
                elif parent_page.class_name in ['invoice', 'sale']:
                    # For invoice/sale transfers, reference is the invoice/sale name
                    reference = parent_page.name or ''
        
        data = {
            "id": self.id,
            "name": self.name,
            "date": self.date if hasattr(self, 'date') else '',
            "reference": reference,
            "amount": amount,
            "fee": fee,
            "net": net,
            "text": self.text if hasattr(self, 'text') else '',
        }
        trace_out()
        return data
    
    def _get_child_row_field_type(self) -> str:
        """Return field type for transfer rows."""
        return 'transfer'
    
    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize transfer metadata.
        Sets default values for transfer fields.
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
        
        # Initialize transfer fields with defaults
        page.set_metadata_value('transferTo', None)
        page.set_metadata_value('date', '')
        page.set_metadata_value('amount', 0.0)
        page.set_metadata_value('fee', 0.0)
        
        # Also set attributes directly
        page.transferTo = None
        page.date = ''
        page.amount = 0.0
        page.fee = 0.0
        
        log(f"Initialized metadata for transfer page {new_page_id}")
        trace_out()
    
    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add transfer-specific fields to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['transferTo'] = str(self.transferTo) if self.transferTo else None
            badge_headers['page_summary']['date'] = self.date if self.date else None
            badge_headers['page_summary']['amount'] = f"{self.amount:.2f}" if self.amount else "0.00"
            badge_headers['page_summary']['fee'] = f"{self.fee:.2f}" if self.fee else "0.00"
        else:
            warn(f"Transfer._add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers
    
    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """Transfer keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge
    
    def modify_transfer_info(self, date: str, amount: str, modifier: str, fee: str) -> bool:
        """Modify transfer information (date, amount, modifier, fee). Matches legacy modifyTransferInfo."""
        trace_in()
        # Handle modifier: if modifier != 0, adjust amount by modifier
        normalized_amount = DecimalMath.normalize(amount)
        normalized_modifier = DecimalMath.normalize(modifier)
        if not DecimalMath.is_zero(normalized_modifier):
            current_amount = str(self.amount or '')
            adjusted_amount = DecimalMath.add(current_amount, normalized_modifier)
            normalized_amount = DecimalMath.normalize(adjusted_amount)
        normalized_fee = DecimalMath.normalize(fee)
        
        self.set_metadata_value('date', date)
        self.set_metadata_value('amount', normalized_amount)
        self.set_metadata_value('fee', normalized_fee)
        self.date = date
        self.amount = normalized_amount
        self.fee = normalized_fee
        self.flag_page_modification("transfer info changed")
        log(f"Modified transfer info for page {self.id}: date={date}, amount={normalized_amount}, modifier={normalized_modifier}, fee={normalized_fee}")
        trace_out()
        return not is_error()
    
    def modify_target_info(self, transfer_to: Optional[int]) -> bool:
        """Modify the transfer target page ID."""
        trace_in()
        self.set_metadata_value('transferTo', transfer_to)
        self.transferTo = transfer_to
        self.flag_page_modification("transfer target changed")
        log(f"Modified transfer target for page {self.id} to '{transfer_to}'")
        trace_out()
        return not is_error()
    
    def recalculateGeneratedValues(self) -> bool:
        """
        Propagate recalculation to parent page and transferTo page (if set).
        Matches legacy Transfer::recalculateGeneratedValues().
        """
        trace_in()
        # Recalculate parent page (statement, sale, or invoice)
        if self.parent:
            parent_page = get_page(self.parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        
        # Recalculate transferTo page (if set and valid)
        if self.transferTo:
            transfer_to_page = get_page(self.transferTo)
            if transfer_to_page and hasattr(transfer_to_page, 'recalculateGeneratedValues'):
                transfer_to_page.recalculateGeneratedValues()
        
        log(f"Propagated recalculation from transfer {self.id} to parent={self.parent}, transferTo={self.transferTo}")
        trace_out()
        return not is_error()
    
    def _after_copy_page(self, new_page_id: int) -> None:
        """Hook called after copying a transfer page. Recalculates new parent and new target."""
        trace_in()
        # Recalculate the new parent (statement, sale, or invoice)
        if self.parent:
            parent_page = get_page(self.parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        # Recalculate the new target (transferTo of the new page)
        new_page = get_page(new_page_id)
        if new_page and hasattr(new_page, 'transferTo') and new_page.transferTo:
            transfer_to_page = get_page(new_page.transferTo)
            if transfer_to_page and hasattr(transfer_to_page, 'recalculateGeneratedValues'):
                transfer_to_page.recalculateGeneratedValues()
        trace_out()
    
    def _after_move_page(self, old_parent_id: Optional[int], new_parent_id: int) -> None:
        """Hook called after moving a transfer page. Recalculates old parent and new parent (NOT target)."""
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
        """Hook called before deleting a transfer page. Captures parent and transferTo for later recalculation."""
        trace_in()
        # Store parent and transferTo for use in _after_delete_page
        self._deleted_parent = self.parent
        self._deleted_transfer_to = self.transferTo
        trace_out()
    
    def _after_delete_page(self) -> None:
        """Hook called after deleting a transfer page. Recalculates old parent and old target."""
        trace_in()
        # Recalculate old parent
        if hasattr(self, '_deleted_parent') and self._deleted_parent:
            parent_page = get_page(self._deleted_parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        # Recalculate old target
        if hasattr(self, '_deleted_transfer_to') and self._deleted_transfer_to:
            transfer_to_page = get_page(self._deleted_transfer_to)
            if transfer_to_page and hasattr(transfer_to_page, 'recalculateGeneratedValues'):
                transfer_to_page.recalculateGeneratedValues()
        trace_out()
    
    def _get_display_name(self) -> str:
        """Return formatted display name for transfer, following legacy getNameString pattern."""
        if self.name:
            return self.name

        # Format like legacy: "Transfer #123"
        return f"Transfer #{self.id}"

    def get_page_data(self) -> Dict[str, Any]:
        """Override to add transfer-specific fields to full page data."""
        trace_in()
        data = super().get_page_data()
        data['transferTo'] = self.transferTo
        data['date'] = self.date
        data['amount'] = self.amount
        data['fee'] = self.fee
        trace_out()
        return data


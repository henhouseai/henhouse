"""
Sale page class for accounting system.
Extends Page with sale information including customer details and totals.
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
def _initialize_sale_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('sale')
class Sale(OcrPage):
    """
    Sale page class for recording sales transactions (money coming in).
    """
    
    # Type annotations for metadata-extracted attributes
    receiptNum: Optional[str]
    date: str
    saleType: str
    customerName: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postalCode: Optional[str]
    country: Optional[str]
    total: float
    tax: float
    shipping: float
    balanced: bool
    
    def __init__(self, id: int):
        """Initialize Sale by calling parent constructor."""
        super().__init__(id)
    
    def _after_metadata_extraction(self) -> None:
        """Override hook to set defaults for sale metadata fields and trigger recalculation if needed."""
        # Initialize metadata-extracted attributes with defaults
        if not hasattr(self, 'receiptNum'):
            self.receiptNum = None
        if not hasattr(self, 'date'):
            self.date = ''
        if not hasattr(self, 'saleType'):
            self.saleType = 'retail'
        if not hasattr(self, 'customerName'):
            self.customerName = None
        if not hasattr(self, 'address'):
            self.address = None
        if not hasattr(self, 'city'):
            self.city = None
        if not hasattr(self, 'state'):
            self.state = None
        if not hasattr(self, 'postalCode'):
            self.postalCode = None
        if not hasattr(self, 'country'):
            self.country = None
        if not hasattr(self, 'total'):
            self.total = 0.0
        if not hasattr(self, 'tax'):
            self.tax = 0.0
        if not hasattr(self, 'shipping'):
            self.shipping = 0.0
        if not hasattr(self, 'balanced'):
            self.balanced = False
        
        # Check if derived field is at default value (indicating it hasn't been calculated)
        # If so, trigger recalculation
        if self.balanced == False:
            # Store original value to check if it changed
            old_balanced = self.balanced
            
            # Trigger recalculation
            self.recalculateGeneratedValues()
            
            # Check if value changed from default - if so, cache refresh already flagged by recalculateGeneratedValues
            if self.balanced != old_balanced:
                # Value changed, cache refresh already flagged
                pass
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Sales allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Sales allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Sales do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Sales can only contain transfers."""
        return target_class == 'transfer'
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Sales can be inside pages."""
        return parent_class == 'page'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for sale section headers."""
        return ['Sales']

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Query for sale children of a parent page."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'sale' ORDER BY JSON_EXTRACT(metadata, '$.date') DESC, JSON_EXTRACT(metadata, '$.receiptNum') DESC, JSON_EXTRACT(metadata, '$.saleType'), id DESC",
            [parent_id]
        )
    
    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'table') -> List[Dict[str, Any]]:
        """
        Override to query for sale pages with default table view.
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
            log(f"Loaded {len(children_data)} children for class 'sale' (table format)")
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
            log(f"Loaded {len(children_data)} children for class 'sale' (tile format)")
        
        trace_out()
        return children_data
    
    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return data for sale rows in table view."""
        trace_in()
        # Ensure derived value is calculated
        if hasattr(self, 'get_balanced'):
            self.get_balanced()
        
        # Calculate subtotal (total - tax - shipping)
        total = self.total if hasattr(self, 'total') else 0.0
        tax = self.tax if hasattr(self, 'tax') else 0.0
        shipping = self.shipping if hasattr(self, 'shipping') else 0.0
        subtotal = total - tax - shipping
        
        data = {
            "id": self.id,
            "name": self.name,
            "receiptNum": self.receiptNum if hasattr(self, 'receiptNum') else None,
            "date": self.date if hasattr(self, 'date') else '',
            "saleType": self.saleType if hasattr(self, 'saleType') else 'retail',
            "customerName": self.customerName if hasattr(self, 'customerName') else None,
            "subtotal": subtotal,
            "shipping": shipping,
            "tax": tax,
            "total": total,
            "text": self.text if hasattr(self, 'text') else '',
        }
        trace_out()
        return data
    
    def _get_child_row_field_type(self) -> str:
        """Return field type for sale rows. Uses 'red' class if not balanced."""
        balanced = self.balanced if hasattr(self, 'balanced') else False
        return 'sale_red' if not balanced else 'sale'
    
    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize sale metadata.
        Sets default values for sale fields.
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
        
        # Initialize sale fields with defaults
        page.set_metadata_value('receiptNum', None)
        page.set_metadata_value('date', '')
        page.set_metadata_value('saleType', 'retail')
        page.set_metadata_value('customerName', None)
        page.set_metadata_value('address', None)
        page.set_metadata_value('city', None)
        page.set_metadata_value('state', None)
        page.set_metadata_value('postalCode', None)
        page.set_metadata_value('country', None)
        page.set_metadata_value('total', 0.0)
        page.set_metadata_value('tax', 0.0)
        page.set_metadata_value('shipping', 0.0)
        page.set_metadata_value('balanced', False)
        
        # Also set attributes directly
        page.receiptNum = None
        page.date = ''
        page.saleType = 'retail'
        page.customerName = None
        page.address = None
        page.city = None
        page.state = None
        page.postalCode = None
        page.country = None
        page.total = 0.0
        page.tax = 0.0
        page.shipping = 0.0
        page.balanced = False
        
        log(f"Initialized metadata for sale page {new_page_id}")
        trace_out()
    
    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add sale-specific fields to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['receiptNum'] = self.receiptNum if self.receiptNum else None
            badge_headers['page_summary']['date'] = self.date if self.date else None
            badge_headers['page_summary']['saleType'] = self.saleType if self.saleType else None
            badge_headers['page_summary']['customerName'] = self.customerName if self.customerName else None
            badge_headers['page_summary']['address'] = self.address if self.address else None
            badge_headers['page_summary']['city'] = self.city if self.city else None
            badge_headers['page_summary']['state'] = self.state if self.state else None
            badge_headers['page_summary']['postalCode'] = self.postalCode if self.postalCode else None
            badge_headers['page_summary']['country'] = self.country if self.country else None
            badge_headers['page_summary']['total'] = f"{self.total:.2f}" if self.total else "0.00"
            badge_headers['page_summary']['tax'] = f"{self.tax:.2f}" if self.tax else "0.00"
            badge_headers['page_summary']['shipping'] = f"{self.shipping:.2f}" if self.shipping else "0.00"
            badge_headers['page_summary']['balanced'] = "✅" if self.balanced else "❌"
        else:
            warn(f"Sale._add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers
    
    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """Sale keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge
    
    def modify_sale_info(self, date: str, receipt_num: Optional[str], sale_type: str) -> bool:
        """Modify sale date, receipt number, and sale type information."""
        trace_in()
        self.set_metadata_value('date', date)
        self.set_metadata_value('receiptNum', receipt_num)
        self.set_metadata_value('saleType', sale_type)
        self.date = date
        self.receiptNum = receipt_num
        self.saleType = sale_type
        self.flag_page_modification("sale info changed")
        log(f"Modified sale info for page {self.id}: date={date}, receiptNum={receipt_num}, saleType={sale_type}")
        trace_out()
        return not is_error()
    
    def modify_customer_info(self, customer_name: Optional[str], address: Optional[str], city: Optional[str], state: Optional[str], postal_code: Optional[str], country: Optional[str]) -> bool:
        """Modify customer information (name, address, city, state, postal code, country)."""
        trace_in()
        self.set_metadata_value('customerName', customer_name)
        self.set_metadata_value('address', address)
        self.set_metadata_value('city', city)
        self.set_metadata_value('state', state)
        self.set_metadata_value('postalCode', postal_code)
        self.set_metadata_value('country', country)
        self.customerName = customer_name
        self.address = address
        self.city = city
        self.state = state
        self.postalCode = postal_code
        self.country = country
        self.flag_page_modification("customer info changed")
        log(f"Modified customer info for page {self.id}: customerName={customer_name}, address={address}, city={city}, state={state}, postalCode={postal_code}, country={country}")
        trace_out()
        return not is_error()
    
    def modify_sale_cost_breakdown(self, total: float, tax: float, shipping: float) -> bool:
        """Modify sale cost breakdown (total, tax, shipping)."""
        trace_in()
        self.set_metadata_value('total', total)
        self.set_metadata_value('tax', tax)
        self.set_metadata_value('shipping', shipping)
        self.total = total
        self.tax = tax
        self.shipping = shipping
        self.flag_page_modification("cost breakdown changed")
        log(f"Modified cost breakdown for page {self.id}: total={total}, tax={tax}, shipping={shipping}")
        trace_out()
        return not is_error()
    
    
    def recalculateGeneratedValues(self) -> bool:
        """
        Recalculate derived values: balanced.
        Matches legacy Sale::recalculateGeneratedValues().
        Uses DecimalMath for precise decimal calculations.
        """
        trace_in()

        # Query incoming transfers (transfers where transferTo = this sale.id)
        incoming_query = """
            SELECT id FROM pages
            WHERE class = 'transfer'
            AND CAST(JSON_EXTRACT(metadata, '$.transferTo') AS UNSIGNED) = %s
            ORDER BY JSON_EXTRACT(metadata, '$.date'), id
        """
        incoming_results = self.gateway.conn.read(incoming_query, [self.id])
        incoming_amounts = []
        incoming_fees = []
        if incoming_results:
            for row in incoming_results:
                transfer_page = get_page(row['id'])
                if transfer_page and hasattr(transfer_page, 'amount') and hasattr(transfer_page, 'fee'):
                    # Only count if transferTo is valid (not empty string or invalid)
                    if transfer_page.transferTo and transfer_page.transferTo == self.id:
                        incoming_amounts.append(str(transfer_page.amount or ''))
                        incoming_fees.append(str(transfer_page.fee or ''))

        # Query outgoing transfers (transfers where parent = this sale.id)
        outgoing_query = """
            SELECT id FROM pages
            WHERE parent = %s AND class = 'transfer'
            ORDER BY JSON_EXTRACT(metadata, '$.date'), id
        """
        outgoing_results = self.gateway.conn.read(outgoing_query, [self.id])
        outgoing_amounts = []
        if outgoing_results:
            for row in outgoing_results:
                transfer_page = get_page(row['id'])
                if transfer_page and hasattr(transfer_page, 'amount'):
                    # Only count if transferTo is valid (not empty string or invalid)
                    if transfer_page.transferTo is not None and transfer_page.transferTo != '':
                        outgoing_amounts.append(str(transfer_page.amount or ''))

        # Calculate totals
        total_incoming = DecimalMath.sum(incoming_amounts)
        total_incoming_fees = DecimalMath.sum(incoming_fees)
        total_outgoing = DecimalMath.sum(outgoing_amounts)

        # Calculate balanced based on saleType
        sale_total = str(self.total or '')
        net_incoming = DecimalMath.subtract(total_incoming, total_incoming_fees)

        if self.saleType == 'advance':
            # Advance: total == outgoing == incoming
            balanced = (DecimalMath.equals(sale_total, total_outgoing) and
                       DecimalMath.equals(total_outgoing, net_incoming))
        elif self.saleType == 'refund':
            # Refund: -total == outgoing == incoming
            negative_total = DecimalMath.negate(sale_total)
            balanced = (DecimalMath.equals(negative_total, total_outgoing) and
                       DecimalMath.equals(total_outgoing, net_incoming))
        else:
            # Default: retail, wholesale, consignment, royalty, service, etc.
            # total == (outgoing - incoming)
            net_amount = DecimalMath.subtract(total_outgoing, net_incoming)
            balanced = DecimalMath.equals(sale_total, net_amount)
        
        # Store original value to check if it changed
        old_balanced = getattr(self, 'balanced', False)
        
        # Update balanced
        if self.balanced != balanced:
            self.set_metadata_value('balanced', balanced)
        self.balanced = balanced
        
        # Check if value changed from default - if so, flag cache refresh
        if self.balanced != old_balanced:
            # Value changed, flag cache refresh
            self._flag_cache_refresh()
        
        log(f"Recalculated generated values for sale {self.id}: balanced={balanced} (saleType={self.saleType})")
        
        trace_out()
        return not is_error()
    
    def _after_copy_page(self, new_page_id: int) -> None:
        """Hook called after copying a sale page. Recalculates new page and new parent."""
        trace_in()
        # Recalculate the new page
        new_page = get_page(new_page_id)
        if new_page and hasattr(new_page, 'recalculateGeneratedValues'):
            new_page.recalculateGeneratedValues()
        # Recalculate the new parent (account)
        if self.parent:
            parent_page = get_page(self.parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        trace_out()
    
    def _after_move_page(self, old_parent_id: Optional[int], new_parent_id: int) -> None:
        """Hook called after moving a sale page. Recalculates self, old parent, and new parent."""
        trace_in()
        # Recalculate self
        if hasattr(self, 'recalculateGeneratedValues'):
            self.recalculateGeneratedValues()
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
        """Hook called before deleting a sale page. Captures parent for later recalculation."""
        trace_in()
        # Store parent for use in _after_delete_page
        self._deleted_parent = self.parent
        trace_out()
    
    def _after_delete_page(self) -> None:
        """Hook called after deleting a sale page. Recalculates old parent."""
        trace_in()
        # Recalculate old parent
        if hasattr(self, '_deleted_parent') and self._deleted_parent:
            parent_page = get_page(self._deleted_parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        trace_out()
    
    def _get_display_name(self) -> str:
        """Return formatted display name for sale, following legacy getNameString pattern."""
        if self.name:
            return self.name

        # Format like legacy: "Sale #123 : Customer Name"
        customer_name = self.customerName or ""
        return f"Sale #{self.id} : {customer_name}"

    def get_page_data(self) -> Dict[str, Any]:
        """Override to add sale-specific fields to full page data."""
        trace_in()
        data = super().get_page_data()
        data['receiptNum'] = self.receiptNum
        data['date'] = self.date
        data['saleType'] = self.saleType
        data['customerName'] = self.customerName
        data['address'] = self.address
        data['city'] = self.city
        data['state'] = self.state
        data['postalCode'] = self.postalCode
        data['country'] = self.country
        data['total'] = self.total
        data['tax'] = self.tax
        data['shipping'] = self.shipping
        data['balanced'] = self.balanced
        trace_out()
        return data


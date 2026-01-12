"""
Invoice page class for accounting system.
Extends Page with invoice information including reference and totals.
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
def _initialize_invoice_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('invoice')
class Invoice(OcrPage):
    """
    Invoice page class for recording invoices (money going out).
    """
    
    # Type annotations for metadata-extracted attributes
    date: str
    reference: Optional[str]
    total: str
    tax: str
    shipping: str
    balanced: bool
    
    def __init__(self, id: int):
        """Initialize Invoice by calling parent constructor."""
        super().__init__(id)
    
    def _after_metadata_extraction(self) -> None:
        """Override hook to set defaults for invoice metadata fields and trigger recalculation if needed."""
        # Initialize metadata-extracted attributes with defaults
        if not hasattr(self, 'date'):
            self.date = ''
        if not hasattr(self, 'reference'):
            self.reference = None
        if not hasattr(self, 'total'):
            self.total = ''
        if not hasattr(self, 'tax'):
            self.tax = ''
        if not hasattr(self, 'shipping'):
            self.shipping = ''
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
        """Invoices allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Invoices allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Invoices do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Invoices can only contain transfers."""
        return target_class == 'transfer'
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Invoices can be inside expense categories."""
        return parent_class == 'expenseCategory'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for invoice section headers."""
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            trace_out()
            return []
        
        parent_page = get_page(parent_id)
        if not parent_page:
            warn(f"Parent page {parent_id} not found")
            trace_out()
            return []
        
        parent_class = parent_page.class_name if hasattr(parent_page, 'class_name') else parent_page.__class__.__name__.lower()
        if parent_class == 'fiscalPeriod':
            return ['Invoices', 'd', 'v', '$', 'Yd', 'Yv', 'Y$', 'Md', 'Mv', 'M$', 'Vd', 'V$', 'Cd', 'Cv', 'C$']
        else:
            return ['Invoices', 'd', 'v', '$', 'Yd', 'Yv', 'Y$', 'Fd', 'Fv', 'F$', 'Md', 'Mv', 'M$', 'Vd', 'V$']

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Query for invoice children of a parent page."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'invoice' ORDER BY JSON_EXTRACT(metadata, '$.date') DESC, JSON_EXTRACT(metadata, '$.reference'), JSON_EXTRACT(metadata, '$.total') DESC",
            [parent_id]
        )
    
    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'table') -> List[Dict[str, Any]]:
        """
        Override to query for invoice pages with support for custom view types and grouping.
        Supports 'table', 'tile', and custom view types like 'd', 'v', '$', 'Md', 'Fd', etc.
        Custom view types return grouped data with 'groupBy' field when applicable.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return []
        
        children_data = []
        
        # Handle standard view types ('table' and 'tile')
        if view_type in ['table', 'tile']:
            query, params = cls._get_children_query(parent_id)
            results = gateway.conn.read(query, params)
            
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
                log(f"Loaded {len(children_data)} children for class 'invoice' (table format)")
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
                log(f"Loaded {len(children_data)} children for class 'invoice' (tile format)")
        else:
        # Handle custom view types (d, v, $, Md, Fd, etc.) - return grouped data
            debug(f"getChildrenOf: calling _get_browser_sort_query with parent_id={parent_id}, view_type='{view_type}'")
            query, params = cls._get_browser_sort_query(parent_id, view_type)
            debug(f"getChildrenOf: _get_browser_sort_query returned query: {query}")
            if not query:
                warn(f"Failed to build query for view_type '{view_type}'")
                trace_out()
                return []

            debug(f"getChildrenOf: executing query for view_type '{view_type}': {query}")
            results = gateway.conn.read(query, params)
            log(f"getChildrenOf: query returned {len(results) if results else 0} rows")

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
                        # Add groupBy field if present (for grouped views)
                        if 'groupBy' in row:
                            child_data['groupBy'] = str(row['groupBy']) if row['groupBy'] is not None else ''
                            debug(f"getChildrenOf: added groupBy '{child_data['groupBy']}' to child_data")
                        children_data.append(child_data)
            log(f"Loaded {len(children_data)} children for class 'invoice' (view_type: {view_type})")
        
        trace_out()
        return children_data
    
    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return data for invoice rows in table view."""
        trace_in()
        # Ensure derived value is calculated
        if hasattr(self, 'get_balanced'):
            self.get_balanced()
        
        # Calculate subtotal (total - tax - shipping)
        total = str(self.total or '')
        tax = str(self.tax or '')
        shipping = str(self.shipping or '')
        subtotal = DecimalMath.subtract(DecimalMath.subtract(total, tax), shipping)
        
        data = {
            "id": self.id,
            "name": self.name,
            "date": self.date if hasattr(self, 'date') else '',
            "reference": self.reference if hasattr(self, 'reference') else None,
            "subtotal": subtotal,
            "shipping": shipping,
            "tax": tax,
            "total": total,
            "text": self.text if hasattr(self, 'text') else '',
        }
        trace_out()
        return data
    
    def _get_display_name(self) -> str:
        """Return formatted display name for invoice, following legacy getNameString pattern."""
        if self.name:
            return self.name

        # Format like legacy: "Invoice #123 : Vendor Name"
        reference = self.reference or ""
        return f"Invoice #{self.id} : {reference}"

    def _get_child_row_field_type(self) -> str:
        """Return field type for invoice rows. Uses 'red' class if not balanced."""
        balanced = self.balanced if hasattr(self, 'balanced') else False
        return 'invoice_red' if not balanced else 'invoice'
    
    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize invoice metadata.
        Sets default values for invoice fields.
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
        
        # Initialize invoice fields with defaults
        page.set_metadata_value('date', '')
        page.set_metadata_value('reference', None)
        page.set_metadata_value('total', '')
        page.set_metadata_value('tax', '')
        page.set_metadata_value('shipping', '')
        page.set_metadata_value('balanced', False)
        
        # Also set attributes directly
        page.date = ''
        page.reference = None
        page.total = ''
        page.tax = ''
        page.shipping = ''
        page.balanced = False
        
        log(f"Initialized metadata for invoice page {new_page_id}")
        trace_out()
    
    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add invoice-specific fields to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['date'] = self.date if self.date else None
            badge_headers['page_summary']['reference'] = self.reference if self.reference else None
            badge_headers['page_summary']['total'] = f"{self.total:.2f}" if self.total else "0.00"
            badge_headers['page_summary']['tax'] = f"{self.tax:.2f}" if self.tax else "0.00"
            badge_headers['page_summary']['shipping'] = f"{self.shipping:.2f}" if self.shipping else "0.00"
            badge_headers['page_summary']['balanced'] = "✅" if self.balanced else "❌"
        else:
            warn(f"Invoice._add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers
    
    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """Invoice keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge
    
    def modify_invoice_info(self, date: str, reference: Optional[str]) -> bool:
        """Modify invoice date and reference information."""
        trace_in()
        self.set_metadata_value('date', date)
        self.set_metadata_value('reference', reference)
        self.date = date
        self.reference = reference
        self.flag_page_modification("invoice info changed")
        log(f"Modified invoice info for page {self.id}: date={date}, reference={reference}")
        trace_out()
        return not is_error()
    
    def modify_invoice_cost_breakdown(self, total: str, tax: str, shipping: str) -> bool:
        """Modify invoice cost breakdown (total, tax, shipping)."""
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
        Matches legacy Invoice::recalculateGeneratedValues().
        Uses DecimalMath for precise decimal calculations.
        """
        trace_in()

        # Query incoming transfers (transfers where transferTo = this invoice.id)
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

        # Query outgoing transfers (transfers where parent = this invoice.id)
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

        # Calculate balanced: (total + totalOutgoing - totalIncoming + totalIncomingFees) == 0
        invoice_total = str(self.total or '')
        balance = DecimalMath.add(DecimalMath.add(DecimalMath.subtract(invoice_total, total_incoming), total_outgoing), total_incoming_fees)
        balanced = DecimalMath.is_zero(balance)
        
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
        
        log(f"Recalculated generated values for invoice {self.id}: balanced={balanced}")
        
        trace_out()
        return not is_error()
    
    def _after_copy_page(self, new_page_id: int) -> None:
        """Hook called after copying an invoice page. Recalculates new page and new parent."""
        trace_in()
        # Recalculate the new page
        new_page = get_page(new_page_id)
        if new_page and hasattr(new_page, 'recalculateGeneratedValues'):
            new_page.recalculateGeneratedValues()
        # Recalculate the new parent (expense category)
        if self.parent:
            parent_page = get_page(self.parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        trace_out()
    
    def _after_move_page(self, old_parent_id: Optional[int], new_parent_id: int) -> None:
        """Hook called after moving an invoice page. Recalculates self, old parent, and new parent."""
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
        """Hook called before deleting an invoice page. Captures parent for later recalculation."""
        trace_in()
        # Store parent for use in _after_delete_page
        self._deleted_parent = self.parent
        trace_out()
    
    def _after_delete_page(self) -> None:
        """Hook called after deleting an invoice page. Recalculates old parent."""
        trace_in()
        # Recalculate old parent
        if hasattr(self, '_deleted_parent') and self._deleted_parent:
            parent_page = get_page(self._deleted_parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        trace_out()
    
    def get_page_data(self) -> Dict[str, Any]:
        """Override to add invoice-specific fields to full page data."""
        trace_in()
        data = super().get_page_data()
        data['date'] = self.date
        data['reference'] = self.reference
        data['total'] = self.total
        data['tax'] = self.tax
        data['shipping'] = self.shipping
        data['balanced'] = self.balanced
        trace_out()
        return data
    
    @classmethod
    def _get_browser_sort_query(cls, parent_id: int, view_type: str) -> tuple[str, list]:
        """
        Build query string for invoice browser sorting based on view_type and parent class.
        Returns query string and params list. Query should return 'id' and optionally 'groupBy' columns.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            trace_out()
            return ("", [])
        
        parent_page = get_page(parent_id)
        if not parent_page:
            warn(f"Parent page {parent_id} not found")
            trace_out()
            return ("", [])
        
        parent_class = parent_page.class_name if hasattr(parent_page, 'class_name') else parent_page.__class__.__name__.lower()
        debug(f"_get_browser_sort_query: parent_class detected as '{parent_class}'")
        log(f"_get_browser_sort_query: parent_id={parent_id}, parent_class='{parent_class}', view_type='{view_type}'")

        # Base WHERE clause
        base_where = "WHERE pages.class = 'invoice'"
        params = []
        
        debug(f"_get_browser_sort_query: checking parent_class '{parent_class}' for view_type '{view_type}'")

        if parent_class == 'fiscalPeriod':
            debug(f"_get_browser_sort_query: handling fiscalperiod parent")
            # Fiscal period parent - filter by date range
            if hasattr(parent_page, 'startDate') and hasattr(parent_page, 'endDate'):
                start_date = parent_page.startDate
                end_date = parent_page.endDate
                base_where += " AND JSON_EXTRACT(pages.metadata, '$.date') BETWEEN %s AND %s"
                params.extend([start_date, end_date])

            # Build query based on view_type
            if view_type in ['Md', 'Mv', 'M$']:
                # Group by month
                query = f"""
                    SELECT pages.id as id, 
                           MONTHNAME(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')), '%%Y-%%m-%%d')) as groupBy
                    FROM pages
                    {base_where}
                    ORDER BY MONTH(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')), '%%Y-%%m-%%d'))
                """
                if view_type == 'Md':
                    query += ", JSON_EXTRACT(pages.metadata, '$.date'), JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.total') DESC"
                elif view_type == 'Mv':
                    query += ", JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.date'), JSON_EXTRACT(pages.metadata, '$.total') DESC"
                else:  # M$
                    query += ", JSON_EXTRACT(pages.metadata, '$.total') DESC, JSON_EXTRACT(pages.metadata, '$.date'), JSON_EXTRACT(pages.metadata, '$.reference')"
                query += ", pages.id"
            elif view_type in ['Vd', 'V$']:
                # Group by reference (vendor)
                query = f"""
                    SELECT pages.id as id, 
                           COALESCE(JSON_EXTRACT(pages.metadata, '$.reference'), '') as groupBy
                    FROM pages
                    {base_where}
                    ORDER BY COALESCE(JSON_EXTRACT(pages.metadata, '$.reference'), '')
                """
                if view_type == 'Vd':
                    query += ", JSON_EXTRACT(pages.metadata, '$.date'), JSON_EXTRACT(pages.metadata, '$.total') DESC"
                else:  # V$
                    query += ", JSON_EXTRACT(pages.metadata, '$.total') DESC, JSON_EXTRACT(pages.metadata, '$.date')"
                query += ", pages.id"
            elif view_type in ['Cd', 'Cv', 'C$']:
                debug(f"_get_browser_sort_query: MATCHED category grouping condition for view_type '{view_type}'")
                # Group by category (parent expense category)
                query = f"""
                    SELECT pages.id as id, 
                           parent.name as groupBy
                    FROM pages
                    JOIN pages as parent ON pages.parent = parent.id
                    {base_where}
                    ORDER BY parent.name
                """
                if view_type == 'Cd':
                    query += ", JSON_EXTRACT(pages.metadata, '$.date'), JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.total') DESC"
                elif view_type == 'Cv':
                    query += ", JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.date'), JSON_EXTRACT(pages.metadata, '$.total') DESC"
                else:  # C$
                    query += ", JSON_EXTRACT(pages.metadata, '$.total') DESC, JSON_EXTRACT(pages.metadata, '$.date'), JSON_EXTRACT(pages.metadata, '$.reference')"
                query += ", pages.id"
            elif view_type == 'v':
                # Sort by reference (vendor), no grouping
                query = f"""
                    SELECT pages.id as id
                    FROM pages
                    {base_where}
                    ORDER BY COALESCE(JSON_EXTRACT(pages.metadata, '$.reference'), ''), 
                             JSON_EXTRACT(pages.metadata, '$.date'), 
                             JSON_EXTRACT(pages.metadata, '$.total') DESC,
                             pages.id
                """
            elif view_type == '$':
                # Sort by total, no grouping
                query = f"""
                    SELECT pages.id as id
                    FROM pages
                    {base_where}
                    ORDER BY JSON_EXTRACT(pages.metadata, '$.total') DESC,
                             JSON_EXTRACT(pages.metadata, '$.date'),
                             JSON_EXTRACT(pages.metadata, '$.reference'),
                             pages.id
                """
            else:  # 'd', 'auto', default
                debug(f"_get_browser_sort_query: NO MATCH - FALLING THROUGH to default date sorting for view_type '{view_type}' - NO GROUPING")
                # Sort by date, no grouping
                query = f"""
                    SELECT pages.id as id
                    FROM pages
                    {base_where}
                    ORDER BY JSON_EXTRACT(pages.metadata, '$.date'),
                             JSON_EXTRACT(pages.metadata, '$.reference'),
                             JSON_EXTRACT(pages.metadata, '$.total') DESC,
                             pages.id
                """
        elif parent_class == 'expenseCategory':
            debug(f"_get_browser_sort_query: handling expensecategory parent")
            # Expense category parent
            base_where += " AND pages.parent = %s"
            params.append(parent_id)

            debug(f"_get_browser_sort_query: base_where is now: {base_where}")
            debug(f"_get_browser_sort_query: about to check view_type conditions, view_type='{view_type}'")
            if view_type in ['Yd', 'Yv', 'Y$']:
                debug(f"_get_browser_sort_query: MATCHED year grouping condition for view_type '{view_type}'")
                # Group by year
                query = f"""
                    SELECT pages.id as id,
                           YEAR(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')), '%%Y-%%m-%%d')) as groupBy
                    FROM pages
                    {base_where}
                    ORDER BY YEAR(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')), '%%Y-%%m-%%d')) DESC
                """
                if view_type == 'Yd':
                    query += ", JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.total') DESC"
                elif view_type == 'Yv':
                    query += ", JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.total') DESC"
                else:  # Y$
                    query += ", JSON_EXTRACT(pages.metadata, '$.total') DESC, JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.reference')"
                query += ", pages.id"
                debug(f"_get_browser_sort_query: built year grouping query: {query}")
            elif view_type in ['Md', 'Mv', 'M$']:
                debug(f"_get_browser_sort_query: MATCHED month grouping condition for view_type '{view_type}'")
                # Group by month
                query = f"""
                    SELECT pages.id as id, 
                           CONCAT(MONTHNAME(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')), '%%Y-%%m-%%d')), ', ',
                                  YEAR(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')), '%%Y-%%m-%%d'))) as groupBy
                    FROM pages
                    {base_where}
                    ORDER BY YEAR(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')), '%%Y-%%m-%%d')) DESC,
                             MONTH(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')), '%%Y-%%m-%%d')) DESC
                """
                if view_type == 'Md':
                    query += ", JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.total') DESC"
                elif view_type == 'Mv':
                    query += ", JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.total') DESC"
                else:  # M$
                    query += ", JSON_EXTRACT(pages.metadata, '$.total') DESC, JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.reference')"
                query += ", pages.id"
            elif view_type in ['Fd', 'Fv', 'F$']:
                debug(f"_get_browser_sort_query: MATCHED fiscal period grouping condition for view_type '{view_type}'")
                # Group by fiscal period
                query = f"""
                    SELECT pages.id as id, 
                           CONCAT(YEAR(JSON_UNQUOTE(JSON_EXTRACT(fp.metadata, '$.startDate'))), ' (',
                                  MONTHNAME(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(fp.metadata, '$.startDate')), '%%Y-%%m-%%d')), ' - ',
                                  MONTHNAME(STR_TO_DATE(JSON_UNQUOTE(JSON_EXTRACT(fp.metadata, '$.endDate')), '%%Y-%%m-%%d')), ')') as groupBy
                    FROM pages
                    JOIN pages as fp ON JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')) >= JSON_UNQUOTE(JSON_EXTRACT(fp.metadata, '$.startDate'))
                                    AND JSON_UNQUOTE(JSON_EXTRACT(pages.metadata, '$.date')) <= JSON_UNQUOTE(JSON_EXTRACT(fp.metadata, '$.endDate'))
                                    AND fp.class = 'fiscalPeriod'
                    {base_where}
                    ORDER BY JSON_UNQUOTE(JSON_EXTRACT(fp.metadata, '$.startDate')) DESC
                """
                if view_type == 'Fd':
                    query += ", JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.total') DESC"
                elif view_type == 'Fv':
                    query += ", JSON_EXTRACT(pages.metadata, '$.reference'), JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.total') DESC"
                else:  # F$
                    query += ", JSON_EXTRACT(pages.metadata, '$.total') DESC, JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.reference')"
                query += ", pages.id"
            elif view_type in ['Vd', 'V$']:
                debug(f"_get_browser_sort_query: MATCHED vendor grouping condition for view_type '{view_type}'")
                # Group by reference (vendor)
                query = f"""
                    SELECT pages.id as id, 
                           COALESCE(JSON_EXTRACT(pages.metadata, '$.reference'), '') as groupBy
                    FROM pages
                    {base_where}
                    ORDER BY COALESCE(JSON_EXTRACT(pages.metadata, '$.reference'), '')
                """
                if view_type == 'Vd':
                    query += ", JSON_EXTRACT(pages.metadata, '$.date') DESC, JSON_EXTRACT(pages.metadata, '$.total') DESC"
                else:  # V$
                    query += ", JSON_EXTRACT(pages.metadata, '$.total') DESC, JSON_EXTRACT(pages.metadata, '$.date') DESC"
                query += ", pages.id"
            elif view_type == 'v':
                # Sort by reference (vendor), no grouping
                query = f"""
                    SELECT pages.id as id
                    FROM pages
                    {base_where}
                    ORDER BY COALESCE(JSON_EXTRACT(pages.metadata, '$.reference'), ''),
                             JSON_EXTRACT(pages.metadata, '$.date') DESC,
                             JSON_EXTRACT(pages.metadata, '$.total') DESC,
                             pages.id
                """
            elif view_type == '$':
                # Sort by total, no grouping
                query = f"""
                    SELECT pages.id as id
                    FROM pages
                    {base_where}
                    ORDER BY JSON_EXTRACT(pages.metadata, '$.total') DESC,
                             JSON_EXTRACT(pages.metadata, '$.date') DESC,
                             JSON_EXTRACT(pages.metadata, '$.reference'),
                             pages.id
                """
            else:  # 'd', 'auto', default
                # Sort by date, no grouping
                query = f"""
                    SELECT pages.id as id
                    FROM pages
                    {base_where}
                    ORDER BY JSON_EXTRACT(pages.metadata, '$.date') DESC,
                             JSON_EXTRACT(pages.metadata, '$.reference'),
                             JSON_EXTRACT(pages.metadata, '$.total') DESC,
                             pages.id
                """
        else:
            # Default parent (not fiscal period or expense category)
            base_where += " AND pages.parent = %s"
            params.append(parent_id)
            
            # Only support ungrouped views for default parent
            if view_type == 'v':
                query = f"""
                    SELECT pages.id as id
                    FROM pages
                    {base_where}
                    ORDER BY COALESCE(JSON_EXTRACT(pages.metadata, '$.reference'), ''),
                             JSON_EXTRACT(pages.metadata, '$.date') DESC,
                             JSON_EXTRACT(pages.metadata, '$.total') DESC,
                             pages.id
                """
            elif view_type == '$':
                query = f"""
                    SELECT pages.id as id
                    FROM pages
                    {base_where}
                    ORDER BY JSON_EXTRACT(pages.metadata, '$.total') DESC,
                             JSON_EXTRACT(pages.metadata, '$.date') DESC,
                             JSON_EXTRACT(pages.metadata, '$.reference'),
                             pages.id
                """
            else:  # 'd', 'auto', default
                query = f"""
                    SELECT pages.id as id
                    FROM pages
                    {base_where}
                    ORDER BY JSON_EXTRACT(pages.metadata, '$.date') DESC,
                             JSON_EXTRACT(pages.metadata, '$.reference'),
                             JSON_EXTRACT(pages.metadata, '$.total') DESC,
                             pages.id
                """
        
        trace_out()
        debug(f"_get_browser_sort_query: FINAL RETURN query='{query}', params={params}")
        return (query, params)
    
    @classmethod
    def get_section_html(cls, parent_id: int, section: str, view_type: str, class_name: Optional[str] = None) -> Optional[str]:
        """
        Custom HTML rendering for invoice children section content only.
        Returns HTML content (no header) with grouped tables based on view_type.
        Headers are now generated by get_section_header_links() hook during initial rendering.
        """
        trace_in()
        
        # Only handle 'children' section for 'invoice' class
        if section != 'children' or class_name != 'invoice':
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
        
        if (view_type == 'table'):
            view_type = 'd'

        # Get children data with grouping
        children_data = cls.getChildrenOf(parent_id, view_type)
        log(f"get_section_html: view_type={view_type}, children_count={len(children_data) if children_data else 0}")

        # Debug: check for groupBy fields
        if children_data:
            has_groupby = any('groupBy' in child for child in children_data)
            debug(f"get_section_html: has_groupBy={has_groupby}")
            if has_groupby:
                groupby_values = [child.get('groupBy', 'NONE') for child in children_data if 'groupBy' in child]
                debug(f"get_section_html: groupBy_values={groupby_values}")

        if not children_data:
            # Return empty content with proper wrapper
            page_id_str = str(parent_id)
            content_id = f"child_pages_invoice_{page_id_str}"
            trace_out()
            return f'<div id="{content_id}"></div>'

        # Build content HTML only
        page_id_str = str(parent_id)
        content_id = f"child_pages_invoice_{page_id_str}"
        
        # Check if this is a grouped view (has groupBy field)
        has_grouping = any('groupBy' in child for child in children_data)
        debug(f"get_section_html: has_grouping={has_grouping}")

        # Start the wrapper div (plain div for swapping, no class)
        html = f'<div id="{content_id}">'

        if has_grouping:
            # Render grouped tables
            current_group = None
            group_invoices: List[Dict[str, Any]] = []
            group_total_cost = ''
            group_total_shipping = ''
            group_total_tax = ''
            group_total_total = ''

            for child_data in children_data:
                group_by = child_data.get('groupBy', '')

                if group_by != current_group:
                    # Close previous group if exists
                    if current_group is not None and group_invoices:
                        html += cls._render_invoice_table(group_invoices, group_total_cost, group_total_shipping, group_total_tax, group_total_total)
                        html += '</div>'  # Close content div

                    # Start new group
                    current_group = group_by
                    group_invoices = []
                    group_total_cost = ''
                    group_total_shipping = ''
                    group_total_tax = ''
                    group_total_total = ''

                    # Add group header
                    debug(f"get_section_html: generating group header for '{current_group}'")
                    html += f'<div class="contentHeader">{current_group}</div>'
                    html += '<div class="content tableViewDiv">'

                # Add invoice to current group
                group_invoices.append(child_data)
                subtotal = str(child_data.get('subtotal', ''))
                shipping = str(child_data.get('shipping', ''))
                tax = str(child_data.get('tax', ''))
                total = str(child_data.get('total', ''))
                group_total_cost = DecimalMath.add(group_total_cost, subtotal)
                group_total_shipping = DecimalMath.add(group_total_shipping, shipping)
                group_total_tax = DecimalMath.add(group_total_tax, tax)
                group_total_total = DecimalMath.add(group_total_total, total)

            # Close last group
            if current_group is not None and group_invoices:
                html += cls._render_invoice_table(group_invoices, group_total_cost, group_total_shipping, group_total_tax, group_total_total)
                html += '</div>'  # Close content div
        else:
            # Render single ungrouped table
            total_cost = DecimalMath.sum([str(child.get('subtotal', '')) for child in children_data])
            total_shipping = DecimalMath.sum([str(child.get('shipping', '')) for child in children_data])
            total_tax = DecimalMath.sum([str(child.get('tax', '')) for child in children_data])
            total_total = DecimalMath.sum([str(child.get('total', '')) for child in children_data])
            html += '<div class="content tableViewDiv">'
            html += cls._render_invoice_table(children_data, total_cost, total_shipping, total_tax, total_total)
            html += '</div>'  # Close content div

        # Close the wrapper div
        html += '</div>'

        trace_out()
        return html
    
    @classmethod
    def _render_invoice_table(cls, invoices: List[Dict[str, Any]], total_cost: str, total_shipping: str, total_tax: str, total_total: str) -> str:
        """Render a single invoice table with header, rows, and footer."""
        html = '<table class="pageTableView invoiceTableView" cellpadding="0" cellspacing="0">'
        html += '<thead><tr>'
        html += '<th class="date">Date</th>'
        html += '<th class="reference">Reference</th>'
        html += '<th class="subtotal">cost</th>'
        html += '<th class="shipping">S+H</th>'
        html += '<th class="tax">tax</th>'
        html += '<th class="total">total</th>'
        html += '<th class="comments">Comments</th>'
        html += '</tr></thead><tbody>'
        
        row_ctr = 0
        for invoice_data in invoices:
            invoice_id = invoice_data.get('id')
            date = invoice_data.get('date', '')
            reference = invoice_data.get('reference') or ''
            subtotal = invoice_data.get('subtotal', 0.0)
            shipping = invoice_data.get('shipping', 0.0)
            tax = invoice_data.get('tax', 0.0)
            total = invoice_data.get('total', 0.0)
            text = invoice_data.get('text', '')
            field_type = invoice_data.get('field_type', 'invoice')
            is_red = 'invoice_red' in field_type
            
            row_class = ('red ' if is_red else '') + ('odd' if (row_ctr % 2) == 0 else 'even')
            html += f'<tr class="{row_class}">'
            html += f'<td class="date"><a href="{invoice_id}">{date}</a></td>'
            html += f'<td class="reference"><a href="{invoice_id}">{reference if reference else "&nbsp;"}</a></td>'
            html += f'<td class="subtotal"><a href="{invoice_id}">{DecimalMath.normalize(subtotal) if subtotal else "&nbsp;"}</a></td>'
            html += f'<td class="shipping">{DecimalMath.normalize(shipping) if shipping else "&nbsp;"}</td>'
            html += f'<td class="tax">{DecimalMath.normalize(tax) if tax else "&nbsp;"}</td>'
            html += f'<td class="total">{DecimalMath.normalize(total) if total else "&nbsp;"}</td>'
            html += f'<td class="comments">{text if text else "&nbsp;"}</td>'
            html += '</tr>'
            row_ctr += 1
        
        html += '</tbody><tfoot><tr class="totalFooter">'
        html += '<td>&nbsp;</td>'
        html += f'<td>{row_ctr} Invoices Total</td>'
        html += f'<td class="subtotal">{DecimalMath.normalize(total_cost) if total_cost else "&nbsp;"}</td>'
        html += f'<td class="shipping">{DecimalMath.normalize(total_shipping) if total_shipping else "&nbsp;"}</td>'
        html += f'<td class="tax">{DecimalMath.normalize(total_tax) if total_tax else "&nbsp;"}</td>'
        html += f'<td class="total">{DecimalMath.normalize(total_total) if total_total else "&nbsp;"}</td>'
        html += '<td class="comments">&nbsp;</td>'
        html += '</tr></tfoot></table>'
        
        return html


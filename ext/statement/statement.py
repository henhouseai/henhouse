"""
Statement page class for accounting system.
Extends Page with statement period and balance information.
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
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_statement_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('statement')
class Statement(OcrPage):
    """
    Statement page class for account statements with period dates and balances.
    """
    
    # Type annotations for metadata-extracted attributes
    startDate: str
    endDate: str
    openingBalance: str
    closingBalance: str
    interestEarned: str
    financeCharge: str
    totalIncoming: str
    totalOutgoing: str
    totalFees: str
    unaccountedMoney: str
    balanced: bool
    
    def __init__(self, id: int):
        """Initialize Statement by calling parent constructor."""
        super().__init__(id)
    
    def _after_metadata_extraction(self) -> None:
        """Override hook to set defaults for statement metadata fields and trigger recalculation if needed."""
        # Initialize metadata-extracted attributes with defaults
        if not hasattr(self, 'startDate'):
            self.startDate = ''
        if not hasattr(self, 'endDate'):
            self.endDate = ''
        if not hasattr(self, 'openingBalance'):
            self.openingBalance = ''
        if not hasattr(self, 'closingBalance'):
            self.closingBalance = ''
        if not hasattr(self, 'interestEarned'):
            self.interestEarned = ''
        if not hasattr(self, 'financeCharge'):
            self.financeCharge = ''
        if not hasattr(self, 'totalIncoming'):
            self.totalIncoming = ''
        if not hasattr(self, 'totalOutgoing'):
            self.totalOutgoing = ''
        if not hasattr(self, 'totalFees'):
            self.totalFees = ''
        if not hasattr(self, 'unaccountedMoney'):
            self.unaccountedMoney = ''
        if not hasattr(self, 'balanced'):
            self.balanced = False
        
        # Check if derived fields are at default values (indicating they haven't been calculated)
        # If so, trigger recalculation
        needs_recalculation = (
            self.totalIncoming == 0.0 and
            self.totalOutgoing == 0.0 and
            self.totalFees == 0.0 and
            self.unaccountedMoney == 0.0 and
            self.balanced == False
        )
        
        if needs_recalculation:
            # Store original values to check if they changed
            old_total_incoming = self.totalIncoming
            old_total_outgoing = self.totalOutgoing
            old_total_fees = self.totalFees
            old_unaccounted_money = self.unaccountedMoney
            old_balanced = self.balanced
            
            # Trigger recalculation
            self.recalculateGeneratedValues()
            
            # Check if values changed from defaults - if so, flag cache refresh
            if (self.totalIncoming != old_total_incoming or
                self.totalOutgoing != old_total_outgoing or
                self.totalFees != old_total_fees or
                self.unaccountedMoney != old_unaccounted_money or
                self.balanced != old_balanced):
                # Values changed, cache refresh already flagged by recalculateGeneratedValues
                pass
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Statements allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Statements allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Statements do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Statements can only contain fees and transfers."""
        return target_class in ['fee', 'transfer']
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Statements can only be inside accounts."""
        return parent_class == 'account'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for statement section headers."""
        return ['Statements']

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Query for statement children of a parent page."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'statement' ORDER BY JSON_EXTRACT(metadata, '$.startDate') DESC",
            [parent_id]
        )
    
    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'table') -> List[Dict[str, Any]]:
        """
        Override to query for statement pages with default table view.
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
            log(f"Loaded {len(children_data)} children for class 'statement' (table format)")
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
            log(f"Loaded {len(children_data)} children for class 'statement' (tile format)")
        
        trace_out()
        return children_data
    
    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return data for statement rows in table view."""
        trace_in()
        # Ensure derived values are calculated
        if hasattr(self, 'get_total_incoming'):
            self.get_total_incoming()
        if hasattr(self, 'get_total_outgoing'):
            self.get_total_outgoing()
        if hasattr(self, 'get_total_fees'):
            self.get_total_fees()
        if hasattr(self, 'get_unaccounted_money'):
            self.get_unaccounted_money()
        if hasattr(self, 'get_balanced'):
            self.get_balanced()
        
        data = {
            "id": self.id,
            "name": self.name,
            "startDate": self.startDate if hasattr(self, 'startDate') else '',
            "endDate": self.endDate if hasattr(self, 'endDate') else '',
            "openingBalance": self.openingBalance if hasattr(self, 'openingBalance') else 0.0,
            "totalIncoming": self.totalIncoming if hasattr(self, 'totalIncoming') else 0.0,
            "interestEarned": self.interestEarned if hasattr(self, 'interestEarned') else 0.0,
            "totalOutgoing": self.totalOutgoing if hasattr(self, 'totalOutgoing') else 0.0,
            "totalFees": self.totalFees if hasattr(self, 'totalFees') else 0.0,
            "financeCharge": self.financeCharge if hasattr(self, 'financeCharge') else 0.0,
            "unaccountedMoney": self.unaccountedMoney if hasattr(self, 'unaccountedMoney') else 0.0,
            "closingBalance": self.closingBalance if hasattr(self, 'closingBalance') else 0.0,
        }
        trace_out()
        return data
    
    def _get_child_row_field_type(self) -> str:
        """Return field type for statement rows. Uses 'red' class if not balanced."""
        balanced = self.balanced if hasattr(self, 'balanced') else False
        return 'statement_red' if not balanced else 'statement'
    
    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize statement metadata.
        Sets default values for all statement fields.
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
        
        # Initialize all statement fields with defaults
        page.set_metadata_value('startDate', '')
        page.set_metadata_value('endDate', '')
        page.set_metadata_value('openingBalance', '')
        page.set_metadata_value('closingBalance', '')
        page.set_metadata_value('interestEarned', '')
        page.set_metadata_value('financeCharge', '')
        page.set_metadata_value('totalIncoming', '')
        page.set_metadata_value('totalOutgoing', '')
        page.set_metadata_value('totalFees', '')
        page.set_metadata_value('unaccountedMoney', '')
        page.set_metadata_value('balanced', False)
        
        # Also set attributes directly
        page.startDate = ''
        page.endDate = ''
        page.openingBalance = ''
        page.closingBalance = ''
        page.interestEarned = ''
        page.financeCharge = ''
        page.totalIncoming = ''
        page.totalOutgoing = ''
        page.totalFees = ''
        page.unaccountedMoney = ''
        page.balanced = False
        
        log(f"Initialized metadata for statement page {new_page_id}")
        trace_out()
    
    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add statement-specific fields to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['startDate'] = self.startDate if self.startDate else None
            badge_headers['page_summary']['endDate'] = self.endDate if self.endDate else None
            badge_headers['page_summary']['openingBalance'] = f"{self.openingBalance:.2f}" if self.openingBalance else "0.00"
            badge_headers['page_summary']['closingBalance'] = f"{self.closingBalance:.2f}" if self.closingBalance else "0.00"
            badge_headers['page_summary']['interestEarned'] = f"{self.interestEarned:.2f}" if self.interestEarned else "0.00"
            badge_headers['page_summary']['financeCharge'] = f"{self.financeCharge:.2f}" if self.financeCharge else "0.00"
            badge_headers['page_summary']['totalIncoming'] = f"{self.totalIncoming:.2f}" if self.totalIncoming else "0.00"
            badge_headers['page_summary']['totalOutgoing'] = f"{self.totalOutgoing:.2f}" if self.totalOutgoing else "0.00"
            badge_headers['page_summary']['totalFees'] = f"{self.totalFees:.2f}" if self.totalFees else "0.00"
            badge_headers['page_summary']['unaccountedMoney'] = f"{self.unaccountedMoney:.2f}" if self.unaccountedMoney else "0.00"
            badge_headers['page_summary']['balanced'] = "✅" if self.balanced else "❌"
        else:
            warn(f"Statement._add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers
    
    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """Statement keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge
    
    def modify_statement_info(self, start_date: str, end_date: str, opening_balance: str, closing_balance: str) -> bool:
        """Modify statement period and balance information."""
        trace_in()
        self.set_metadata_value('startDate', start_date)
        self.set_metadata_value('endDate', end_date)
        self.set_metadata_value('openingBalance', opening_balance)
        self.set_metadata_value('closingBalance', closing_balance)
        self.startDate = start_date
        self.endDate = end_date
        self.openingBalance = opening_balance
        self.closingBalance = closing_balance
        self.flag_page_modification("statement info changed")
        log(f"Modified statement info for page {self.id}: startDate={start_date}, endDate={end_date}, openingBalance={opening_balance}, closingBalance={closing_balance}")
        trace_out()
        return not is_error()
    
    def modify_finance_info(self, interest_earned: str, finance_charge: str) -> bool:
        """Modify finance information (interest earned and finance charge)."""
        trace_in()
        self.set_metadata_value('interestEarned', interest_earned)
        self.set_metadata_value('financeCharge', finance_charge)
        self.interestEarned = interest_earned
        self.financeCharge = finance_charge
        self.flag_page_modification("finance info changed")
        log(f"Modified finance info for page {self.id}: interestEarned={interest_earned}, financeCharge={finance_charge}")
        trace_out()
        return not is_error()
    
    
    def recalculateGeneratedValues(self) -> bool:
        """
        Recalculate derived values: totalIncoming, totalOutgoing, totalFees, unaccountedMoney, balanced.
        Matches legacy Statement::recalculateGeneratedValues().
        Uses DecimalMath for precise decimal calculations.
        """
        trace_in()

        # Query incoming transfers (transfers where transferTo = this statement.id)
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
                    # Double-check transferTo is valid (not empty string or invalid)
                    if transfer_page.transferTo and transfer_page.transferTo == self.id:
                        incoming_amounts.append(str(transfer_page.amount or ''))
                        incoming_fees.append(str(transfer_page.fee or ''))

        # Query outgoing transfers (transfers where parent = this statement.id)
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

        # Query statement fees (fees where parent = this statement.id)
        fees_query = """
            SELECT id FROM pages
            WHERE parent = %s AND class = 'fee'
            ORDER BY JSON_EXTRACT(metadata, '$.date'), id
        """
        fees_results = self.gateway.conn.read(fees_query, [self.id])
        statement_fees = []
        if fees_results:
            for row in fees_results:
                fee_page = get_page(row['id'])
                if fee_page and hasattr(fee_page, 'fee'):
                    statement_fees.append(str(fee_page.fee or ''))

        # Calculate totals
        total_incoming = DecimalMath.sum(incoming_amounts)
        total_outgoing = DecimalMath.sum(outgoing_amounts)
        total_fees = DecimalMath.sum(incoming_fees + statement_fees)

        # Calculate unaccounted money using DecimalMath
        # Formula: closingBalance + totalOutgoing + totalFees + financeCharge - (openingBalance + totalIncoming + interestEarned)
        closing_balance = str(self.closingBalance or '')
        finance_charge = str(self.financeCharge or '')
        opening_balance = str(self.openingBalance or '')
        interest_earned = str(self.interestEarned or '')

        positive_sum = DecimalMath.sum([closing_balance, total_outgoing, total_fees, finance_charge])
        negative_sum = DecimalMath.sum([opening_balance, total_incoming, interest_earned])
        unaccounted_money = DecimalMath.subtract(positive_sum, negative_sum)

        # Calculate balanced (True if unaccountedMoney == 0)
        balanced = DecimalMath.is_zero(unaccounted_money)
        
        # Store original values to check if they changed
        old_total_incoming = getattr(self, 'totalIncoming', '')
        old_total_outgoing = getattr(self, 'totalOutgoing', '')
        old_total_fees = getattr(self, 'totalFees', '')
        old_unaccounted_money = getattr(self, 'unaccountedMoney', '')
        old_balanced = getattr(self, 'balanced', False)
        
        # Update metadata and attributes
        self.set_metadata_value('totalIncoming', total_incoming)
        self.set_metadata_value('totalOutgoing', total_outgoing)
        self.set_metadata_value('totalFees', total_fees)
        self.set_metadata_value('unaccountedMoney', unaccounted_money)
        self.set_metadata_value('balanced', balanced)
        
        self.totalIncoming = total_incoming
        self.totalOutgoing = total_outgoing
        self.totalFees = total_fees
        self.unaccountedMoney = unaccounted_money
        self.balanced = balanced
        
        # Check if values changed from defaults - if so, flag cache refresh
        if (self.totalIncoming != old_total_incoming or
            self.totalOutgoing != old_total_outgoing or
            self.totalFees != old_total_fees or
            self.unaccountedMoney != old_unaccounted_money or
            self.balanced != old_balanced):
            # Values changed, flag cache refresh
            self._flag_cache_refresh()
        
        log(f"Recalculated generated values for statement {self.id}: totalIncoming={total_incoming}, totalOutgoing={total_outgoing}, totalFees={total_fees}, unaccountedMoney={unaccounted_money}, balanced={balanced}")
        trace_out()
        return not is_error()
    
    def _after_copy_page(self, new_page_id: int) -> None:
        """Hook called after copying a statement page. Recalculates new page and new parent."""
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
        """Hook called after moving a statement page. Recalculates self, old parent, and new parent."""
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
        """Hook called before deleting a statement page. Captures parent for later recalculation."""
        trace_in()
        # Store parent for use in _after_delete_page
        self._deleted_parent = self.parent
        trace_out()
    
    def _after_delete_page(self) -> None:
        """Hook called after deleting a statement page. Recalculates old parent."""
        trace_in()
        # Recalculate old parent
        if hasattr(self, '_deleted_parent') and self._deleted_parent:
            parent_page = get_page(self._deleted_parent)
            if parent_page and hasattr(parent_page, 'recalculateGeneratedValues'):
                parent_page.recalculateGeneratedValues()
        trace_out()
    
    def _get_display_name(self) -> str:
        """Return formatted display name for statement, following legacy getNameString pattern."""
        if self.name:
            return self.name

        # Format like legacy: "Account Name 2023-01-01...2023-01-31"
        account_name = ""
        if self.parent:
            try:
                account_page = get_page(self.parent)
                if account_page:
                    account_name = account_page._get_display_name()
            except:
                pass

        date_range = ""
        if hasattr(self, 'startDate') and hasattr(self, 'endDate') and self.startDate and self.endDate:
            if self.startDate != '0000-00-00' and self.endDate != '0000-00-00':
                date_range = f" {self.startDate}...{self.endDate}"

        return f"{account_name}{date_range}"

    def get_page_data(self) -> Dict[str, Any]:
        """Override to add statement-specific fields to full page data."""
        trace_in()
        data = super().get_page_data()
        data['startDate'] = self.startDate
        data['endDate'] = self.endDate
        data['openingBalance'] = self.openingBalance
        data['closingBalance'] = self.closingBalance
        data['interestEarned'] = self.interestEarned
        data['financeCharge'] = self.financeCharge
        data['totalIncoming'] = self.totalIncoming
        data['totalOutgoing'] = self.totalOutgoing
        data['totalFees'] = self.totalFees
        data['unaccountedMoney'] = self.unaccountedMoney
        data['balanced'] = self.balanced
        trace_out()
        return data


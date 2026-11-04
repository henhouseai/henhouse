"""Migration tasks for migrating data from legacy database to new database."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
import re
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh_page.page_registry import get_page
from accounting.deploy.maint.legacy_db_connection import get_legacy_db_connection

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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


def migrate_pages(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate generic pages from legacy database.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of pages to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get pages that haven't been migrated yet (new_id is NULL)
        # Only get pages whose parent has been migrated (or is root page)
        # Only get pages that are not account-specific types
        cursor.execute("""
            SELECT p.id, p.parent, p.name, p.link, p.class, p.text
            FROM pages p
            LEFT JOIN pages parent ON parent.id = p.parent
            WHERE p.new_id IS NULL
            AND p.class NOT IN ('account', 'statement', 'transfer', 'fee', 'invoice', 'sale', 'fiscalPeriod', 'expenseCategory')
            AND (p.parent = 0 OR p.parent IS NULL OR parent.new_id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (batch_size,))
        
        pages = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for page_row in pages:
            try:
                legacy_id = page_row['id']
                parent_id = page_row['parent']
                name = page_row['name']
                class_name = page_row['class']
                text = page_row['text'] or ''
                
                # Get parent's new_id (query already ensures parent is migrated if parent != 0)
                new_parent_id = None
                if parent_id and parent_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (parent_id,))
                    parent_result = cursor.fetchone()
                    if parent_result and parent_result['new_id']:
                        new_parent_id = parent_result['new_id']
                    else:
                        # This shouldn't happen due to query filter, but handle it anyway
                        skipped += 1
                        debug(f"Skipping page {legacy_id} - parent {parent_id} not migrated (unexpected)")
                        continue
                
                # Create page in new database
                if new_parent_id:
                    parent_page = get_page(new_parent_id)
                    if not parent_page:
                        skipped += 1
                        debug(f"Skipping page {legacy_id} - parent page {new_parent_id} not found")
                        continue
                    new_page_id = parent_page.add_page(class_name, name)
                else:
                    # Root page (parent is 0 or None)
                    # Need to find root page in new database
                    if not gateway.conn:
                        skipped += 1
                        debug(f"Skipping page {legacy_id} - no database connection")
                        continue
                    root_pages = gateway.conn.read("SELECT id FROM pages WHERE parent = 0 LIMIT 1")
                    if not root_pages:
                        skipped += 1
                        debug(f"Skipping page {legacy_id} - no root page found in new database")
                        continue
                    root_page = get_page(root_pages[0]['id'])
                    if not root_page:
                        skipped += 1
                        continue
                    new_page_id = root_page.add_page(class_name, name)
                
                if not new_page_id:
                    errors.append(f"Failed to create page {legacy_id}")
                    continue
                
                # VERIFY: Load page back immediately to ensure it exists
                verification_page = get_page(new_page_id)
                if not verification_page:
                    error_msg = f"Failed to verify page {legacy_id} - page {new_page_id} not found after creation"
                    report_error("action", error_msg)
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # VERIFY: Check key fields match
                if verification_page.name != name:
                    error_msg = f"Failed to verify page {legacy_id} - name mismatch: expected '{name}', got '{verification_page.name}'"
                    report_error("action", error_msg)
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if verification_page.class_name != class_name:
                    error_msg = f"Failed to verify page {legacy_id} - class mismatch: expected '{class_name}', got '{verification_page.class_name}'"
                    report_error("action", error_msg)
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Note: Page text is NOT migrated here - it will be migrated separately after all pages exist
                # This is because page text can contain links to other pages that need to exist first
                
                # Only update legacy database after successful verification
                cursor.execute("UPDATE pages SET new_id = %s WHERE id = %s", (new_page_id, legacy_id))
                
                migrated += 1
                debug(f"Migrated and verified page {legacy_id} -> {new_page_id}")
                
            except Exception as e:
                error_msg = f"Error migrating page {page_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],  # Limit error details
            "has_more": len(pages) > 0  # Indicate if there are more pages to migrate
        }
        
        log(f"Migrated {migrated} pages, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_accounts(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate accounts from legacy database.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of accounts to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get accounts that haven't been migrated yet (new_id is NULL)
        # Only get accounts whose parent has been migrated (or is root page)
        cursor.execute("""
            SELECT p.id, p.parent, p.name, p.link, p.class
            FROM pages p
            LEFT JOIN pages parent ON parent.id = p.parent
            WHERE p.new_id IS NULL
            AND p.class = 'account'
            AND (p.parent = 0 OR p.parent IS NULL OR parent.new_id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (batch_size,))
        
        accounts = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for account_row in accounts:
            try:
                legacy_id = account_row['id']
                parent_id = account_row['parent']
                name = account_row['name']
                class_name = account_row['class']
                
                # Get account type from legacy accounts table
                cursor.execute("SELECT type FROM accounts WHERE id = %s LIMIT 1", (legacy_id,))
                account_result = cursor.fetchone()
                account_type = account_result['type'] if account_result and account_result.get('type') else 'cash'
                
                # Get parent's new_id (query already ensures parent is migrated if parent != 0)
                new_parent_id = None
                if parent_id and parent_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (parent_id,))
                    parent_result = cursor.fetchone()
                    if parent_result and parent_result['new_id']:
                        new_parent_id = parent_result['new_id']
                    else:
                        # This shouldn't happen due to query filter, but handle it anyway
                        skipped += 1
                        debug(f"Skipping account {legacy_id} - parent {parent_id} not migrated (unexpected)")
                        continue
                
                # Create account in new database
                if new_parent_id:
                    parent_page = get_page(new_parent_id)
                    if not parent_page:
                        skipped += 1
                        debug(f"Skipping account {legacy_id} - parent page {new_parent_id} not found")
                        continue
                    # Create account with type argument
                    # We'll need to set the type after creation since add_page doesn't accept type directly
                    new_account_id = parent_page.add_page(class_name, name)
                else:
                    # Root account (parent is 0 or None)
                    if not gateway.conn:
                        skipped += 1
                        debug(f"Skipping account {legacy_id} - no database connection")
                        continue
                    root_pages = gateway.conn.read("SELECT id FROM pages WHERE parent = 0 LIMIT 1")
                    if not root_pages:
                        skipped += 1
                        debug(f"Skipping account {legacy_id} - no root page found in new database")
                        continue
                    root_page = get_page(root_pages[0]['id'])
                    if not root_page:
                        skipped += 1
                        continue
                    new_account_id = root_page.add_page(class_name, name)
                
                if not new_account_id:
                    errors.append(f"Failed to create account {legacy_id}")
                    continue
                
                # VERIFY: Load account back immediately to ensure it exists
                verification_account = get_page(new_account_id)
                if not verification_account:
                    error_msg = f"Failed to verify account {legacy_id} - account {new_account_id} not found after creation"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # VERIFY: Check key fields match
                if verification_account.name != name:
                    error_msg = f"Failed to verify account {legacy_id} - name mismatch: expected '{name}', got '{verification_account.name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if verification_account.class_name != class_name:
                    error_msg = f"Failed to verify account {legacy_id} - class mismatch: expected '{class_name}', got '{verification_account.class_name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set account type (skip text - will be migrated separately)
                if hasattr(verification_account, 'modify_account_type'):
                    verification_account.modify_account_type(account_type)
                    # Re-verify after type update
                    verification_account = get_page(new_account_id)
                    if not verification_account:
                        error_msg = f"Failed to verify account {legacy_id} after type update - account {new_account_id} not found"
                        warn(error_msg)
                        errors.append(error_msg)
                        continue
                    
                    # Verify type was set correctly
                    if hasattr(verification_account, 'type') and verification_account.type != account_type:
                        error_msg = f"Failed to verify account {legacy_id} - type mismatch: expected '{account_type}', got '{verification_account.type}'"
                        warn(error_msg)
                        errors.append(error_msg)
                        continue
                
                # Only update legacy database after successful verification
                cursor.execute("UPDATE pages SET new_id = %s WHERE id = %s", (new_account_id, legacy_id))
                
                migrated += 1
                debug(f"Migrated and verified account {legacy_id} -> {new_account_id} (type: {account_type})")
                
            except Exception as e:
                error_msg = f"Error migrating account {account_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],  # Limit error details
            "has_more": len(accounts) == batch_size  # If we got a full batch, there might be more
        }
        
        log(f"Migrated {migrated} accounts, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_expense_categories(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate expense categories from legacy database.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of expense categories to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get expense categories that haven't been migrated yet (new_id is NULL)
        # Only get expense categories whose parent has been migrated
        cursor.execute("""
            SELECT p.id, p.parent, p.name, p.link, p.class
            FROM pages p
            LEFT JOIN pages parent ON parent.id = p.parent
            WHERE p.new_id IS NULL
            AND p.class = 'expenseCategory'
            AND (p.parent = 0 OR p.parent IS NULL OR parent.new_id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (batch_size,))
        
        expense_categories = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for expense_category_row in expense_categories:
            try:
                legacy_id = expense_category_row['id']
                parent_id = expense_category_row['parent']
                name = expense_category_row['name'] if expense_category_row['name'] else None
                class_name = expense_category_row['class']
                
                # Get parent's new_id (query already ensures parent is migrated if parent != 0)
                new_parent_id = None
                if parent_id and parent_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (parent_id,))
                    parent_result = cursor.fetchone()
                    if parent_result and parent_result['new_id']:
                        new_parent_id = parent_result['new_id']
                    else:
                        # This shouldn't happen due to query filter, but handle it anyway
                        skipped += 1
                        debug(f"Skipping expense category {legacy_id} - parent {parent_id} not migrated (unexpected)")
                        continue
                
                # Create expense category in new database
                if new_parent_id:
                    parent_page = get_page(new_parent_id)
                    if not parent_page:
                        skipped += 1
                        debug(f"Skipping expense category {legacy_id} - parent page {new_parent_id} not found")
                        continue
                    new_expense_category_id = parent_page.add_page(class_name, name)
                else:
                    # Root expense category (parent is 0 or None)
                    if not gateway.conn:
                        skipped += 1
                        debug(f"Skipping expense category {legacy_id} - no database connection")
                        continue
                    root_pages = gateway.conn.read("SELECT id FROM pages WHERE parent = 0 LIMIT 1")
                    if not root_pages:
                        skipped += 1
                        debug(f"Skipping expense category {legacy_id} - no root page found in new database")
                        continue
                    root_page = get_page(root_pages[0]['id'])
                    if not root_page:
                        skipped += 1
                        continue
                    new_expense_category_id = root_page.add_page(class_name, name)
                
                if not new_expense_category_id:
                    errors.append(f"Failed to create expense category {legacy_id}")
                    continue
                
                # VERIFY: Load expense category back immediately to ensure it exists
                verification_expense_category = get_page(new_expense_category_id)
                if not verification_expense_category:
                    error_msg = f"Failed to verify expense category {legacy_id} - expense category {new_expense_category_id} not found after creation"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # VERIFY: Check key fields match
                # Normalize names: treat empty string and None as equivalent
                expected_name = name if name else None
                actual_name = verification_expense_category.name if verification_expense_category.name else None
                if actual_name != expected_name:
                    error_msg = f"Failed to verify expense category {legacy_id} - name mismatch: expected '{name}', got '{verification_expense_category.name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if verification_expense_category.class_name != class_name:
                    error_msg = f"Failed to verify expense category {legacy_id} - class mismatch: expected '{class_name}', got '{verification_expense_category.class_name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Note: Expense categories have no special metadata fields to migrate
                # They're just simple pages with names
                
                # Only update legacy database after successful verification
                cursor.execute("UPDATE pages SET new_id = %s WHERE id = %s", (new_expense_category_id, legacy_id))
                
                migrated += 1
                debug(f"Migrated and verified expense category {legacy_id} -> {new_expense_category_id}")
                
            except Exception as e:
                error_msg = f"Error migrating expense category {expense_category_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],  # Limit error details
            "has_more": len(expense_categories) == batch_size  # If we got a full batch, there might be more
        }
        
        log(f"Migrated {migrated} expense categories, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_fiscal_periods(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate fiscal periods from legacy database.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of fiscal periods to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get fiscal periods that haven't been migrated yet (new_id is NULL)
        # Only get fiscal periods whose parent has been migrated
        cursor.execute("""
            SELECT p.id, p.parent, p.name, p.link, p.class
            FROM pages p
            LEFT JOIN pages parent ON parent.id = p.parent
            WHERE p.new_id IS NULL
            AND p.class = 'fiscalPeriod'
            AND (p.parent = 0 OR p.parent IS NULL OR parent.new_id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (batch_size,))
        
        fiscal_periods = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for fiscal_period_row in fiscal_periods:
            try:
                legacy_id = fiscal_period_row['id']
                parent_id = fiscal_period_row['parent']
                name = fiscal_period_row['name'] if fiscal_period_row['name'] else None
                class_name = fiscal_period_row['class']
                
                # Get fiscal period fields from legacy fiscalPeriods table
                cursor.execute("""
                    SELECT startDate, endDate
                    FROM fiscalPeriods
                    WHERE id = %s
                    LIMIT 1
                """, (legacy_id,))
                fiscal_period_result = cursor.fetchone()
                
                if not fiscal_period_result:
                    errors.append(f"Fiscal period {legacy_id} not found in fiscalPeriods table")
                    continue
                
                # Convert dates to strings (YYYY-MM-DD format)
                start_date_raw = fiscal_period_result.get('startDate')
                if start_date_raw:
                    if hasattr(start_date_raw, 'strftime'):
                        start_date = start_date_raw.strftime('%Y-%m-%d')
                    else:
                        start_date = str(start_date_raw)
                else:
                    start_date = ''
                
                end_date_raw = fiscal_period_result.get('endDate')
                if end_date_raw:
                    if hasattr(end_date_raw, 'strftime'):
                        end_date = end_date_raw.strftime('%Y-%m-%d')
                    else:
                        end_date = str(end_date_raw)
                else:
                    end_date = ''
                
                # Get parent's new_id (query already ensures parent is migrated if parent != 0)
                new_parent_id = None
                if parent_id and parent_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (parent_id,))
                    parent_result = cursor.fetchone()
                    if parent_result and parent_result['new_id']:
                        new_parent_id = parent_result['new_id']
                    else:
                        skipped += 1
                        debug(f"Skipping fiscal period {legacy_id} - parent {parent_id} not migrated (unexpected)")
                        continue
                
                # Create fiscal period in new database
                if new_parent_id:
                    parent_page = get_page(new_parent_id)
                    if not parent_page:
                        skipped += 1
                        debug(f"Skipping fiscal period {legacy_id} - parent page {new_parent_id} not found")
                        continue
                    new_fiscal_period_id = parent_page.add_page(class_name, name)
                else:
                    if not gateway.conn:
                        skipped += 1
                        debug(f"Skipping fiscal period {legacy_id} - no database connection")
                        continue
                    root_pages = gateway.conn.read("SELECT id FROM pages WHERE parent = 0 LIMIT 1")
                    if not root_pages:
                        skipped += 1
                        debug(f"Skipping fiscal period {legacy_id} - no root page found in new database")
                        continue
                    root_page = get_page(root_pages[0]['id'])
                    if not root_page:
                        skipped += 1
                        continue
                    new_fiscal_period_id = root_page.add_page(class_name, name)
                
                if not new_fiscal_period_id:
                    errors.append(f"Failed to create fiscal period {legacy_id}")
                    continue
                
                # VERIFY: Load fiscal period back immediately to ensure it exists
                verification_fiscal_period = get_page(new_fiscal_period_id)
                if not verification_fiscal_period:
                    error_msg = f"Failed to verify fiscal period {legacy_id} - fiscal period {new_fiscal_period_id} not found after creation"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # VERIFY: Check key fields match
                expected_name = name if name else None
                actual_name = verification_fiscal_period.name if verification_fiscal_period.name else None
                if actual_name != expected_name:
                    error_msg = f"Failed to verify fiscal period {legacy_id} - name mismatch: expected '{name}', got '{verification_fiscal_period.name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if verification_fiscal_period.class_name != class_name:
                    error_msg = f"Failed to verify fiscal period {legacy_id} - class mismatch: expected '{class_name}', got '{verification_fiscal_period.class_name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set fiscal period info (skip text - will be migrated separately)
                if hasattr(verification_fiscal_period, 'modify_fiscal_period_info'):
                    verification_fiscal_period.modify_fiscal_period_info(start_date, end_date)
                else:
                    error_msg = f"Fiscal period {legacy_id} doesn't have modify_fiscal_period_info method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Re-verify after updates
                verification_fiscal_period = get_page(new_fiscal_period_id)
                if not verification_fiscal_period:
                    error_msg = f"Failed to verify fiscal period {legacy_id} after field updates - fiscal period {new_fiscal_period_id} not found"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Verify fields were set correctly
                if hasattr(verification_fiscal_period, 'startDate') and verification_fiscal_period.startDate != start_date:
                    error_msg = f"Failed to verify fiscal period {legacy_id} - startDate mismatch: expected '{start_date}', got '{verification_fiscal_period.startDate}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if hasattr(verification_fiscal_period, 'endDate') and verification_fiscal_period.endDate != end_date:
                    error_msg = f"Failed to verify fiscal period {legacy_id} - endDate mismatch: expected '{end_date}', got '{verification_fiscal_period.endDate}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Only update legacy database after successful verification
                cursor.execute("UPDATE pages SET new_id = %s WHERE id = %s", (new_fiscal_period_id, legacy_id))
                
                migrated += 1
                debug(f"Migrated and verified fiscal period {legacy_id} -> {new_fiscal_period_id} (dates: {start_date} to {end_date})")
                
            except Exception as e:
                error_msg = f"Error migrating fiscal period {fiscal_period_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],
            "has_more": len(fiscal_periods) == batch_size
        }
        
        log(f"Migrated {migrated} fiscal periods, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_fees(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate fees from legacy database.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of fees to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get fees that haven't been migrated yet (new_id is NULL)
        # Only get fees whose parent (statement) has been migrated
        cursor.execute("""
            SELECT p.id, p.parent, p.name, p.link, p.class
            FROM pages p
            LEFT JOIN pages parent ON parent.id = p.parent
            WHERE p.new_id IS NULL
            AND p.class = 'fee'
            AND (p.parent = 0 OR p.parent IS NULL OR parent.new_id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (batch_size,))
        
        fees = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for fee_row in fees:
            try:
                legacy_id = fee_row['id']
                parent_id = fee_row['parent']
                name = fee_row['name'] if fee_row['name'] else None
                class_name = fee_row['class']
                
                # Get fee fields from legacy fees table
                cursor.execute("""
                    SELECT date, fee
                    FROM fees
                    WHERE id = %s
                    LIMIT 1
                """, (legacy_id,))
                fee_result = cursor.fetchone()
                
                if not fee_result:
                    errors.append(f"Fee {legacy_id} not found in fees table")
                    continue
                
                # Convert date to string (YYYY-MM-DD format)
                date_raw = fee_result.get('date')
                if date_raw:
                    if hasattr(date_raw, 'strftime'):
                        date = date_raw.strftime('%Y-%m-%d')
                    else:
                        date = str(date_raw)
                else:
                    date = ''
                
                fee_amount = float(fee_result.get('fee') or 0.0)
                
                # Get parent's new_id (query already ensures parent is migrated if parent != 0)
                new_parent_id = None
                if parent_id and parent_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (parent_id,))
                    parent_result = cursor.fetchone()
                    if parent_result and parent_result['new_id']:
                        new_parent_id = parent_result['new_id']
                    else:
                        skipped += 1
                        debug(f"Skipping fee {legacy_id} - parent {parent_id} not migrated (unexpected)")
                        continue
                
                # Create fee in new database
                if new_parent_id:
                    parent_page = get_page(new_parent_id)
                    if not parent_page:
                        skipped += 1
                        debug(f"Skipping fee {legacy_id} - parent page {new_parent_id} not found")
                        continue
                    new_fee_id = parent_page.add_page(class_name, name)
                else:
                    if not gateway.conn:
                        skipped += 1
                        debug(f"Skipping fee {legacy_id} - no database connection")
                        continue
                    root_pages = gateway.conn.read("SELECT id FROM pages WHERE parent = 0 LIMIT 1")
                    if not root_pages:
                        skipped += 1
                        debug(f"Skipping fee {legacy_id} - no root page found in new database")
                        continue
                    root_page = get_page(root_pages[0]['id'])
                    if not root_page:
                        skipped += 1
                        continue
                    new_fee_id = root_page.add_page(class_name, name)
                
                if not new_fee_id:
                    errors.append(f"Failed to create fee {legacy_id}")
                    continue
                
                # VERIFY: Load fee back immediately to ensure it exists
                verification_fee = get_page(new_fee_id)
                if not verification_fee:
                    error_msg = f"Failed to verify fee {legacy_id} - fee {new_fee_id} not found after creation"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # VERIFY: Check key fields match
                expected_name = name if name else None
                actual_name = verification_fee.name if verification_fee.name else None
                if actual_name != expected_name:
                    error_msg = f"Failed to verify fee {legacy_id} - name mismatch: expected '{name}', got '{verification_fee.name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if verification_fee.class_name != class_name:
                    error_msg = f"Failed to verify fee {legacy_id} - class mismatch: expected '{class_name}', got '{verification_fee.class_name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set fee info (skip text - will be migrated separately)
                if hasattr(verification_fee, 'modify_fee_info'):
                    verification_fee.modify_fee_info(fee_amount, date)
                else:
                    error_msg = f"Fee {legacy_id} doesn't have modify_fee_info method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Re-verify after updates
                verification_fee = get_page(new_fee_id)
                if not verification_fee:
                    error_msg = f"Failed to verify fee {legacy_id} after field updates - fee {new_fee_id} not found"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Verify fields were set correctly
                if hasattr(verification_fee, 'date') and verification_fee.date != date:
                    error_msg = f"Failed to verify fee {legacy_id} - date mismatch: expected '{date}', got '{verification_fee.date}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Only update legacy database after successful verification
                cursor.execute("UPDATE pages SET new_id = %s WHERE id = %s", (new_fee_id, legacy_id))
                
                migrated += 1
                debug(f"Migrated and verified fee {legacy_id} -> {new_fee_id} (date: {date}, fee: {fee_amount})")
                
            except Exception as e:
                error_msg = f"Error migrating fee {fee_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],
            "has_more": len(fees) == batch_size
        }
        
        log(f"Migrated {migrated} fees, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_transfers(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate transfers from legacy database.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of transfers to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get transfers that haven't been migrated yet (new_id is NULL)
        # Only get transfers whose parent has been migrated
        cursor.execute("""
            SELECT p.id, p.parent, p.name, p.link, p.class
            FROM pages p
            LEFT JOIN pages parent ON parent.id = p.parent
            WHERE p.new_id IS NULL
            AND p.class = 'transfer'
            AND (p.parent = 0 OR p.parent IS NULL OR parent.new_id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (batch_size,))
        
        transfers = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for transfer_row in transfers:
            try:
                legacy_id = transfer_row['id']
                parent_id = transfer_row['parent']
                name = transfer_row['name'] if transfer_row['name'] else None
                class_name = transfer_row['class']
                
                # Get transfer fields from legacy transfers table
                cursor.execute("""
                    SELECT date, amount, fee, transferTo
                    FROM transfers
                    WHERE id = %s
                    LIMIT 1
                """, (legacy_id,))
                transfer_result = cursor.fetchone()
                
                if not transfer_result:
                    errors.append(f"Transfer {legacy_id} not found in transfers table")
                    continue
                
                # Convert date to string (YYYY-MM-DD format)
                date_raw = transfer_result.get('date')
                if date_raw:
                    if hasattr(date_raw, 'strftime'):
                        date = date_raw.strftime('%Y-%m-%d')
                    else:
                        date = str(date_raw)
                else:
                    date = ''
                
                amount = float(transfer_result.get('amount') or 0.0)
                fee = float(transfer_result.get('fee') or 0.0)
                transfer_to_legacy_id = transfer_result.get('transferTo')
                
                # Get parent's new_id (query already ensures parent is migrated if parent != 0)
                new_parent_id = None
                if parent_id and parent_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (parent_id,))
                    parent_result = cursor.fetchone()
                    if parent_result and parent_result['new_id']:
                        new_parent_id = parent_result['new_id']
                    else:
                        skipped += 1
                        debug(f"Skipping transfer {legacy_id} - parent {parent_id} not migrated (unexpected)")
                        continue
                
                # Get transferTo's new_id (if transferTo is set)
                new_transfer_to_id = None
                if transfer_to_legacy_id and transfer_to_legacy_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (transfer_to_legacy_id,))
                    transfer_to_result = cursor.fetchone()
                    if transfer_to_result and transfer_to_result['new_id']:
                        new_transfer_to_id = transfer_to_result['new_id']
                        # Pre-verify that the target page exists in new system
                        target_page = get_page(new_transfer_to_id)
                        if not target_page:
                            skipped += 1
                            debug(f"Skipping transfer {legacy_id} - transferTo target {new_transfer_to_id} not found in new system")
                            continue
                    else:
                        skipped += 1
                        debug(f"Skipping transfer {legacy_id} - transferTo {transfer_to_legacy_id} not migrated yet")
                        continue
                
                # Create transfer in new database
                if new_parent_id:
                    parent_page = get_page(new_parent_id)
                    if not parent_page:
                        skipped += 1
                        debug(f"Skipping transfer {legacy_id} - parent page {new_parent_id} not found")
                        continue
                    new_transfer_id = parent_page.add_page(class_name, name)
                else:
                    if not gateway.conn:
                        skipped += 1
                        debug(f"Skipping transfer {legacy_id} - no database connection")
                        continue
                    root_pages = gateway.conn.read("SELECT id FROM pages WHERE parent = 0 LIMIT 1")
                    if not root_pages:
                        skipped += 1
                        debug(f"Skipping transfer {legacy_id} - no root page found in new database")
                        continue
                    root_page = get_page(root_pages[0]['id'])
                    if not root_page:
                        skipped += 1
                        continue
                    new_transfer_id = root_page.add_page(class_name, name)
                
                if not new_transfer_id:
                    errors.append(f"Failed to create transfer {legacy_id}")
                    continue
                
                # VERIFY: Load transfer back immediately to ensure it exists
                verification_transfer = get_page(new_transfer_id)
                if not verification_transfer:
                    error_msg = f"Failed to verify transfer {legacy_id} - transfer {new_transfer_id} not found after creation"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # VERIFY: Check key fields match
                expected_name = name if name else None
                actual_name = verification_transfer.name if verification_transfer.name else None
                if actual_name != expected_name:
                    error_msg = f"Failed to verify transfer {legacy_id} - name mismatch: expected '{name}', got '{verification_transfer.name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if verification_transfer.class_name != class_name:
                    error_msg = f"Failed to verify transfer {legacy_id} - class mismatch: expected '{class_name}', got '{verification_transfer.class_name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set transfer info (skip text - will be migrated separately)
                # modifier is 0 for migration (no adjustment needed)
                if hasattr(verification_transfer, 'modify_transfer_info'):
                    verification_transfer.modify_transfer_info(date, amount, 0.0, fee)
                else:
                    error_msg = f"Transfer {legacy_id} doesn't have modify_transfer_info method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set transfer target (if transferTo is set)
                if new_transfer_to_id:
                    if hasattr(verification_transfer, 'modify_target_info'):
                        verification_transfer.modify_target_info(new_transfer_to_id)
                    else:
                        error_msg = f"Transfer {legacy_id} doesn't have modify_target_info method"
                        warn(error_msg)
                        errors.append(error_msg)
                        continue
                
                # Re-verify after updates
                verification_transfer = get_page(new_transfer_id)
                if not verification_transfer:
                    error_msg = f"Failed to verify transfer {legacy_id} after field updates - transfer {new_transfer_id} not found"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Verify fields were set correctly
                if hasattr(verification_transfer, 'date') and verification_transfer.date != date:
                    error_msg = f"Failed to verify transfer {legacy_id} - date mismatch: expected '{date}', got '{verification_transfer.date}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if new_transfer_to_id:
                    if hasattr(verification_transfer, 'transferTo') and verification_transfer.transferTo != new_transfer_to_id:
                        error_msg = f"Failed to verify transfer {legacy_id} - transferTo mismatch: expected {new_transfer_to_id}, got {verification_transfer.transferTo}"
                        warn(error_msg)
                        errors.append(error_msg)
                        continue
                
                # Only update legacy database after successful verification
                cursor.execute("UPDATE pages SET new_id = %s WHERE id = %s", (new_transfer_id, legacy_id))
                
                migrated += 1
                debug(f"Migrated and verified transfer {legacy_id} -> {new_transfer_id} (date: {date}, amount: {amount}, transferTo: {new_transfer_to_id})")
                
            except Exception as e:
                error_msg = f"Error migrating transfer {transfer_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],
            "has_more": len(transfers) == batch_size
        }
        
        log(f"Migrated {migrated} transfers, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_invoices(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate invoices from legacy database.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of invoices to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get invoices that haven't been migrated yet (new_id is NULL)
        # Only get invoices whose parent (expense category) has been migrated
        cursor.execute("""
            SELECT p.id, p.parent, p.name, p.link, p.class
            FROM pages p
            LEFT JOIN pages parent ON parent.id = p.parent
            WHERE p.new_id IS NULL
            AND p.class = 'invoice'
            AND (p.parent = 0 OR p.parent IS NULL OR parent.new_id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (batch_size,))
        
        invoices = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for invoice_row in invoices:
            try:
                legacy_id = invoice_row['id']
                parent_id = invoice_row['parent']
                name = invoice_row['name'] if invoice_row['name'] else None
                class_name = invoice_row['class']
                
                # Get invoice fields from legacy invoices table
                cursor.execute("""
                    SELECT date, reference, total, tax, shipping
                    FROM invoices
                    WHERE id = %s
                    LIMIT 1
                """, (legacy_id,))
                invoice_result = cursor.fetchone()
                
                if not invoice_result:
                    errors.append(f"Invoice {legacy_id} not found in invoices table")
                    continue
                
                # Convert date to string (YYYY-MM-DD format)
                date_raw = invoice_result.get('date')
                if date_raw:
                    if hasattr(date_raw, 'strftime'):
                        date = date_raw.strftime('%Y-%m-%d')
                    else:
                        date = str(date_raw)
                else:
                    date = ''
                
                reference = invoice_result.get('reference') or None
                total = float(invoice_result.get('total') or 0.0)
                tax = float(invoice_result.get('tax') or 0.0)
                shipping = float(invoice_result.get('shipping') or 0.0)
                
                # Get parent's new_id (query already ensures parent is migrated if parent != 0)
                new_parent_id = None
                if parent_id and parent_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (parent_id,))
                    parent_result = cursor.fetchone()
                    if parent_result and parent_result['new_id']:
                        new_parent_id = parent_result['new_id']
                    else:
                        skipped += 1
                        debug(f"Skipping invoice {legacy_id} - parent {parent_id} not migrated (unexpected)")
                        continue
                
                # Create invoice in new database
                if new_parent_id:
                    parent_page = get_page(new_parent_id)
                    if not parent_page:
                        skipped += 1
                        debug(f"Skipping invoice {legacy_id} - parent page {new_parent_id} not found")
                        continue
                    new_invoice_id = parent_page.add_page(class_name, name)
                else:
                    if not gateway.conn:
                        skipped += 1
                        debug(f"Skipping invoice {legacy_id} - no database connection")
                        continue
                    root_pages = gateway.conn.read("SELECT id FROM pages WHERE parent = 0 LIMIT 1")
                    if not root_pages:
                        skipped += 1
                        debug(f"Skipping invoice {legacy_id} - no root page found in new database")
                        continue
                    root_page = get_page(root_pages[0]['id'])
                    if not root_page:
                        skipped += 1
                        continue
                    new_invoice_id = root_page.add_page(class_name, name)
                
                if not new_invoice_id:
                    errors.append(f"Failed to create invoice {legacy_id}")
                    continue
                
                # VERIFY: Load invoice back immediately to ensure it exists
                verification_invoice = get_page(new_invoice_id)
                if not verification_invoice:
                    error_msg = f"Failed to verify invoice {legacy_id} - invoice {new_invoice_id} not found after creation"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # VERIFY: Check key fields match
                expected_name = name if name else None
                actual_name = verification_invoice.name if verification_invoice.name else None
                if actual_name != expected_name:
                    error_msg = f"Failed to verify invoice {legacy_id} - name mismatch: expected '{name}', got '{verification_invoice.name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if verification_invoice.class_name != class_name:
                    error_msg = f"Failed to verify invoice {legacy_id} - class mismatch: expected '{class_name}', got '{verification_invoice.class_name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set invoice info (skip text - will be migrated separately)
                if hasattr(verification_invoice, 'modify_invoice_info'):
                    verification_invoice.modify_invoice_info(date, reference)
                else:
                    error_msg = f"Invoice {legacy_id} doesn't have modify_invoice_info method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set cost breakdown
                if hasattr(verification_invoice, 'modify_invoice_cost_breakdown'):
                    verification_invoice.modify_invoice_cost_breakdown(total, tax, shipping)
                else:
                    error_msg = f"Invoice {legacy_id} doesn't have modify_invoice_cost_breakdown method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Re-verify after updates
                verification_invoice = get_page(new_invoice_id)
                if not verification_invoice:
                    error_msg = f"Failed to verify invoice {legacy_id} after field updates - invoice {new_invoice_id} not found"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Verify fields were set correctly
                if hasattr(verification_invoice, 'date') and verification_invoice.date != date:
                    error_msg = f"Failed to verify invoice {legacy_id} - date mismatch: expected '{date}', got '{verification_invoice.date}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Only update legacy database after successful verification
                cursor.execute("UPDATE pages SET new_id = %s WHERE id = %s", (new_invoice_id, legacy_id))
                
                migrated += 1
                debug(f"Migrated and verified invoice {legacy_id} -> {new_invoice_id} (date: {date}, total: {total})")
                
            except Exception as e:
                error_msg = f"Error migrating invoice {invoice_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],
            "has_more": len(invoices) == batch_size
        }
        
        log(f"Migrated {migrated} invoices, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_sales(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate sales from legacy database.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of sales to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get sales that haven't been migrated yet (new_id is NULL)
        # Sales can be in root or under pages, so check if parent is migrated or is root
        cursor.execute("""
            SELECT p.id, p.parent, p.name, p.link, p.class
            FROM pages p
            LEFT JOIN pages parent ON parent.id = p.parent
            WHERE p.new_id IS NULL
            AND p.class = 'sale'
            AND (p.parent = 0 OR p.parent IS NULL OR parent.new_id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (batch_size,))
        
        sales = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for sale_row in sales:
            try:
                legacy_id = sale_row['id']
                parent_id = sale_row['parent']
                name = sale_row['name'] if sale_row['name'] else None
                class_name = sale_row['class']
                
                # Get sale fields from legacy sales table
                cursor.execute("""
                    SELECT date, receiptNum, saleType, customerName, address, city, state, postalCode, country, total, tax, shipping
                    FROM sales
                    WHERE id = %s
                    LIMIT 1
                """, (legacy_id,))
                sale_result = cursor.fetchone()
                
                # If no entry in sales table, use default values instead of erroring
                if not sale_result:
                    warn(f"Sale {legacy_id} not found in sales table - using default values")
                    # Use default values for all fields
                    date = ''
                    receipt_num = None
                    sale_type = 'retail'
                    customer_name = None
                    address = None
                    city = None
                    state = None
                    postal_code = None
                    country = None
                    total = 0.0
                    tax = 0.0
                    shipping = 0.0
                else:
                    # Convert date to string (YYYY-MM-DD format)
                    date_raw = sale_result.get('date')
                    if date_raw:
                        if hasattr(date_raw, 'strftime'):
                            date = date_raw.strftime('%Y-%m-%d')
                        else:
                            date = str(date_raw)
                    else:
                        date = ''
                    
                    receipt_num = sale_result.get('receiptNum') or None
                    sale_type = sale_result.get('saleType') or 'retail'
                    customer_name = sale_result.get('customerName') or None
                    address = sale_result.get('address') or None
                    city = sale_result.get('city') or None
                    state = sale_result.get('state') or None
                    postal_code = sale_result.get('postalCode') or None
                    country = sale_result.get('country') or None
                    total = float(sale_result.get('total') or 0.0)
                    tax = float(sale_result.get('tax') or 0.0)
                    shipping = float(sale_result.get('shipping') or 0.0)
                
                # Get parent's new_id (query already ensures parent is migrated if parent != 0)
                new_parent_id = None
                if parent_id and parent_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (parent_id,))
                    parent_result = cursor.fetchone()
                    if parent_result and parent_result['new_id']:
                        new_parent_id = parent_result['new_id']
                    else:
                        skipped += 1
                        debug(f"Skipping sale {legacy_id} - parent {parent_id} not migrated (unexpected)")
                        continue
                
                # Create sale in new database
                if new_parent_id:
                    parent_page = get_page(new_parent_id)
                    if not parent_page:
                        skipped += 1
                        debug(f"Skipping sale {legacy_id} - parent page {new_parent_id} not found")
                        continue
                    new_sale_id = parent_page.add_page(class_name, name)
                else:
                    if not gateway.conn:
                        skipped += 1
                        debug(f"Skipping sale {legacy_id} - no database connection")
                        continue
                    root_pages = gateway.conn.read("SELECT id FROM pages WHERE parent = 0 LIMIT 1")
                    if not root_pages:
                        skipped += 1
                        debug(f"Skipping sale {legacy_id} - no root page found in new database")
                        continue
                    root_page = get_page(root_pages[0]['id'])
                    if not root_page:
                        skipped += 1
                        continue
                    new_sale_id = root_page.add_page(class_name, name)
                
                if not new_sale_id:
                    errors.append(f"Failed to create sale {legacy_id}")
                    continue
                
                # VERIFY: Load sale back immediately to ensure it exists
                verification_sale = get_page(new_sale_id)
                if not verification_sale:
                    error_msg = f"Failed to verify sale {legacy_id} - sale {new_sale_id} not found after creation"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # VERIFY: Check key fields match
                expected_name = name if name else None
                actual_name = verification_sale.name if verification_sale.name else None
                if actual_name != expected_name:
                    error_msg = f"Failed to verify sale {legacy_id} - name mismatch: expected '{name}', got '{verification_sale.name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if verification_sale.class_name != class_name:
                    error_msg = f"Failed to verify sale {legacy_id} - class mismatch: expected '{class_name}', got '{verification_sale.class_name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set sale info (skip text - will be migrated separately)
                if hasattr(verification_sale, 'modify_sale_info'):
                    verification_sale.modify_sale_info(date, receipt_num, sale_type)
                else:
                    error_msg = f"Sale {legacy_id} doesn't have modify_sale_info method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set customer info
                if hasattr(verification_sale, 'modify_customer_info'):
                    verification_sale.modify_customer_info(customer_name, address, city, state, postal_code, country)
                else:
                    error_msg = f"Sale {legacy_id} doesn't have modify_customer_info method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set cost breakdown
                if hasattr(verification_sale, 'modify_sale_cost_breakdown'):
                    verification_sale.modify_sale_cost_breakdown(total, tax, shipping)
                else:
                    error_msg = f"Sale {legacy_id} doesn't have modify_sale_cost_breakdown method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Re-verify after updates
                verification_sale = get_page(new_sale_id)
                if not verification_sale:
                    error_msg = f"Failed to verify sale {legacy_id} after field updates - sale {new_sale_id} not found"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Verify fields were set correctly
                if hasattr(verification_sale, 'date') and verification_sale.date != date:
                    error_msg = f"Failed to verify sale {legacy_id} - date mismatch: expected '{date}', got '{verification_sale.date}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Only update legacy database after successful verification
                cursor.execute("UPDATE pages SET new_id = %s WHERE id = %s", (new_sale_id, legacy_id))
                
                migrated += 1
                debug(f"Migrated and verified sale {legacy_id} -> {new_sale_id} (date: {date}, saleType: {sale_type}, total: {total})")
                
            except Exception as e:
                error_msg = f"Error migrating sale {sale_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],
            "has_more": len(sales) == batch_size
        }
        
        log(f"Migrated {migrated} sales, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_statements(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate statements from legacy database.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of statements to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get statements that haven't been migrated yet (new_id is NULL)
        # Only get statements whose parent (account) has been migrated
        cursor.execute("""
            SELECT p.id, p.parent, p.name, p.link, p.class
            FROM pages p
            LEFT JOIN pages parent ON parent.id = p.parent
            WHERE p.new_id IS NULL
            AND p.class = 'statement'
            AND (p.parent = 0 OR p.parent IS NULL OR parent.new_id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (batch_size,))
        
        statements = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for statement_row in statements:
            try:
                legacy_id = statement_row['id']
                parent_id = statement_row['parent']
                name = statement_row['name'] if statement_row['name'] else None
                class_name = statement_row['class']
                
                # Get statement fields from legacy statements table
                cursor.execute("""
                    SELECT startDate, endDate, openingBalance, closingBalance, interestEarned, financeCharge
                    FROM statements
                    WHERE id = %s
                    LIMIT 1
                """, (legacy_id,))
                statement_result = cursor.fetchone()
                
                if not statement_result:
                    errors.append(f"Statement {legacy_id} not found in statements table")
                    continue
                
                # Convert dates to strings (YYYY-MM-DD format)
                # MySQL dates come back as date objects, need to convert to strings
                start_date_raw = statement_result.get('startDate')
                if start_date_raw:
                    if hasattr(start_date_raw, 'strftime'):
                        # It's a date/datetime object
                        start_date = start_date_raw.strftime('%Y-%m-%d')
                    else:
                        # It's already a string
                        start_date = str(start_date_raw)
                else:
                    start_date = ''
                
                end_date_raw = statement_result.get('endDate')
                if end_date_raw:
                    if hasattr(end_date_raw, 'strftime'):
                        # It's a date/datetime object
                        end_date = end_date_raw.strftime('%Y-%m-%d')
                    else:
                        # It's already a string
                        end_date = str(end_date_raw)
                else:
                    end_date = ''
                opening_balance = float(statement_result.get('openingBalance') or 0.0)
                closing_balance = float(statement_result.get('closingBalance') or 0.0)
                interest_earned = float(statement_result.get('interestEarned') or 0.0)
                finance_charge = float(statement_result.get('financeCharge') or 0.0)
                
                # Get parent's new_id (query already ensures parent is migrated if parent != 0)
                new_parent_id = None
                if parent_id and parent_id != 0:
                    cursor.execute("SELECT new_id FROM pages WHERE id = %s", (parent_id,))
                    parent_result = cursor.fetchone()
                    if parent_result and parent_result['new_id']:
                        new_parent_id = parent_result['new_id']
                    else:
                        # This shouldn't happen due to query filter, but handle it anyway
                        skipped += 1
                        debug(f"Skipping statement {legacy_id} - parent {parent_id} not migrated (unexpected)")
                        continue
                
                # Create statement in new database
                if new_parent_id:
                    parent_page = get_page(new_parent_id)
                    if not parent_page:
                        skipped += 1
                        debug(f"Skipping statement {legacy_id} - parent page {new_parent_id} not found")
                        continue
                    new_statement_id = parent_page.add_page(class_name, name)
                else:
                    # Root statement (parent is 0 or None) - shouldn't happen for statements, but handle it
                    if not gateway.conn:
                        skipped += 1
                        debug(f"Skipping statement {legacy_id} - no database connection")
                        continue
                    root_pages = gateway.conn.read("SELECT id FROM pages WHERE parent = 0 LIMIT 1")
                    if not root_pages:
                        skipped += 1
                        debug(f"Skipping statement {legacy_id} - no root page found in new database")
                        continue
                    root_page = get_page(root_pages[0]['id'])
                    if not root_page:
                        skipped += 1
                        continue
                    new_statement_id = root_page.add_page(class_name, name)
                
                if not new_statement_id:
                    errors.append(f"Failed to create statement {legacy_id}")
                    continue
                
                # VERIFY: Load statement back immediately to ensure it exists
                verification_statement = get_page(new_statement_id)
                if not verification_statement:
                    error_msg = f"Failed to verify statement {legacy_id} - statement {new_statement_id} not found after creation"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # VERIFY: Check key fields match
                # Normalize names: treat empty string and None as equivalent
                expected_name = name if name else None
                actual_name = verification_statement.name if verification_statement.name else None
                if actual_name != expected_name:
                    error_msg = f"Failed to verify statement {legacy_id} - name mismatch: expected '{name}', got '{verification_statement.name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if verification_statement.class_name != class_name:
                    error_msg = f"Failed to verify statement {legacy_id} - class mismatch: expected '{class_name}', got '{verification_statement.class_name}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set statement info (skip text - will be migrated separately)
                if hasattr(verification_statement, 'modify_statement_info'):
                    verification_statement.modify_statement_info(start_date, end_date, opening_balance, closing_balance)
                else:
                    error_msg = f"Statement {legacy_id} doesn't have modify_statement_info method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Set finance info
                if hasattr(verification_statement, 'modify_finance_info'):
                    verification_statement.modify_finance_info(interest_earned, finance_charge)
                else:
                    error_msg = f"Statement {legacy_id} doesn't have modify_finance_info method"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Re-verify after updates
                verification_statement = get_page(new_statement_id)
                if not verification_statement:
                    error_msg = f"Failed to verify statement {legacy_id} after field updates - statement {new_statement_id} not found"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Verify fields were set correctly
                if hasattr(verification_statement, 'startDate') and verification_statement.startDate != start_date:
                    error_msg = f"Failed to verify statement {legacy_id} - startDate mismatch: expected '{start_date}', got '{verification_statement.startDate}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                if hasattr(verification_statement, 'endDate') and verification_statement.endDate != end_date:
                    error_msg = f"Failed to verify statement {legacy_id} - endDate mismatch: expected '{end_date}', got '{verification_statement.endDate}'"
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Only update legacy database after successful verification
                cursor.execute("UPDATE pages SET new_id = %s WHERE id = %s", (new_statement_id, legacy_id))
                
                migrated += 1
                debug(f"Migrated and verified statement {legacy_id} -> {new_statement_id} (dates: {start_date} to {end_date})")
                
            except Exception as e:
                error_msg = f"Error migrating statement {statement_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],  # Limit error details
            "has_more": len(statements) == batch_size  # If we got a full batch, there might be more
        }
        
        log(f"Migrated {migrated} statements, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Statement migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_text(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate page text from legacy database.
    
    Special migration phase for migrating page text content.
    This is not a class-based migration, but a special content migration.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of pages to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get pages that need text migration:
        # - migration_status = 2 (images migrated, ready for text)
        # - Have text (text IS NOT NULL AND text != '')
        # - Have been migrated to new database (new_id IS NOT NULL)
        cursor.execute("""
            SELECT id, new_id, text
            FROM pages
            WHERE migration_status = 2
            AND text IS NOT NULL
            AND text != ''
            AND new_id IS NOT NULL
            ORDER BY id
            LIMIT %s
        """, (batch_size,))
        
        pages = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for page_row in pages:
            try:
                legacy_page_id = page_row['id']
                new_page_id = page_row['new_id']
                legacy_text = page_row['text'] or ''
                
                if not new_page_id:
                    skipped += 1
                    debug(f"Skipping page {legacy_page_id} - no new_id mapping")
                    continue
                
                # Step 1: Collect all replacements needed
                replacements = []
                
                # Query imageLinks table for image replacements
                cursor.execute("""
                    SELECT resolution_id
                    FROM imageLinks
                    WHERE id = %s
                """, (legacy_page_id,))
                
                image_links = cursor.fetchall()
                for image_link_row in image_links:
                    legacy_image_id = image_link_row['resolution_id']
                    if not legacy_image_id:
                        continue
                    
                    # Map legacy image ID → new image ID
                    cursor.execute("""
                        SELECT new_id
                        FROM images
                        WHERE id = %s
                    """, (legacy_image_id,))
                    
                    image_result = cursor.fetchone()
                    if image_result and image_result['new_id']:
                        new_image_id = image_result['new_id']
                        replacements.append((legacy_image_id, new_image_id, 'image'))
                        debug(f"Image replacement: {legacy_image_id} -> {new_image_id}")
                    else:
                        error_msg = f"Image {legacy_image_id} has no new_id mapping for page {legacy_page_id}"
                        report_error("action", error_msg)
                        warn(error_msg)
                
                # Query links table for numeric page link replacements
                cursor.execute("""
                    SELECT link, resolution_id
                    FROM links
                    WHERE id = %s
                """, (legacy_page_id,))
                
                page_links = cursor.fetchall()
                for link_row in page_links:
                    link = link_row['link']
                    resolution_id = link_row['resolution_id']
                    
                    # Only process if link is numeric (matches resolution_id)
                    if link and resolution_id and str(link).isdigit() and int(link) == resolution_id:
                        legacy_target_page_id = resolution_id
                        
                        # Map legacy page ID → new page ID
                        cursor.execute("""
                            SELECT new_id
                            FROM pages
                            WHERE id = %s
                        """, (legacy_target_page_id,))
                        
                        page_result = cursor.fetchone()
                        if page_result and page_result['new_id']:
                            new_target_page_id = page_result['new_id']
                            replacements.append((legacy_target_page_id, new_target_page_id, 'page_numeric'))
                            debug(f"Page link replacement: {legacy_target_page_id} -> {new_target_page_id}")
                        else:
                            debug(f"Page {legacy_target_page_id} has no new_id mapping (may not be migrated yet)")
                    # If link is text-based, skip (name-based links stay the same)
                
                # Step 2: Get legacy page text (already have it: legacy_text)
                text_buffer = legacy_text
                
                # Step 3: Apply all replacements to buffer
                for legacy_id, new_id, replacement_type in replacements:
                    if replacement_type == 'image':
                        # Search pattern: exactly {{{<legacy_image_id>}}}
                        # Replacement: {{<new_image_id>}}
                        # Use regex with word boundaries to match exactly 3 braces + ID + 3 braces
                        # Pattern: \{\{\{<id>\}\}\}
                        search_pattern = r'\{\{\{' + re.escape(str(legacy_id)) + r'\}\}\}'
                        replacement = '{{' + str(new_id) + '}}'
                        text_buffer = re.sub(search_pattern, replacement, text_buffer)
                        debug(f"Applied image replacement: {legacy_id} -> {new_id}")
                    
                    elif replacement_type == 'page_numeric':
                        # Search pattern: [<legacy_page_id>] (single square bracket)
                        # Replacement: [<new_page_id>]
                        search_pattern_brackets = r'\[' + re.escape(str(legacy_id)) + r'\]'
                        replacement_brackets = '[' + str(new_id) + ']'
                        text_buffer = re.sub(search_pattern_brackets, replacement_brackets, text_buffer)
                        
                        # Search pattern: {<legacy_page_id>} (single brace)
                        # Replacement: {<new_page_id>}
                        search_pattern_braces = r'\{' + re.escape(str(legacy_id)) + r'\}'
                        replacement_braces = '{' + str(new_id) + '}'
                        text_buffer = re.sub(search_pattern_braces, replacement_braces, text_buffer)
                        
                        debug(f"Applied page link replacement: {legacy_id} -> {new_id}")
                
                # Step 4: Set converted text
                new_page = get_page(new_page_id)
                if not new_page:
                    error_msg = f"Failed to load new page {new_page_id} for legacy page {legacy_page_id}"
                    report_error("action", error_msg)
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Call modify_text() which will validate and update links/image_links tables
                if not new_page.modify_text(text_buffer):
                    error_msg = f"Failed to modify text for page {legacy_page_id} (new_id: {new_page_id})"
                    report_error("action", error_msg)
                    warn(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Update migration_status to 3 (text migrated)
                cursor.execute("""
                    UPDATE pages
                    SET migration_status = 3
                    WHERE id = %s
                """, (legacy_page_id,))
                
                migrated += 1
                debug(f"Migrated text for page {legacy_page_id} -> {new_page_id}")
                
            except Exception as e:
                error_msg = f"Error migrating text for page {page_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
        
        legacy_conn.commit()
        
        # Check if there are more pages to migrate
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM pages
            WHERE migration_status = 2
            AND text IS NOT NULL
            AND text != ''
            AND new_id IS NOT NULL
        """)
        
        count_result = cursor.fetchone()
        has_more = (count_result['count'] if count_result else 0) > 0
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],  # Limit error details
            "has_more": has_more
        }
        
        log(f"Migrated text for {migrated} pages, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_no_images(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Mark pages with no images as ready for next phase.
    
    One-shot operation that sets all pages with migration_status = 1
    and no images to migration_status = 2.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Not used (processes all at once)
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Update all pages with migration_status = 1 that have no images
        cursor.execute("""
            UPDATE pages p
            LEFT JOIN images i ON i.parent = p.id
            SET p.migration_status = 2
            WHERE p.migration_status = 1
            AND i.id IS NULL
        """)
        
        pages_updated = cursor.rowcount
        legacy_conn.commit()
        
        log(f"Set {pages_updated} pages with no images to status 2")
        
        trace_out()
        return {
            "migrated": pages_updated,
            "skipped": 0,
            "errors": 0,
            "error_details": [],
            "has_more": False,
            "message": f"Updated {pages_updated} pages with no images"
        }
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_no_text(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Mark pages with no text as ready for next phase.
    
    One-shot operation that sets all pages with migration_status = 2
    and no text to migration_status = 3.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Not used (processes all at once)
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Update all pages with migration_status = 2 that have no text
        cursor.execute("""
            UPDATE pages
            SET migration_status = 3
            WHERE migration_status = 2
            AND (text IS NULL OR text = '')
        """)
        
        pages_updated = cursor.rowcount
        legacy_conn.commit()
        
        log(f"Set {pages_updated} pages with no text to status 3")
        
        trace_out()
        return {
            "migrated": pages_updated,
            "skipped": 0,
            "errors": 0,
            "error_details": [],
            "has_more": False,
            "message": f"Updated {pages_updated} pages with no text"
        }
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_no_calc(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Mark pages with no calculated values as ready for next phase.
    
    One-shot operation that sets all pages with migration_status = 3
    that are NOT statement, invoice, or sale classes to migration_status = 4.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Not used (processes all at once)
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Update all pages with migration_status = 3 that are NOT statement/invoice/sale
        cursor.execute("""
            UPDATE pages
            SET migration_status = 4
            WHERE migration_status = 3
            AND class NOT IN ('statement', 'invoice', 'sale')
        """)
        
        pages_updated = cursor.rowcount
        legacy_conn.commit()
        
        log(f"Set {pages_updated} pages with no calculated values to status 4")
        
        trace_out()
        return {
            "migrated": pages_updated,
            "skipped": 0,
            "errors": 0,
            "error_details": [],
            "has_more": False,
            "message": f"Updated {pages_updated} pages with no calculated values"
        }
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_calc(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Recalculate generated values for Statement, Invoice, and Sale pages.
    
    Processes pages with migration_status = 3 that are statement, invoice, or sale classes.
    Calls recalculateGeneratedValues() on each page and updates migration_status to 4 (success) or -4 (error).
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Number of pages to process per batch
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        cursor = legacy_conn.cursor()
        
        # Get pages that need calculated values migration:
        # - migration_status = 3 (text migrated, ready for calc)
        # - Class is statement, invoice, or sale
        # - Have been migrated to new database (new_id IS NOT NULL)
        cursor.execute("""
            SELECT id, new_id, class
            FROM pages
            WHERE migration_status = 3
            AND class IN ('statement', 'invoice', 'sale')
            AND new_id IS NOT NULL
            ORDER BY id
            LIMIT %s
        """, (batch_size,))
        
        pages = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = []
        
        for page_row in pages:
            try:
                legacy_page_id = page_row['id']
                new_page_id = page_row['new_id']
                page_class = page_row['class']
                
                if not new_page_id:
                    skipped += 1
                    debug(f"Skipping page {legacy_page_id} - no new_id mapping")
                    continue
                
                # Load the new page
                new_page = get_page(new_page_id)
                if not new_page:
                    error_msg = f"Failed to load new page {new_page_id} for legacy page {legacy_page_id}"
                    report_error("action", error_msg)
                    warn(error_msg)
                    errors.append(error_msg)
                    # Mark as error in legacy database
                    cursor.execute("""
                        UPDATE pages
                        SET migration_status = -4
                        WHERE id = %s
                    """, (legacy_page_id,))
                    continue
                
                # Verify it's the correct class
                if not hasattr(new_page, 'recalculateGeneratedValues'):
                    error_msg = f"Page {new_page_id} (class: {new_page.class_name}) does not have recalculateGeneratedValues method"
                    report_error("action", error_msg)
                    warn(error_msg)
                    errors.append(error_msg)
                    cursor.execute("""
                        UPDATE pages
                        SET migration_status = -4
                        WHERE id = %s
                    """, (legacy_page_id,))
                    continue
                
                # Call recalculateGeneratedValues()
                if not new_page.recalculateGeneratedValues():
                    error_msg = f"Failed to recalculate generated values for page {legacy_page_id} (new_id: {new_page_id}, class: {page_class})"
                    report_error("action", error_msg)
                    warn(error_msg)
                    errors.append(error_msg)
                    # Mark as error in legacy database
                    cursor.execute("""
                        UPDATE pages
                        SET migration_status = -4
                        WHERE id = %s
                    """, (legacy_page_id,))
                    continue
                
                # Flag parent page as modified (recalculateGeneratedValues should have flagged cache refresh)
                if hasattr(new_page, 'flag_page_modification'):
                    new_page.flag_page_modification("recalculated generated values")
                
                # Update migration_status to 4 (calc completed successfully)
                cursor.execute("""
                    UPDATE pages
                    SET migration_status = 4
                    WHERE id = %s
                """, (legacy_page_id,))
                
                migrated += 1
                debug(f"Recalculated generated values for page {legacy_page_id} -> {new_page_id} (class: {page_class})")
                
            except Exception as e:
                error_msg = f"Error recalculating generated values for page {page_row.get('id', 'unknown')}: {e}"
                report_error("action", error_msg)
                warn(error_msg)
                errors.append(error_msg)
                # Mark as error in legacy database
                try:
                    cursor.execute("""
                        UPDATE pages
                        SET migration_status = -4
                        WHERE id = %s
                    """, (page_row.get('id'),))
                except:
                    pass
        
        legacy_conn.commit()
        
        # Check if there are more pages to migrate
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM pages
            WHERE migration_status = 3
            AND class IN ('statement', 'invoice', 'sale')
            AND new_id IS NOT NULL
        """)
        
        count_result = cursor.fetchone()
        has_more = (count_result['count'] if count_result else 0) > 0
        
        result = {
            "migrated": migrated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],  # Limit error details
            "has_more": has_more
        }
        
        log(f"Recalculated generated values for {migrated} pages, skipped {skipped}, {len(errors)} errors")
        trace_out()
        return result
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def migrate_images(legacy_conn, batch_size: int = 100) -> Dict[str, Any]:
    """Migrate images from legacy database.
    
    Special migration phase for migrating images.
    Processes one image per cycle for pages with migration_status = 1.
    
    Args:
        legacy_conn: Legacy database connection
        batch_size: Not used (processes one image per cycle)
        
    Returns:
        Dictionary with migration results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    # Base path for legacy images
    LEGACY_IMAGE_BASE_PATH = "/var/www/books.ppw/public_html/images/"
    
    try:
        cursor = legacy_conn.cursor()
        
        # First, check for pages with status 1 that have all images already migrated
        # (all images have new_id set, but page status wasn't updated to 2)
        cursor.execute("""
            SELECT p.id as legacy_page_id
            FROM pages p
            WHERE p.migration_status = 1
            AND EXISTS (SELECT 1 FROM images i WHERE i.parent = p.id)
            AND NOT EXISTS (SELECT 1 FROM images i WHERE i.parent = p.id AND i.new_id IS NULL)
            ORDER BY p.id
            LIMIT 1
        """)
        
        completed_page = cursor.fetchone()
        if completed_page:
            # All images are migrated, set status to 2
            cursor.execute("""
                UPDATE pages
                SET migration_status = 2
                WHERE id = %s
            """, (completed_page['legacy_page_id'],))
            legacy_conn.commit()
            log(f"Page {completed_page['legacy_page_id']} had all images already migrated, set status to 2")
            # Continue to process next page (return has_more=True to continue)
            trace_out()
            return {
                "migrated": 0,
                "skipped": 1,
                "errors": 0,
                "error_details": [],
                "has_more": True,
                "message": f"Page {completed_page['legacy_page_id']} already had all images migrated"
            }
        
        # Find a page with migration_status = 1 that has images without new_id
        cursor.execute("""
            SELECT DISTINCT p.id as legacy_page_id, p.new_id as new_page_id
            FROM pages p
            INNER JOIN images i ON i.parent = p.id
            WHERE p.migration_status = 1
            AND i.new_id IS NULL
            ORDER BY p.id
            LIMIT 1
        """)
        
        page_row = cursor.fetchone()
        
        if not page_row:
            # No pages with images to migrate
            trace_out()
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "error_details": [],
                "has_more": False,
                "message": "No pages with images to migrate"
            }
        
        legacy_page_id = page_row['legacy_page_id']
        new_page_id = page_row['new_page_id']
        
        if not new_page_id:
            error_msg = f"Page {legacy_page_id} has no new_id mapping"
            report_error("action", error_msg)
            warn(error_msg)
            legacy_conn.rollback()
            trace_out()
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 1,
                "error_details": [error_msg],
                "has_more": True
            }
        
        # Check if page has any images without new_id
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM images
            WHERE parent = %s AND new_id IS NULL
        """, (legacy_page_id,))
        
        image_count_result = cursor.fetchone()
        remaining_images = image_count_result['count'] if image_count_result else 0
        
        if remaining_images == 0:
            # No images to migrate for this page, set status to 2
            cursor.execute("""
                UPDATE pages
                SET migration_status = 2
                WHERE id = %s
            """, (legacy_page_id,))
            legacy_conn.commit()
            log(f"Page {legacy_page_id} has no images to migrate, set status to 2")
            trace_out()
            return {
                "migrated": 0,
                "skipped": 1,
                "errors": 0,
                "error_details": [],
                "has_more": True
            }
        
        # Get one image to process (ordered by imageRank)
        cursor.execute("""
            SELECT i.id, i.imageRank, i.caption
            FROM images i
            WHERE i.parent = %s AND i.new_id IS NULL
            ORDER BY i.imageRank ASC
            LIMIT 1
        """, (legacy_page_id,))
        
        image_row = cursor.fetchone()
        
        if not image_row:
            # Should not happen, but handle it
            trace_out()
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "error_details": [],
                "has_more": True
            }
        
        image_id = image_row['id']
        image_rank = image_row['imageRank']
        caption = image_row['caption'] or ""
        
        # Find the largest image instance (by width)
        cursor.execute("""
            SELECT src, width, height, filesize
            FROM imageinstances
            WHERE imageId = %s
            ORDER BY width DESC
            LIMIT 1
        """, (image_id,))
        
        instance_row = cursor.fetchone()
        
        if not instance_row:
            error_msg = f"Image {image_id} has no instances"
            report_error("action", error_msg)
            warn(error_msg)
            # Set page status to -2 (error)
            cursor.execute("""
                UPDATE pages
                SET migration_status = -2
                WHERE id = %s
            """, (legacy_page_id,))
            legacy_conn.commit()
            trace_out()
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 1,
                "error_details": [error_msg],
                "has_more": True
            }
        
        src_path = instance_row['src']
        full_path = LEGACY_IMAGE_BASE_PATH + src_path
        
        # Validate file exists
        from pathlib import Path
        if not Path(full_path).exists():
            error_msg = f"Image file not found: {full_path}"
            report_error("action", error_msg)
            warn(error_msg)
            # Set page status to -2 (error)
            cursor.execute("""
                UPDATE pages
                SET migration_status = -2
                WHERE id = %s
            """, (legacy_page_id,))
            legacy_conn.commit()
            trace_out()
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 1,
                "error_details": [error_msg],
                "has_more": True
            }
        
        # Get the new page object
        new_page = get_page(page_id=new_page_id)
        if not new_page:
            error_msg = f"New page {new_page_id} not found"
            report_error("action", error_msg)
            warn(error_msg)
            # Set page status to -2 (error)
            cursor.execute("""
                UPDATE pages
                SET migration_status = -2
                WHERE id = %s
            """, (legacy_page_id,))
            legacy_conn.commit()
            trace_out()
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 1,
                "error_details": [error_msg],
                "has_more": True
            }
        
        # Add image to new page
        new_image_id = new_page.add_image(full_path, caption)
        
        # Check if add_image failed or set errors
        if new_image_id is None or is_error():
            error_msg = f"Failed to add image {image_id} to page {new_page_id}"
            if is_error():
                # Get error details from error store
                from hh.gateway.error.error_store import get_errors
                error_list = get_errors()
                if error_list:
                    error_msg = f"Failed to add image {image_id} to page {new_page_id}: {error_list[-1].content}"
            report_error("action", error_msg)
            warn(error_msg)
            # Set page status to -2 (error)
            cursor.execute("""
                UPDATE pages
                SET migration_status = -2
                WHERE id = %s
            """, (legacy_page_id,))
            legacy_conn.commit()
            trace_out()
            return {
                "migrated": 0,
                "skipped": 0,
                "errors": 1,
                "error_details": [error_msg],
                "has_more": True
            }
        
        # Store new image ID in legacy images table
        cursor.execute("""
            UPDATE images
            SET new_id = %s
            WHERE id = %s
        """, (new_image_id, image_id))
        
        # Check if there are more images remaining for this page
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM images
            WHERE parent = %s AND new_id IS NULL
        """, (legacy_page_id,))
        
        remaining_result = cursor.fetchone()
        remaining_count = remaining_result['count'] if remaining_result else 0
        
        if remaining_count == 0:
            # No more images, set page status to 2 (success)
            cursor.execute("""
                UPDATE pages
                SET migration_status = 2
                WHERE id = %s
            """, (legacy_page_id,))
            log(f"Page {legacy_page_id} image migration complete, set status to 2")
        # else: leave status at 1 for next cycle
        
        legacy_conn.commit()
        
        log(f"Migrated image {image_id} (legacy) -> {new_image_id} (new) for page {legacy_page_id} -> {new_page_id}")
        
        # Check if there are any errors from add_image
        migration_errors = 0
        error_details = []
        if is_error():
            migration_errors = 1
            from hh.gateway.error.error_store import get_errors
            error_list = get_errors()
            if error_list:
                error_details = [str(error_list[-1].content)]
        
        trace_out()
        return {
            "migrated": 1,
            "skipped": 0,
            "errors": migration_errors,
            "error_details": error_details,
            "has_more": True
        }
        
    except Exception as e:
        error_msg = f"Migration error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        legacy_conn.rollback()
        trace_out()
        return {"error": str(e)}


def check_orphan_pages(legacy_conn) -> List[int]:
    """Check for pages with missing parent pages in legacy database."""
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT child.id
        FROM pages child
        LEFT JOIN pages parent ON parent.id = child.parent
        WHERE child.parent <> 0 AND parent.id IS NULL
        ORDER BY child.id
    """)
    return [row['id'] for row in cursor.fetchall()]


def check_orphan_accounts(legacy_conn) -> List[int]:
    """Check for accounts without corresponding pages."""
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT a.id
        FROM accounts a
        LEFT JOIN pages p ON a.id = p.id
        WHERE p.id IS NULL
        ORDER BY a.id
    """)
    return [row['id'] for row in cursor.fetchall()]


def check_orphan_statements(legacy_conn) -> List[int]:
    """Check for statements without corresponding pages."""
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT s.id
        FROM statements s
        LEFT JOIN pages p ON s.id = p.id
        WHERE p.id IS NULL
        ORDER BY s.id
    """)
    return [row['id'] for row in cursor.fetchall()]


def check_orphan_transfers(legacy_conn) -> List[int]:
    """Check for transfers without corresponding pages."""
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT t.id
        FROM transfers t
        LEFT JOIN pages p ON t.id = p.id
        WHERE p.id IS NULL
        ORDER BY t.id
    """)
    return [row['id'] for row in cursor.fetchall()]


def check_orphan_fees(legacy_conn) -> List[int]:
    """Check for fees without corresponding pages."""
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT f.id
        FROM fees f
        LEFT JOIN pages p ON f.id = p.id
        WHERE p.id IS NULL
        ORDER BY f.id
    """)
    return [row['id'] for row in cursor.fetchall()]


def check_orphan_invoices(legacy_conn) -> List[int]:
    """Check for invoices without corresponding pages."""
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT i.id
        FROM invoices i
        LEFT JOIN pages p ON i.id = p.id
        WHERE p.id IS NULL
        ORDER BY i.id
    """)
    return [row['id'] for row in cursor.fetchall()]


def check_orphan_sales(legacy_conn) -> List[int]:
    """Check for sales without corresponding pages."""
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT s.id
        FROM sales s
        LEFT JOIN pages p ON s.id = p.id
        WHERE p.id IS NULL
        ORDER BY s.id
    """)
    return [row['id'] for row in cursor.fetchall()]


def check_orphan_fiscal_periods(legacy_conn) -> List[int]:
    """Check for fiscalPeriods without corresponding pages."""
    cursor = legacy_conn.cursor()
    cursor.execute("""
        SELECT fp.id
        FROM fiscalPeriods fp
        LEFT JOIN pages p ON fp.id = p.id
        WHERE p.id IS NULL
        ORDER BY fp.id
    """)
    return [row['id'] for row in cursor.fetchall()]


def check_unexpected_page_classes(legacy_conn) -> List[Dict[str, Any]]:
    """Check for pages with unexpected class values."""
    cursor = legacy_conn.cursor()
    expected_classes = {
        'page', 'account', 'statement', 'transfer', 'fee', 
        'invoice', 'sale', 'fiscalPeriod', 'expenseCategory'
    }
    cursor.execute("""
        SELECT id, class
        FROM pages
        WHERE class NOT IN ('page', 'account', 'statement', 'transfer', 'fee', 'invoice', 'sale', 'fiscalPeriod', 'expenseCategory')
        ORDER BY id
    """)
    return [{'id': row['id'], 'class': row['class']} for row in cursor.fetchall()]


def get_migration_status() -> Dict[str, Any]:
    """Get migration status from legacy database.
    
    Only the pages table has new_id column. Other tables are tracked
    by checking if their corresponding page has been migrated.
    Counts are based on class field in pages table.
    
    Returns:
        Dictionary with migration statistics including status breakdown by class
    """
    trace_in()
    try:
        with get_legacy_db_connection() as legacy_conn:
            cursor = legacy_conn.cursor()
            
            status = {}
            status_breakdown = {}
            
            # Pages table - only count class='page' (not all entries)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(new_id) as migrated
                FROM pages
                WHERE class = 'page'
            """)
            result = cursor.fetchone()
            if result:
                status['pages'] = {
                    "total": result['total'],
                    "migrated": result['migrated'],
                    "remaining": result['total'] - result['migrated']
                }
            
            # Get migration_status breakdown for 'page' class
            cursor.execute("""
                SELECT 
                    COALESCE(migration_status, 0) as status_value,
                    COUNT(*) as count
                FROM pages
                WHERE class = 'page'
                GROUP BY migration_status
                ORDER BY migration_status
            """)
            page_status_breakdown = {}
            for row in cursor.fetchall():
                page_status_breakdown[row['status_value']] = row['count']
            status_breakdown['pages'] = page_status_breakdown
            
            # Other types - count by class in pages table
            class_mapping = {
                'accounts': 'account',
                'statements': 'statement',
                'transfers': 'transfer',
                'fees': 'fee',
                'invoices': 'invoice',
                'sales': 'sale',
                'fiscalPeriods': 'fiscalPeriod',
            }
            
            for table_key, class_name in class_mapping.items():
                # Count total records of this class
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(new_id) as migrated
                    FROM pages
                    WHERE class = %s
                """, (class_name,))
                result = cursor.fetchone()
                if result:
                    status[table_key] = {
                        "total": result['total'],
                        "migrated": result['migrated'],
                        "remaining": result['total'] - result['migrated']
                    }
                
                # Get migration_status breakdown for this class
                cursor.execute("""
                    SELECT 
                        COALESCE(migration_status, 0) as status_value,
                        COUNT(*) as count
                    FROM pages
                    WHERE class = %s
                    GROUP BY migration_status
                    ORDER BY migration_status
                """, (class_name,))
                class_status_breakdown = {}
                for row in cursor.fetchall():
                    class_status_breakdown[row['status_value']] = row['count']
                status_breakdown[table_key] = class_status_breakdown
            
            trace_out()
            return {
                "status": status,
                "status_breakdown": status_breakdown
            }
            
    except Exception as e:
        error_msg = f"Failed to get migration status: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return {"error": str(e)}


def get_migration_orphan_checks() -> Dict[str, Any]:
    """Get orphan check results from legacy database.
    
    Returns:
        Dictionary with orphan check results
    """
    trace_in()
    try:
        with get_legacy_db_connection() as legacy_conn:
            # Orphan checks
            orphans = {
                "orphan_pages": check_orphan_pages(legacy_conn),
                "orphan_accounts": check_orphan_accounts(legacy_conn),
                "orphan_statements": check_orphan_statements(legacy_conn),
                "orphan_transfers": check_orphan_transfers(legacy_conn),
                "orphan_fees": check_orphan_fees(legacy_conn),
                "orphan_invoices": check_orphan_invoices(legacy_conn),
                "orphan_sales": check_orphan_sales(legacy_conn),
                "orphan_fiscalPeriods": check_orphan_fiscal_periods(legacy_conn),
                "unexpected_page_classes": check_unexpected_page_classes(legacy_conn),
            }
            
            # Convert to counts for summary
            orphan_summary = {key: len(ids) if isinstance(ids, list) else 0 for key, ids in orphans.items()}
            
            trace_out()
            return {
                "orphans": orphans,
                "orphan_summary": orphan_summary
            }
            
    except Exception as e:
        error_msg = f"Failed to get migration orphan checks: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return {"error": str(e)}


def check_new_pages_without_legacy_link(type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Check for pages in new system that don't have a legacy page with new_id set.
    
    Args:
        type_filter: Optional page class to filter by (e.g., 'account', 'statement')
    
    Returns:
        List of dictionaries with page info (id, name, class) for pages without legacy links
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            # Get all pages from new database, optionally filtered by class
            if type_filter:
                new_pages = gateway.conn.read("SELECT id, name, class FROM pages WHERE class = %s ORDER BY id", (type_filter,))
            else:
                new_pages = gateway.conn.read("SELECT id, name, class FROM pages ORDER BY id")
            
            orphan_pages = []
            legacy_cursor = legacy_conn.cursor()
            
            for page in new_pages:
                page_id = page['id']
                # Check if there's a legacy page with new_id pointing to this page
                legacy_cursor.execute("SELECT id FROM pages WHERE new_id = %s LIMIT 1", (page_id,))
                legacy_result = legacy_cursor.fetchone()
                
                if not legacy_result:
                    # This page in new system doesn't have a legacy link
                    orphan_pages.append({
                        'id': page_id,
                        'name': page.get('name'),
                        'class': page.get('class', 'page')
                    })
            
            trace_out()
            return orphan_pages
            
    except Exception as e:
        error_msg = f"Failed to check new pages without legacy links: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return []


def check_legacy_pages_without_new_link(type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Check for legacy pages with new_id set that don't exist in new system.
    
    Only checks pages with migration_status = 0 (not yet verified).
    
    Args:
        type_filter: Optional page class to filter by (e.g., 'account', 'statement')
    
    Returns:
        List of dictionaries with legacy page info (legacy_id, new_id, name, class) for pages without new system entries
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            legacy_cursor = legacy_conn.cursor()
            # Get all legacy pages with new_id set and migration_status = 0, optionally filtered by class
            if type_filter:
                legacy_cursor.execute("SELECT id, new_id, name, class FROM pages WHERE new_id IS NOT NULL AND migration_status = 0 AND class = %s ORDER BY id", (type_filter,))
            else:
                legacy_cursor.execute("SELECT id, new_id, name, class FROM pages WHERE new_id IS NOT NULL AND migration_status = 0 ORDER BY id")
            legacy_pages = legacy_cursor.fetchall()
            
            orphan_pages = []
            
            for legacy_page in legacy_pages:
                new_id = legacy_page['new_id']
                # Check if this page exists in new system
                new_page = gateway.conn.read("SELECT id FROM pages WHERE id = %s LIMIT 1", (new_id,))
                
                if not new_page:
                    # Legacy page has new_id but page doesn't exist in new system
                    orphan_pages.append({
                        'legacy_id': legacy_page['id'],
                        'new_id': new_id,
                        'name': legacy_page.get('name'),
                        'class': legacy_page.get('class', 'page')
                    })
            
            trace_out()
            return orphan_pages
            
    except Exception as e:
        error_msg = f"Failed to check legacy pages without new links: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return []


def check_page_data_mismatches(type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Check for pages where legacy and new system data doesn't match.
    
    Only checks pages with migration_status = 0 (not yet verified).
    
    Args:
        type_filter: Optional page class to filter by (e.g., 'account', 'statement')
    
    Returns:
        List of dictionaries with mismatch info (id, field, legacy_value, new_value)
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            legacy_cursor = legacy_conn.cursor()
            # Get all legacy pages with new_id set and migration_status = 0, optionally filtered by class
            if type_filter:
                legacy_cursor.execute("""
                    SELECT id, new_id, name, class, text, parent, link
                    FROM pages 
                    WHERE new_id IS NOT NULL 
                    AND migration_status = 0
                    AND class = %s
                    ORDER BY id
                """, (type_filter,))
            else:
                legacy_cursor.execute("""
                    SELECT id, new_id, name, class, text, parent, link
                    FROM pages 
                    WHERE new_id IS NOT NULL 
                    AND migration_status = 0
                    ORDER BY id
                """)
            legacy_pages = legacy_cursor.fetchall()
            
            mismatches = []
            
            for legacy_page in legacy_pages:
                new_id = legacy_page['new_id']
                # Get corresponding page from new system
                new_pages = gateway.conn.read("""
                    SELECT id, name, class, text, parent, link
                    FROM pages 
                    WHERE id = %s
                    LIMIT 1
                """, (new_id,))
                
                if not new_pages:
                    continue  # Already caught by check_legacy_pages_without_new_link
                
                new_page = new_pages[0]
                
                # Compare fields (excluding text - text will be migrated separately after all pages exist)
                fields_to_check = [
                    ('name', legacy_page.get('name'), new_page.get('name')),
                    ('class', legacy_page.get('class'), new_page.get('class')),
                    ('link', legacy_page.get('link'), new_page.get('link')),
                ]
                
                # For parent, we need to check if legacy parent's new_id matches new parent
                legacy_parent_id = legacy_page.get('parent')
                new_parent_id = new_page.get('parent')
                
                if legacy_parent_id and legacy_parent_id != 0:
                    # Get legacy parent's new_id
                    legacy_cursor.execute("SELECT new_id FROM pages WHERE id = %s LIMIT 1", (legacy_parent_id,))
                    legacy_parent_result = legacy_cursor.fetchone()
                    legacy_parent_new_id = legacy_parent_result['new_id'] if legacy_parent_result else None
                    
                    if legacy_parent_new_id != new_parent_id:
                        mismatches.append({
                            'id': new_id,
                            'legacy_id': legacy_page['id'],
                            'field': 'parent',
                            'legacy_value': f"{legacy_parent_id} (new_id: {legacy_parent_new_id})",
                            'new_value': str(new_parent_id) if new_parent_id else 'None'
                        })
                elif legacy_parent_id != new_parent_id:
                    # Both should be 0 or None
                    mismatches.append({
                        'id': new_id,
                        'legacy_id': legacy_page['id'],
                        'field': 'parent',
                        'legacy_value': str(legacy_parent_id) if legacy_parent_id else 'None',
                        'new_value': str(new_parent_id) if new_parent_id else 'None'
                    })
                
                # Check other fields
                for field_name, legacy_value, new_value in fields_to_check:
                    # Normalize None to empty string for comparison
                    legacy_val = legacy_value if legacy_value is not None else ''
                    new_val = new_value if new_value is not None else ''
                    
                    if legacy_val != new_val:
                        mismatches.append({
                            'id': new_id,
                            'legacy_id': legacy_page['id'],
                            'field': field_name,
                            'legacy_value': str(legacy_val)[:100] if len(str(legacy_val)) <= 100 else str(legacy_val)[:100] + '...',
                            'new_value': str(new_val)[:100] if len(str(new_val)) <= 100 else str(new_val)[:100] + '...'
                        })
            
            trace_out()
            return mismatches
            
    except Exception as e:
        error_msg = f"Failed to check page data mismatches: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return []


def repair_migration_issues(repair_limit: int = 1, type_filter: Optional[str] = None) -> Dict[str, Any]:
    """Repair migration issues found by double check.
    
    Args:
        repair_limit: Maximum number of repairs to perform in one batch
        type_filter: Optional filter type (e.g., 'images' for image-specific repairs)
        
    Returns:
        Dictionary with repair results
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return {"error": "No gateway available"}
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            repairs_made = 0
            errors = []
            
            # Special handling for images repair
            if type_filter == 'images':
                # Repair 1: Null out new_id for legacy images that don't exist in new system
                legacy_orphans = check_legacy_images_without_new_link()
                legacy_cursor = legacy_conn.cursor()
                
                for orphan in legacy_orphans[:repair_limit]:
                    try:
                        legacy_id = orphan['legacy_id']
                        # Null out the new_id so image processor can retry
                        legacy_cursor.execute("""
                            UPDATE images
                            SET new_id = NULL
                            WHERE id = %s
                        """, (legacy_id,))
                        repairs_made += 1
                        debug(f"Nulled out new_id for legacy image {legacy_id} (image doesn't exist in new system)")
                    except Exception as e:
                        error_msg = f"Error nulling new_id for legacy image {orphan.get('legacy_id', 'unknown')}: {e}"
                        report_error("action", error_msg)
                        warn(error_msg)
                        errors.append(error_msg)
                
                legacy_conn.commit()
                
                # Repair 2: Delete orphaned new images (no legacy link) - only if confirm flag is set
                confirm_arg = gateway.get_arg('confirm')
                confirm = confirm_arg if confirm_arg else False
                if isinstance(confirm, str):
                    confirm = confirm.lower() in ('true', '1', 'yes', 'on')
                
                if confirm and repairs_made < repair_limit:
                    new_orphans = check_new_images_without_legacy_link()
                    for orphan in new_orphans[:repair_limit - repairs_made]:
                        try:
                            image_id = orphan['id']
                            # Delete the orphaned image from new system
                            affected = gateway.conn.delete("DELETE FROM images WHERE id = %s", (image_id,))
                            if affected > 0:
                                repairs_made += 1
                                debug(f"Deleted orphaned image {image_id} (no legacy link)")
                            else:
                                errors.append(f"Failed to delete orphaned image {image_id}")
                        except Exception as e:
                            error_msg = f"Error deleting orphaned image {orphan.get('id', 'unknown')}: {e}"
                            report_error("action", error_msg)
                            warn(error_msg)
                            errors.append(error_msg)
                
                trace_out()
                return {
                    "repairs_made": repairs_made,
                    "errors": len(errors),
                    "error_details": errors[:10],
                    "has_more": len(legacy_orphans) > repair_limit or (confirm and len(new_orphans) > (repair_limit - repairs_made))
                }
            
            # Repair 1: Delete orphaned new pages (no legacy link) - only if confirm flag is set
            confirm = gateway.get_arg('confirm')
            if confirm and repairs_made < repair_limit:
                new_orphans = check_new_pages_without_legacy_link(type_filter=type_filter)
                for orphan in new_orphans[:repair_limit - repairs_made]:
                    try:
                        page_id = orphan['id']
                        # Skip root page
                        if page_id == 1:
                            debug(f"Skipping root page {page_id} for deletion")
                            continue
                        
                        page = get_page(page_id)
                        if page:
                            # Skip if parent is 0, None, or any falsy value
                            if not page.parent or page.parent == 0:
                                debug(f"Skipping root page {page_id} (parent is {page.parent}) for deletion")
                                continue
                            
                            # Delete the orphaned page using delete_page (requires confirm flag)
                            if page.delete_page():
                                repairs_made += 1
                                debug(f"Deleted orphaned page {page_id} (no legacy link)")
                            else:
                                errors.append(f"Failed to delete orphaned page {page_id}")
                        else:
                            errors.append(f"Orphaned page {page_id} not found")
                    except Exception as e:
                        error_msg = f"Error deleting orphaned page {orphan.get('id', 'unknown')}: {e}"
                        report_error("action", error_msg)
                        warn(error_msg)
                        errors.append(error_msg)
            
            # Repair 2: Fix data mismatches
            if repairs_made < repair_limit:
                data_mismatches = check_page_data_mismatches(type_filter=type_filter)
                legacy_cursor = legacy_conn.cursor()
                legacy_cursor = legacy_conn.cursor()
                
                for mismatch in data_mismatches:
                    if repairs_made >= repair_limit:
                        break
                    
                    try:
                        new_id = mismatch['id']
                        legacy_id = mismatch['legacy_id']
                        field = mismatch['field']
                        legacy_value = mismatch['legacy_value']
                        
                        # Skip root page (ID 1 or parent is 0/null/None)
                        if new_id == 1:
                            debug(f"Skipping root page {new_id} for mismatch repair")
                            continue
                        
                        page = get_page(new_id)
                        if not page:
                            errors.append(f"Page {new_id} not found for mismatch repair")
                            continue
                        
                        # Also skip if parent is 0, None, or any falsy value
                        if not page.parent or page.parent == 0:
                            debug(f"Skipping root page {new_id} (parent is {page.parent}) for mismatch repair")
                            continue
                        
                        if field == 'name':
                            # Fix name mismatch
                            legacy_name = legacy_value if legacy_value else None
                            # Check if name actually needs to be changed
                            if page.name != legacy_name:
                                if page.modify_name(legacy_name):
                                    repairs_made += 1
                                    debug(f"Fixed name mismatch for page {new_id}: '{page.name}' -> '{legacy_name}'")
                                else:
                                    errors.append(f"Failed to fix name mismatch for page {new_id}")
                            else:
                                debug(f"Name already matches for page {new_id}: '{legacy_name}'")
                        
                        elif field == 'link':
                            # Fix link mismatch - directly update database
                            legacy_link = legacy_value if legacy_value and legacy_value.strip() else None
                            # Normalize current link for comparison
                            current_link = page.link if (page.link and page.link.strip()) else None
                            if current_link != legacy_link:
                                affected = gateway.conn.update("UPDATE pages SET link = %s WHERE id = %s", (legacy_link, new_id))
                                if affected > 0:
                                    page.link = legacy_link
                                    repairs_made += 1
                                    debug(f"Fixed link mismatch for page {new_id}: '{current_link}' -> '{legacy_link}'")
                                else:
                                    errors.append(f"Failed to fix link mismatch for page {new_id}")
                            else:
                                debug(f"Link already matches for page {new_id}: '{legacy_link}'")
                        
                        elif field == 'parent':
                            # Fix parent mismatch
                            # Extract the new_id from legacy_value if it contains it
                            legacy_parent_new_id = None
                            if '(' in legacy_value and 'new_id:' in legacy_value:
                                # Format: "123 (new_id: 456)"
                                try:
                                    legacy_parent_new_id = int(legacy_value.split('new_id:')[1].strip().rstrip(')'))
                                except (ValueError, IndexError):
                                    pass
                            
                            if legacy_parent_new_id is None:
                                # Try to get legacy parent's new_id from the legacy page
                                legacy_cursor.execute("SELECT parent FROM pages WHERE id = %s LIMIT 1", (legacy_id,))
                                legacy_result = legacy_cursor.fetchone()
                                if legacy_result and legacy_result.get('parent'):
                                    legacy_parent_id = legacy_result['parent']
                                    if legacy_parent_id and legacy_parent_id != 0:
                                        legacy_cursor.execute("SELECT new_id FROM pages WHERE id = %s LIMIT 1", (legacy_parent_id,))
                                        parent_result = legacy_cursor.fetchone()
                                        if parent_result and parent_result.get('new_id'):
                                            legacy_parent_new_id = parent_result['new_id']
                            
                            if legacy_parent_new_id:
                                if page.move_page(legacy_parent_new_id):
                                    repairs_made += 1
                                    debug(f"Fixed parent mismatch for page {new_id}: moved to parent {legacy_parent_new_id}")
                                else:
                                    errors.append(f"Failed to fix parent mismatch for page {new_id}")
                            elif legacy_value == 'None' or legacy_value == '0':
                                # Legacy has no parent, move to root (parent = 0)
                                if page.move_page(0):
                                    repairs_made += 1
                                    debug(f"Fixed parent mismatch for page {new_id}: moved to root")
                                else:
                                    errors.append(f"Failed to fix parent mismatch for page {new_id} (move to root)")
                            else:
                                errors.append(f"Could not determine legacy parent new_id for page {new_id} (legacy_value: '{legacy_value}')")
                        
                        elif field == 'class':
                            # Class mismatch - this is more serious, log but don't auto-fix
                            errors.append(f"Class mismatch for page {new_id}: legacy='{legacy_value}', new='{page.class_name}' (not auto-fixing)")
                    
                    except Exception as e:
                        error_msg = f"Error repairing mismatch for page {mismatch.get('id', 'unknown')}: {e}"
                        report_error("action", error_msg)
                        warn(error_msg)
                        errors.append(error_msg)
            
            result = {
                "repairs_made": repairs_made,
                "errors": len(errors),
                "error_details": errors[:10],  # Limit error details
                "has_more": repairs_made >= repair_limit  # If we hit the limit, there might be more
            }
            
            log(f"Repaired {repairs_made} migration issues, {len(errors)} errors")
            trace_out()
            return result
            
    except Exception as e:
        error_msg = f"Repair error: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return {"error": str(e)}


def check_legacy_images_without_new_link() -> List[Dict[str, Any]]:
    """Check for legacy images with new_id set that don't exist in new system.
    
    Returns:
        List of dictionaries with legacy image info (legacy_id, new_id, parent, caption) for images without new system entries
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            legacy_cursor = legacy_conn.cursor()
            # Get all legacy images with new_id set
            legacy_cursor.execute("""
                SELECT id, new_id, parent, caption
                FROM images 
                WHERE new_id IS NOT NULL 
                ORDER BY id
            """)
            legacy_images = legacy_cursor.fetchall()
            
            orphan_images = []
            
            for legacy_image in legacy_images:
                new_id = legacy_image['new_id']
                # Check if this image exists in new system
                new_images = gateway.conn.read("SELECT id FROM images WHERE id = %s LIMIT 1", (new_id,))
                
                if not new_images:
                    # Legacy image has new_id but image doesn't exist in new system
                    orphan_images.append({
                        'legacy_id': legacy_image['id'],
                        'new_id': new_id,
                        'parent': legacy_image.get('parent'),
                        'caption': legacy_image.get('caption')
                    })
            
            trace_out()
            return orphan_images
            
    except Exception as e:
        error_msg = f"Failed to check legacy images without new links: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return []


def check_new_images_without_legacy_link() -> List[Dict[str, Any]]:
    """Check for images in new system that don't have a legacy image with new_id set.
    
    Returns:
        List of dictionaries with image info (id, caption) for images without legacy links
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            # Get all images from new database
            new_images = gateway.conn.read("SELECT id, caption FROM images ORDER BY id")
            
            orphan_images = []
            legacy_cursor = legacy_conn.cursor()
            
            for image in new_images:
                image_id = image['id']
                # Check if there's a legacy image with new_id pointing to this image
                legacy_cursor.execute("SELECT id FROM images WHERE new_id = %s LIMIT 1", (image_id,))
                legacy_result = legacy_cursor.fetchone()
                
                if not legacy_result:
                    # This image in new system doesn't have a legacy link
                    orphan_images.append({
                        'id': image_id,
                        'caption': image.get('caption')
                    })
            
            trace_out()
            return orphan_images
            
    except Exception as e:
        error_msg = f"Failed to check new images without legacy links: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return []


def check_pages_missing_text_migration() -> List[Dict[str, Any]]:
    """Check for pages in new database with no text that had text in legacy database.
    
    Only checks pages with migration_status = 3 (text migration marked complete).
    
    Returns:
        List of dictionaries with page info (legacy_id, new_id, name, class) for pages that need text migration
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            legacy_cursor = legacy_conn.cursor()
            
            # Find pages where:
            # - Legacy has text (not NULL and not empty)
            # - New system has no text (NULL or empty)
            # - Legacy has new_id set (page was migrated)
            # - Legacy has migration_status = 3 (text migration marked complete)
            legacy_cursor.execute("""
                SELECT p.id as legacy_id, p.new_id as new_id, p.name, p.class, p.text as legacy_text
                FROM pages p
                WHERE p.new_id IS NOT NULL
                AND p.migration_status = 3
                AND p.text IS NOT NULL
                AND p.text != ''
                ORDER BY p.id
            """)
            legacy_pages = legacy_cursor.fetchall()
            
            missing_text_pages = []
            
            for legacy_page in legacy_pages:
                new_id = legacy_page['new_id']
                legacy_text = legacy_page['legacy_text']
                
                # Check if new page has text
                new_pages = gateway.conn.read("""
                    SELECT id, text
                    FROM pages
                    WHERE id = %s
                    LIMIT 1
                """, (new_id,))
                
                if not new_pages:
                    continue  # Page doesn't exist in new system (caught by other checks)
                
                new_page = new_pages[0]
                new_text = new_page.get('text')
                
                # Check if new page has no text (NULL or empty) but legacy had text
                if (not new_text or new_text.strip() == '') and legacy_text and legacy_text.strip():
                    missing_text_pages.append({
                        'legacy_id': legacy_page['legacy_id'],
                        'new_id': new_id,
                        'name': legacy_page.get('name'),
                        'class': legacy_page.get('class', 'page')
                    })
            
            trace_out()
            return missing_text_pages
            
    except Exception as e:
        error_msg = f"Failed to check pages missing text migration: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return []


def get_migration_images_double_check() -> Dict[str, Any]:
    """Get double check results for images - bidirectional orphan checks.
    
    Checks all images regardless of migration_status.
    
    Returns:
        Dictionary with image double check results
    """
    trace_in()
    try:
        # Check 1: Legacy images with new_id that don't exist in new system
        legacy_orphans = check_legacy_images_without_new_link()
        
        # Check 2: New images that don't have a legacy image with new_id pointing to them
        new_orphans = check_new_images_without_legacy_link()
        
        trace_out()
        return {
            "new_orphans": new_orphans,
            "new_orphan_count": len(new_orphans),
            "legacy_orphans": legacy_orphans,
            "legacy_orphan_count": len(legacy_orphans),
            "data_mismatches": [],  # No data mismatch checks for images
            "mismatch_count": 0
        }
            
    except Exception as e:
        error_msg = f"Failed to get migration images double check: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return {"error": str(e)}


def get_migration_text_double_check() -> Dict[str, Any]:
    """Get double check results for text migration - find pages missing text.
    
    Checks for pages in new database with no text that had text in legacy database.
    These pages should have their migration_status set back to 2 for retry.
    
    Returns:
        Dictionary with text double check results
    """
    trace_in()
    try:
        # Check for pages missing text migration
        missing_text_pages = check_pages_missing_text_migration()
        
        # Update migration_status to 2 for pages that need text migration
        # Only update pages that are currently at status 3
        if missing_text_pages:
            with get_legacy_db_connection() as legacy_conn:
                legacy_cursor = legacy_conn.cursor()
                updated_count = 0
                for page in missing_text_pages:
                    legacy_id = page['legacy_id']
                    # Set migration_status back to 2 so text migration can retry
                    # Only update if current status is 3
                    legacy_cursor.execute("""
                        UPDATE pages
                        SET migration_status = 2
                        WHERE id = %s
                        AND migration_status = 3
                    """, (legacy_id,))
                    if legacy_cursor.rowcount > 0:
                        updated_count += 1
                legacy_conn.commit()
                log(f"Set migration_status to 2 for {updated_count} pages missing text migration (downgraded from status 3)")
        
        trace_out()
        return {
            "missing_text_pages": missing_text_pages,
            "missing_text_count": len(missing_text_pages),
            "new_orphans": [],  # No orphan checks for text
            "new_orphan_count": 0,
            "legacy_orphans": [],
            "legacy_orphan_count": 0,
            "data_mismatches": [],
            "mismatch_count": 0
        }
            
    except Exception as e:
        error_msg = f"Failed to get migration text double check: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return {"error": str(e)}


def get_migration_double_check(type_filter: Optional[str] = None) -> Dict[str, Any]:
    """Get double check results - bidirectional checks and data integrity verification.
    
    Only checks pages with migration_status = 0. After checking, pages that pass
    (no orphans, no mismatches) will have their migration_status set to 1.
    
    Args:
        type_filter: Optional page class to filter by (e.g., 'account', 'statement')
    
    Returns:
        Dictionary with double check results
    """
    trace_in()
    try:
        # Check 1: New system pages without legacy links
        new_orphans = check_new_pages_without_legacy_link(type_filter=type_filter)
        
        # Check 2: Legacy pages with new_id but no corresponding new system page
        legacy_orphans = check_legacy_pages_without_new_link(type_filter=type_filter)
        
        # Check 3: Data mismatches between legacy and new systems
        data_mismatches = check_page_data_mismatches(type_filter=type_filter)
        
        # Build sets of legacy IDs that have issues
        legacy_ids_with_issues = set()
        
        # Add legacy IDs from orphan checks
        for orphan in legacy_orphans:
            legacy_ids_with_issues.add(orphan['legacy_id'])
        
        # Add legacy IDs from mismatch checks
        for mismatch in data_mismatches:
            legacy_ids_with_issues.add(mismatch['legacy_id'])
        
        # For new orphans, we need to find their corresponding legacy IDs
        # (if they exist - they might not have a legacy link at all)
        if new_orphans:
            with get_legacy_db_connection() as legacy_conn:
                legacy_cursor = legacy_conn.cursor()
                for orphan in new_orphans:
                    new_id = orphan['id']
                    # Find legacy page with this new_id
                    legacy_cursor.execute("SELECT id FROM pages WHERE new_id = %s LIMIT 1", (new_id,))
                    legacy_result = legacy_cursor.fetchone()
                    if legacy_result:
                        legacy_ids_with_issues.add(legacy_result['id'])
        
        # Update migration_status to 1 for pages that passed (no issues)
        # Only update pages with migration_status = 0 that are not in the issues set
        if type_filter:
            # Get all legacy pages with migration_status = 0 and new_id set for this class
            with get_legacy_db_connection() as legacy_conn:
                legacy_cursor = legacy_conn.cursor()
                legacy_cursor.execute("""
                    SELECT id FROM pages 
                    WHERE new_id IS NOT NULL 
                    AND migration_status = 0 
                    AND class = %s
                """, (type_filter,))
                all_checked_pages = legacy_cursor.fetchall()
                
                # Find pages that passed (are not in issues set)
                passed_legacy_ids = [row['id'] for row in all_checked_pages if row['id'] not in legacy_ids_with_issues]
                
                # Update migration_status to 1 for pages that passed
                if passed_legacy_ids:
                    # Update in batches to avoid SQL parameter limits
                    batch_size = 1000
                    for i in range(0, len(passed_legacy_ids), batch_size):
                        batch = passed_legacy_ids[i:i + batch_size]
                        placeholders = ','.join(['%s'] * len(batch))
                        legacy_cursor.execute(f"""
                            UPDATE pages 
                            SET migration_status = 1 
                            WHERE id IN ({placeholders})
                        """, batch)
                    legacy_conn.commit()
                    log(f"Updated migration_status to 1 for {len(passed_legacy_ids)} pages that passed double check")
        else:
            # Get all legacy pages with migration_status = 0 and new_id set
            with get_legacy_db_connection() as legacy_conn:
                legacy_cursor = legacy_conn.cursor()
                legacy_cursor.execute("""
                    SELECT id FROM pages 
                    WHERE new_id IS NOT NULL 
                    AND migration_status = 0
                """)
                all_checked_pages = legacy_cursor.fetchall()
                
                # Find pages that passed (are not in issues set)
                passed_legacy_ids = [row['id'] for row in all_checked_pages if row['id'] not in legacy_ids_with_issues]
                
                # Update migration_status to 1 for pages that passed
                if passed_legacy_ids:
                    # Update in batches to avoid SQL parameter limits
                    batch_size = 1000
                    for i in range(0, len(passed_legacy_ids), batch_size):
                        batch = passed_legacy_ids[i:i + batch_size]
                        placeholders = ','.join(['%s'] * len(batch))
                        legacy_cursor.execute(f"""
                            UPDATE pages 
                            SET migration_status = 1 
                            WHERE id IN ({placeholders})
                        """, batch)
                    legacy_conn.commit()
                    log(f"Updated migration_status to 1 for {len(passed_legacy_ids)} pages that passed double check")
        
        trace_out()
        return {
            "new_orphans": new_orphans,
            "new_orphan_count": len(new_orphans),
            "legacy_orphans": legacy_orphans,
            "legacy_orphan_count": len(legacy_orphans),
            "data_mismatches": data_mismatches,
            "mismatch_count": len(data_mismatches)
        }
            
    except Exception as e:
        error_msg = f"Failed to get migration double check: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return {"error": str(e)}


def check_new_accounts_without_legacy_link() -> List[Dict[str, Any]]:
    """Check for accounts in new system that don't have a legacy account with new_id set.
    
    Returns:
        List of dictionaries with account info (id, name, type) for accounts without legacy links
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            # Get all accounts from new database
            new_accounts = gateway.conn.read("SELECT id, name FROM pages WHERE class = 'account' ORDER BY id")
            
            orphan_accounts = []
            legacy_cursor = legacy_conn.cursor()
            
            for account in new_accounts:
                account_id = account['id']
                # Check if there's a legacy account with new_id pointing to this account
                legacy_cursor.execute("SELECT id FROM pages WHERE new_id = %s AND class = 'account' LIMIT 1", (account_id,))
                legacy_result = legacy_cursor.fetchone()
                
                if not legacy_result:
                    # Get account type from new system
                    account_page = get_page(account_id)
                    account_type = account_page.type if account_page and hasattr(account_page, 'type') else 'unknown'
                    
                    # This account in new system doesn't have a legacy link
                    orphan_accounts.append({
                        'id': account_id,
                        'name': account.get('name'),
                        'type': account_type
                    })
            
            trace_out()
            return orphan_accounts
            
    except Exception as e:
        error_msg = f"Failed to check new accounts without legacy links: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return []


def check_legacy_accounts_without_new_link() -> List[Dict[str, Any]]:
    """Check for legacy accounts with new_id set that don't exist in new system.
    
    Returns:
        List of dictionaries with legacy account info (legacy_id, new_id, name, type) for accounts without new system entries
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            legacy_cursor = legacy_conn.cursor()
            # Get all legacy accounts with new_id set
            legacy_cursor.execute("""
                SELECT p.id, p.new_id, p.name, p.class
                FROM pages p
                WHERE p.new_id IS NOT NULL
                AND p.class = 'account'
                ORDER BY p.id
            """)
            legacy_accounts = legacy_cursor.fetchall()
            
            orphan_accounts = []
            
            for legacy_account in legacy_accounts:
                new_id = legacy_account['new_id']
                # Check if this account exists in new system
                new_account = gateway.conn.read("SELECT id FROM pages WHERE id = %s AND class = 'account' LIMIT 1", (new_id,))
                
                if not new_account:
                    # Get account type from legacy accounts table
                    legacy_cursor.execute("SELECT type FROM accounts WHERE id = %s LIMIT 1", (legacy_account['id'],))
                    account_type_result = legacy_cursor.fetchone()
                    account_type = account_type_result['type'] if account_type_result and account_type_result.get('type') else 'unknown'
                    
                    # Legacy account has new_id but account doesn't exist in new system
                    orphan_accounts.append({
                        'legacy_id': legacy_account['id'],
                        'new_id': new_id,
                        'name': legacy_account.get('name'),
                        'type': account_type
                    })
            
            trace_out()
            return orphan_accounts
            
    except Exception as e:
        error_msg = f"Failed to check legacy accounts without new links: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return []


def check_account_data_mismatches() -> List[Dict[str, Any]]:
    """Check for accounts where legacy and new system data doesn't match.
    
    Returns:
        List of dictionaries with mismatch info (id, field, legacy_value, new_value)
    """
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        trace_out()
        return []
    
    try:
        with get_legacy_db_connection() as legacy_conn:
            legacy_cursor = legacy_conn.cursor()
            # Get all legacy accounts with new_id set
            legacy_cursor.execute("""
                SELECT p.id, p.new_id, p.name, p.class, p.parent, p.link
                FROM pages p
                WHERE p.new_id IS NOT NULL
                AND p.class = 'account'
                ORDER BY p.id
            """)
            legacy_accounts = legacy_cursor.fetchall()
            
            mismatches = []
            
            for legacy_account in legacy_accounts:
                new_id = legacy_account['new_id']
                # Get corresponding account from new system
                new_accounts = gateway.conn.read("""
                    SELECT id, name, class, parent, link
                    FROM pages 
                    WHERE id = %s
                    AND class = 'account'
                    LIMIT 1
                """, (new_id,))
                
                if not new_accounts:
                    continue  # Already caught by check_legacy_accounts_without_new_link
                
                new_account = new_accounts[0]
                
                # Get account type from legacy accounts table
                legacy_cursor.execute("SELECT type FROM accounts WHERE id = %s LIMIT 1", (legacy_account['id'],))
                account_type_result = legacy_cursor.fetchone()
                legacy_account_type = account_type_result['type'] if account_type_result and account_type_result.get('type') else 'cash'
                
                # Get account type from new system
                account_page = get_page(new_id)
                new_account_type = account_page.type if account_page and hasattr(account_page, 'type') else 'cash'
                
                # Compare account type
                if legacy_account_type != new_account_type:
                    mismatches.append({
                        'id': new_id,
                        'legacy_id': legacy_account['id'],
                        'field': 'type',
                        'legacy_value': legacy_account_type,
                        'new_value': new_account_type
                    })
                
                # Compare fields (excluding text - text will be migrated separately)
                fields_to_check = [
                    ('name', legacy_account.get('name'), new_account.get('name')),
                    ('class', legacy_account.get('class'), new_account.get('class')),
                    ('link', legacy_account.get('link'), new_account.get('link')),
                ]
                
                # For parent, we need to check if legacy parent's new_id matches new parent
                legacy_parent_id = legacy_account.get('parent')
                new_parent_id = new_account.get('parent')
                
                if legacy_parent_id and legacy_parent_id != 0:
                    # Get legacy parent's new_id
                    legacy_cursor.execute("SELECT new_id FROM pages WHERE id = %s LIMIT 1", (legacy_parent_id,))
                    legacy_parent_result = legacy_cursor.fetchone()
                    legacy_parent_new_id = legacy_parent_result['new_id'] if legacy_parent_result else None
                    
                    if legacy_parent_new_id != new_parent_id:
                        mismatches.append({
                            'id': new_id,
                            'legacy_id': legacy_account['id'],
                            'field': 'parent',
                            'legacy_value': f"{legacy_parent_id} (new_id: {legacy_parent_new_id})",
                            'new_value': str(new_parent_id) if new_parent_id else 'None'
                        })
                elif legacy_parent_id != new_parent_id:
                    # Both should be 0 or None
                    mismatches.append({
                        'id': new_id,
                        'legacy_id': legacy_account['id'],
                        'field': 'parent',
                        'legacy_value': str(legacy_parent_id) if legacy_parent_id else 'None',
                        'new_value': str(new_parent_id) if new_parent_id else 'None'
                    })
                
                # Check other fields
                for field_name, legacy_value, new_value in fields_to_check:
                    # Normalize None to empty string for comparison
                    legacy_val = legacy_value if legacy_value is not None else ''
                    new_val = new_value if new_value is not None else ''
                    
                    if legacy_val != new_val:
                        mismatches.append({
                            'id': new_id,
                            'legacy_id': legacy_account['id'],
                            'field': field_name,
                            'legacy_value': str(legacy_val)[:100] if len(str(legacy_val)) <= 100 else str(legacy_val)[:100] + '...',
                            'new_value': str(new_val)[:100] if len(str(new_val)) <= 100 else str(new_val)[:100] + '...'
                        })
            
            trace_out()
            return mismatches
            
    except Exception as e:
        error_msg = f"Failed to check account data mismatches: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return []


def get_migration_account_double_check() -> Dict[str, Any]:
    """Get account double check results - bidirectional checks and data integrity verification for accounts.
    
    Returns:
        Dictionary with account double check results
    """
    trace_in()
    try:
        # Check 1: New system accounts without legacy links
        new_orphans = check_new_accounts_without_legacy_link()
        
        # Check 2: Legacy accounts with new_id but no corresponding new system account
        legacy_orphans = check_legacy_accounts_without_new_link()
        
        # Check 3: Data mismatches between legacy and new systems for accounts
        data_mismatches = check_account_data_mismatches()
        
        trace_out()
        return {
            "new_orphans": new_orphans,
            "new_orphan_count": len(new_orphans),
            "legacy_orphans": legacy_orphans,
            "legacy_orphan_count": len(legacy_orphans),
            "data_mismatches": data_mismatches,
            "mismatch_count": len(data_mismatches)
        }
            
    except Exception as e:
        error_msg = f"Failed to get migration account double check: {e}"
        report_error("action", error_msg)
        warn(error_msg)
        trace_out()
        return {"error": str(e)}
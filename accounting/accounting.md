# Accounting System Documentation

This document covers the accounting system implementation in the Foxhouse project. The accounting system is built on top of the Henhouse Page system, using derived classes to implement financial tracking functionality including accounts, statements, transfers, fees, invoices, sales, fiscal periods, and expense categories.

For the core Page system architecture, see `context/page.md`. For the legacy PHP implementation that this system replaces, see `legacy/books/php/`.

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Accounting Modules](#3-accounting-modules)
   - [Account](#account)
   - [Statement](#statement)
   - [Transfer](#transfer)
   - [Fee](#fee)
   - [Invoice](#invoice)
   - [Sale](#sale)
   - [FiscalPeriod](#fiscalperiod)
   - [ExpenseCategory](#expensecategory)
4. [Derived Fields and Recalculation](#4-derived-fields-and-recalculation)
5. [Table View Implementation](#5-table-view-implementation)
6. [MCP Tool Registration](#6-mcp-tool-registration)
7. [TypeScript Frontend](#7-typescript-frontend)
8. [Lifecycle Hooks](#8-lifecycle-hooks)
9. [Legacy System Reference](#9-legacy-system-reference)

## Agent Quick Reference

- **Location**: All accounting modules are in `ext/` folder (project-specific, not framework)
- **Base Class**: All accounting classes extend `Page` from `hh/page/page.py`
- **Metadata Storage**: All custom fields stored in `metadata` JSON field, automatically extracted as attributes
- **Modification Methods**: Each module has grouped modification methods matching legacy PHP patterns
- **Derived Fields**: Computed fields (e.g., `balanced`, `totalIncoming`) use lazy computation pattern
- **Table Views**: All modules default to table view with `getChildrenOf(view_type='table')`
- **MCP Tools**: All modification methods registered as MCP tools with tiers `[3, 4, 7, 8]` for dual-purpose (MCP + App Actions)
- **TypeScript**: Client-side forms use `PageData` classes with `processOperationsIncrementally()` for multi-field updates
- **Legacy Reference**: Original PHP implementation in `legacy/books/php/` (Account.php, Statement.php, etc.)

---

## 1. Overview

The accounting system provides comprehensive financial tracking capabilities:

- **Accounts**: Financial accounts (cash, checking, savings, credit, etc.) that contain statements
- **Statements**: Account statements with date ranges, balances, and calculated totals
- **Transfers**: Money transfers between accounts, invoices, or sales
- **Fees**: Fees charged on statements
- **Invoices**: Money going out (expenses) organized by expense categories
- **Sales**: Money coming in (revenue) with customer information
- **FiscalPeriods**: Time periods for organizing financial data
- **ExpenseCategory**: Categories for organizing invoices

All modules follow consistent patterns:
- Extend the base `Page` class
- Store custom fields in `metadata` JSON field
- Provide grouped modification methods matching legacy PHP behavior
- Support derived field calculation with lazy computation
- Default to table view for child listings
- Register MCP tools for programmatic access
- Include TypeScript frontend for web UI

---

## 2. Architecture

### Design Principles

1. **Page-Based Hierarchy**: All accounting entities are pages in the page hierarchy
   - Accounts are children of root pages
   - Statements are children of accounts
   - Transfers and fees are children of statements
   - Invoices are children of expense categories
   - Sales are children of root pages

2. **Metadata Storage**: Custom fields stored in `metadata` JSON field
   - Automatically extracted as object attributes by `Page.__init__()`
   - Accessed directly as `self.field_name`
   - Modified via `self.set_metadata_value('field_name', value)`

3. **Grouped Modification Methods**: Fields grouped into logical modification methods
   - Matches legacy PHP method grouping
   - Example: `modify_statement_info()` handles `startDate`, `endDate`, `openingBalance`, `closingBalance`
   - Example: `modify_finance_info()` handles `interestEarned`, `financeCharge`

4. **Derived Fields**: Computed fields use lazy computation pattern
   - Check if field is at default value (0.0, False, empty string)
   - If default, trigger `recalculateGeneratedValues()`
   - Cache refresh flagged if values change from defaults

5. **Table View Default**: All modules default to table view
   - `getChildrenOf(view_type='table')` is the default
   - Can switch to `view_type='tile'` if needed
   - Table view shows relevant fields in structured format

### File Structure

Each accounting module follows this structure:

```
ext/{module_name}/
  ├── {module_name}.py          # Main class definition
  ├── modify_*.py               # Action scripts for modification methods
  ├── render_show_{module}.py   # Parser registration for display
  ├── tools.py              # MCP tool registration
  └── config_labels.py          # Label and icon registration
```

TypeScript frontend files:
```
ext/deploy/site/ts/page-classes/
  ├── {module}-page-data.ts     # PageData class with field mappings and handlers
```

---

## 3. Accounting Modules

### Account

**File**: `ext/account/account.py`  
**Legacy Reference**: `legacy/books/php/Account.php`

**Purpose**: Financial accounts (cash, checking, savings, credit, loan, etc.)

**Metadata Fields**:
- `type` (str): Account type (cash, checking, savings, online, credit, loan, service, person, open order, lease, sublet, house fund)

**Modification Methods**:
- `modify_account_type(account_type: str)`: Set account type

**Validation**:
- Account type must be one of the allowed values (hardcoded in action script)
- Accounts can only contain statements
- Accounts can be inside root pages

**Table View Fields**:
- `type`: Account type
- `name`: Account name
- Ordered by type (using FIELD ordering), then name

**MCP Tool**: `modify_account_type` (tiers: [3, 4, 7, 8])

---

### Statement

**File**: `ext/statement/statement.py`  
**Legacy Reference**: `legacy/books/php/Statement.php`

**Purpose**: Account statements with date ranges, balances, and calculated totals

**Metadata Fields**:
- `startDate` (str): Statement start date (YYYY-MM-DD)
- `endDate` (str): Statement end date (YYYY-MM-DD)
- `openingBalance` (float): Opening balance
- `closingBalance` (float): Closing balance
- `interestEarned` (float): Interest earned during period
- `financeCharge` (float): Finance charge during period

**Derived Fields** (computed by `recalculateGeneratedValues()`):
- `totalIncoming` (float): Total incoming transfers
- `totalOutgoing` (float): Total outgoing transfers
- `totalFees` (float): Total fees paid
- `unaccountedMoney` (float): Difference between expected and actual balance
- `balanced` (bool): Whether statement balances correctly

**Modification Methods**:
- `modify_statement_info(startDate, endDate, openingBalance, closingBalance)`: Set statement period and balances
- `modify_finance_info(interestEarned, financeCharge)`: Set interest and finance charge

**Validation**:
- Dates must be in YYYY-MM-DD format
- Currency values normalized to 2 decimal places
- Statements can only contain transfers and fees
- Statements can only be inside accounts

**Table View Fields**:
- `startDate`, `endDate`: Date range
- `openingBalance`, `closingBalance`: Balances
- `totalIncoming`, `interestEarned`: Income
- `totalOutgoing`, `totalFees`, `financeCharge`: Expenses
- `unaccountedMoney`: Discrepancy
- Ordered by `startDate` DESC
- Row class: `statement_red` if not balanced, `statement` if balanced

**MCP Tools**: `modify_statement_info`, `modify_finance_info` (tiers: [3, 4, 7, 8])

---

### Transfer

**File**: `ext/transfer/transfer.py`  
**Legacy Reference**: `legacy/books/php/Transfer.php`

**Purpose**: Money transfers between accounts, invoices, or sales

**Metadata Fields**:
- `date` (str): Transfer date (YYYY-MM-DD)
- `amount` (float): Transfer amount (can be negative)
- `fee` (float): Transfer fee
- `transferTo` (Optional[int]): Target page ID (statement, sale, or invoice)

**Modification Methods**:
- `modify_transfer_info(date, amount, modifier, fee)`: Set transfer date, amount, modifier, and fee
- `modify_target_info(transfer_to)`: Set transfer target (statement, sale, or invoice)

**Validation**:
- Date must be in YYYY-MM-DD format
- Currency values normalized to 2 decimal places
- `transferTo` must be valid page ID of type statement, sale, or invoice
- `transferTo` can be empty string to clear target
- Transfers cannot contain any child pages
- Transfers can be inside statements, sales, or invoices

**Special Behavior**:
- When `transferTo` changes, recalculates both old and new target pages
- Recalculates parent page (statement) when transfer is modified

**Table View Fields**:
- `date`: Transfer date
- `reference`: Reference from parent page (account name for statement transfers, invoice/sale name for others)
- `amount`: Gross amount
- `fee`: Transfer fee
- `net`: Net amount (amount - fee)
- `text`: Comments
- Ordered by date, id

**MCP Tools**: `modify_transfer_info`, `modify_target_info` (tiers: [3, 4, 7, 8])

---

### Fee

**File**: `ext/fee/fee.py`  
**Legacy Reference**: `legacy/books/php/Fee.php`

**Purpose**: Fees charged on statements

**Metadata Fields**:
- `date` (str): Fee date (YYYY-MM-DD)
- `fee` (float): Fee amount

**Modification Methods**:
- `modify_fee_info(fee, date)`: Set fee amount and date

**Validation**:
- Date must be in YYYY-MM-DD format
- Currency values normalized to 2 decimal places
- Fees cannot contain any child pages
- Fees can only be inside statements

**Special Behavior**:
- Recalculates parent page (statement) when fee is modified

**Table View Fields**:
- `date`: Fee date
- `fee`: Fee amount
- `text`: Comments
- Ordered by date, id

**MCP Tool**: `modify_fee_info` (tiers: [3, 4, 7, 8])

---

### Invoice

**File**: `ext/invoice/invoice.py`  
**Legacy Reference**: `legacy/books/php/Invoice.php`

**Purpose**: Money going out (expenses) organized by expense categories

**Metadata Fields**:
- `date` (str): Invoice date (YYYY-MM-DD)
- `reference` (Optional[str]): Invoice reference number
- `total` (float): Total amount
- `tax` (float): Tax amount
- `shipping` (float): Shipping amount

**Derived Fields** (computed by `recalculateGeneratedValues()`):
- `balanced` (bool): Whether invoice is balanced (transfers match total)

**Modification Methods**:
- `modify_invoice_info(date, reference)`: Set invoice date and reference
- `modify_invoice_cost_breakdown(total, tax, shipping)`: Set cost breakdown

**Validation**:
- Date must be in YYYY-MM-DD format
- Currency values normalized to 2 decimal places
- `reference` is optional
- Invoices can only contain transfers
- Invoices can only be inside expense categories

**Table View Fields**:
- `date`: Invoice date
- `reference`: Invoice reference
- `subtotal`: Subtotal (total - tax - shipping)
- `shipping`: Shipping amount
- `tax`: Tax amount
- `total`: Total amount
- `text`: Comments
- Ordered by date DESC, reference, total DESC
- Row class: `invoice_red` if not balanced, `invoice` if balanced

**MCP Tools**: `modify_invoice_info`, `modify_invoice_cost_breakdown` (tiers: [3, 4, 7, 8])

---

### Sale

**File**: `ext/sale/sale.py`  
**Legacy Reference**: `legacy/books/php/Sale.php`

**Purpose**: Money coming in (revenue) with customer information

**Metadata Fields**:
- `receiptNum` (Optional[str]): Receipt number
- `date` (str): Sale date (YYYY-MM-DD)
- `saleType` (str): Sale type (retail, wholesale, consignment, royalty, service, advance, account, refund, other, capital-gain, gift, sublet, employment, asset sale)
- `customerName` (Optional[str]): Customer name
- `address` (Optional[str]): Customer address
- `city` (Optional[str]): Customer city
- `state` (Optional[str]): Customer state
- `postalCode` (Optional[str]): Customer postal code
- `country` (Optional[str]): Customer country
- `total` (float): Total amount
- `tax` (float): Tax amount
- `shipping` (float): Shipping amount

**Derived Fields** (computed by `recalculateGeneratedValues()`):
- `balanced` (bool): Whether sale is balanced (transfers match total, with saleType-specific logic)

**Modification Methods**:
- `modify_sale_info(date, receiptNum, saleType)`: Set sale date, receipt number, and sale type
- `modify_customer_info(customerName, address, city, state, postalCode, country)`: Set customer information
- `modify_sale_cost_breakdown(total, tax, shipping)`: Set cost breakdown

**Validation**:
- Date must be in YYYY-MM-DD format
- Currency values normalized to 2 decimal places
- `saleType` must be one of the allowed values (hardcoded in action script)
- All customer fields are optional
- Sales can only contain transfers
- Sales can be inside root pages

**Special Behavior**:
- `balanced` calculation varies by `saleType`:
  - `advance`: `total == outgoing == incoming`
  - `refund`: `(total * -1) == outgoing == incoming`
  - Others: `total == (outgoing - incoming)`

**Table View Fields**:
- `receiptNum`: Receipt number
- `date`: Sale date
- `saleType`: Sale type
- `customerName`: Customer name
- `subtotal`: Subtotal (total - tax - shipping)
- `shipping`: Shipping amount
- `tax`: Tax amount
- `total`: Total amount
- `text`: Comments
- Ordered by date DESC, receiptNum DESC, saleType, id DESC
- Row class: `sale_red` if not balanced, `sale` if balanced

**MCP Tools**: `modify_sale_info`, `modify_customer_info`, `modify_sale_cost_breakdown` (tiers: [3, 4, 7, 8])

---

### FiscalPeriod

**File**: `ext/fiscal_period/fiscal_period.py`  
**Legacy Reference**: `legacy/books/php/FiscalPeriod.php`

**Purpose**: Time periods for organizing financial data

**Metadata Fields**:
- `startDate` (str): Period start date (YYYY-MM-DD)
- `endDate` (str): Period end date (YYYY-MM-DD)

**Modification Methods**:
- `modify_fiscal_period_info(startDate, endDate)`: Set period date range

**Validation**:
- Dates must be in YYYY-MM-DD format
- Fiscal periods can contain invoices and sales
- Fiscal periods can be inside root pages

**MCP Tool**: `modify_fiscal_period_info` (tiers: [3, 4, 7, 8])

---

### ExpenseCategory

**File**: `ext/expense_category/expense_category.py`  
**Legacy Reference**: `legacy/books/php/ExpenseCategory.php`

**Purpose**: Categories for organizing invoices

**Metadata Fields**: None (basic page with no custom fields)

**Validation**:
- Expense categories can only contain invoices
- Expense categories can be inside root pages

**Note**: This is a minimal module that primarily serves as a container for invoices. It has no custom fields or modification methods beyond standard page operations.

---

## 4. Derived Fields and Recalculation

Several accounting modules have **derived fields** that are computed from other data rather than being directly set by users.

### Lazy Computation Pattern

Derived fields use a lazy computation pattern:

1. In `_after_metadata_extraction()` hook, check if derived fields are at default values (0.0, False, empty string)
2. If defaults detected, call `recalculateGeneratedValues()`
3. After recalculation, if values changed from defaults, call `_flag_cache_refresh()`
4. Cache refresh happens during gateway commit, writing updated values to cache database

This ensures:
- Derived fields are only computed when needed
- Cache is refreshed only when values actually change
- No unnecessary recalculation on every page load

### Statement Derived Fields

**Computed by**: `Statement.recalculateGeneratedValues()`

- `totalIncoming`: Sum of incoming transfers (transfers where `transferTo = statement.id`)
- `totalOutgoing`: Sum of outgoing transfers (transfers where `parent = statement.id` and `transferTo` is valid)
- `totalFees`: Sum of fees (fees where `parent = statement.id`)
- `unaccountedMoney`: `(openingBalance + totalIncoming + interestEarned) - (totalOutgoing + totalFees + financeCharge + closingBalance)`
- `balanced`: `unaccountedMoney == 0.0`

**Propagation**: When transfers or fees are modified, they trigger recalculation of their parent statement.

### Invoice Derived Fields

**Computed by**: `Invoice.recalculateGeneratedValues()`

- `balanced`: `(total + totalOutgoing - totalIncoming + totalIncomingFees) == 0.0`
  - `totalIncoming`: Sum of incoming transfers (transfers where `transferTo = invoice.id`)
  - `totalOutgoing`: Sum of outgoing transfers (transfers where `parent = invoice.id` and `transferTo` is valid)
  - `totalIncomingFees`: Sum of fees from incoming transfers

**Propagation**: When transfers are modified or `transferTo` changes, affected invoices are recalculated.

### Sale Derived Fields

**Computed by**: `Sale.recalculateGeneratedValues()`

- `balanced`: Calculated based on `saleType`:
  - `advance`: `total == outgoing == incoming`
  - `refund`: `(total * -1) == outgoing == incoming`
  - Others: `total == (outgoing - incoming)`

**Propagation**: When transfers are modified or `transferTo` changes, affected sales are recalculated.

### Recalculation Triggers

Recalculation is triggered in several scenarios:

1. **Lazy computation**: When page is loaded and derived fields are at defaults
2. **Explicit calls**: Action scripts call `page.recalculateGeneratedValues()` after modifications
3. **Lifecycle hooks**: `_after_copy_page()`, `_after_move_page()`, `_before_delete_page()`, `_after_delete_page()` trigger recalculation on affected pages
4. **Transfer target changes**: When `transferTo` changes, both old and new targets are recalculated

---

## 5. Table View Implementation

All accounting modules default to **table view** for displaying child pages, matching the legacy PHP system's table layouts.

### Implementation Pattern

Each module implements:

1. **`getChildrenOf(parent_id, view_type='table')`**: Class method that queries and formats children
   - Default `view_type='table'` (can switch to `'tile'`)
   - For table view: calls `_get_child_page_data()` and adds `num_children`, `field_type`, `_format='table'`
   - For tile view: adds `display_name`, `images`, `_format='tile'`

2. **`_get_child_page_data()`**: Instance method that returns data dictionary for table rows
   - Includes all fields needed for table display
   - May trigger derived field calculation if needed

3. **`_get_child_row_field_type()`**: Instance method that returns CSS class for row styling
   - Used to apply conditional styling (e.g., `statement_red` if not balanced)

### Table View Fields by Module

- **Account**: `type`, `name` (ordered by type, then name)
- **Statement**: `startDate`, `endDate`, `openingBalance`, `totalIncoming`, `interestEarned`, `totalOutgoing`, `totalFees`, `financeCharge`, `unaccountedMoney`, `closingBalance` (ordered by `startDate` DESC)
- **Transfer**: `date`, `reference`, `amount`, `fee`, `net`, `text` (ordered by date, id)
- **Fee**: `date`, `fee`, `text` (ordered by date, id)
- **Invoice**: `date`, `reference`, `subtotal`, `shipping`, `tax`, `total`, `text` (ordered by date DESC, reference, total DESC)
- **Sale**: `receiptNum`, `date`, `saleType`, `customerName`, `subtotal`, `shipping`, `tax`, `total`, `text` (ordered by date DESC, receiptNum DESC, saleType, id DESC)

### Row Styling

Some modules use conditional row styling:
- **Statement**: `statement_red` if not balanced, `statement` if balanced
- **Invoice**: `invoice_red` if not balanced, `invoice` if balanced
- **Sale**: `sale_red` if not balanced, `sale` if balanced

This matches the legacy PHP system's red highlighting for unbalanced items.

---

## 6. MCP Tool Registration

All modification methods are registered as **MCP tools** for programmatic access via the MCP backend.

### Registration Pattern

Each module has an `tools.py` file that registers tools using the `@register_mcp_tool` decorator:

```python
@register_mcp_tool(
    inputSchema={
        'page_id': {'type': 'integer'},
        'field1': {'type': 'string'},
        'field2': {'type': 'number'},
    },
    description='Modify module information',
    crud_type='update',
    requires_approval=False,
    tiers=[3, 4, 7, 8],  # Dual-purpose: MCP + App Actions
    app_action_group='module_name',
    app_action_label='Edit Module Info'
)
def modify_module_info(page_id: int, field1: str, field2: float) -> bool:
    # Implementation
```

### Tier Configuration

All accounting modification tools use **tiers `[3, 4, 7, 8]`**:
- **Tiers 3, 4**: MCP access (admin MCP, root MCP)
- **Tiers 7, 8**: App Actions (admin app, root app)

This provides dual-purpose tools that work both as MCP tools and as clickable actions in the web UI.

### App Action Metadata

Tools that use tiers 7 or 8 must include:
- `app_action_group`: Group name for organizing actions (e.g., 'statement', 'invoice')
- `app_action_label`: Display label for the action (e.g., 'Edit Statement Info')

### Tool List

- **Account**: `modify_account_type`
- **Statement**: `modify_statement_info`, `modify_finance_info`
- **Transfer**: `modify_transfer_info`, `modify_target_info`
- **Fee**: `modify_fee_info`
- **Invoice**: `modify_invoice_info`, `modify_invoice_cost_breakdown`
- **Sale**: `modify_sale_info`, `modify_customer_info`, `modify_sale_cost_breakdown`
- **FiscalPeriod**: `modify_fiscal_period_info`

---

## 7. TypeScript Frontend

The web UI uses **TypeScript PageData classes** to provide interactive forms for editing accounting data.

### File Structure

TypeScript files are in `ext/deploy/site/ts/page-classes/`:
- `account-page-data.ts`
- `statement-page-data.ts`
- `transfer-page-data.ts`
- `fee-page-data.ts`
- `invoice-page-data.ts`
- `sale-page-data.ts`
- `fiscal-period-page-data.ts`
- `expense-category-page-data.ts`

### PageData Pattern

Each module has a `PageData` class that:

1. **Extends base PageData**: Inherits from the base `PageData` class
2. **Defines field mappings**: `getFieldMappings()` returns field-to-action mappings
3. **Implements handlers**: Handler methods call MCP tools via RPC

### Field Mappings

Fields are mapped to modification methods:

```typescript
getFieldMappings(): FieldMapping[] {
    return [
        { field: 'startDate', action: 'modify_statement_info' },
        { field: 'endDate', action: 'modify_statement_info' },
        { field: 'openingBalance', action: 'modify_statement_info' },
        { field: 'closingBalance', action: 'modify_statement_info' },
        { field: 'interestEarned', action: 'modify_finance_info' },
        { field: 'financeCharge', action: 'modify_finance_info' },
    ];
}
```

### Multi-Field Updates

For grouped modification methods (e.g., `modify_statement_info` handles multiple fields), handlers use `processOperationsIncrementally()`:

```typescript
async modify_statement_info(fields: { startDate?: string, endDate?: string, ... }): Promise<void> {
    await this.processOperationsIncrementally(
        'modify_statement_info',
        fields,
        ['startDate', 'endDate', 'openingBalance', 'closingBalance']
    );
}
```

This provides incremental feedback as each field is updated.

### Combo Handlers

Some modules have "combo" handlers that update multiple fields at once:
- **Statement**: `modify_statement_info()` updates 4 fields, `modify_finance_info()` updates 2 fields
- **Invoice**: `modify_invoice_info()` updates 2 fields, `modify_invoice_cost_breakdown()` updates 3 fields
- **Sale**: `modify_sale_info()` updates 3 fields, `modify_customer_info()` updates 6 fields, `modify_sale_cost_breakdown()` updates 3 fields

---

## 8. Lifecycle Hooks

Accounting modules use **lifecycle hooks** to trigger recalculation when pages are copied, moved, or deleted.

### Hook Implementation

Modules implement these hooks from the base `Page` class:

- `_after_add_page(new_page_id)`: Initialize metadata defaults
- `_after_copy_page(new_page_id)`: Recalculate new page and new parent
- `_after_move_page(old_parent_id, new_parent_id)`: Recalculate self, old parent, new parent
- `_before_delete_page()`: Capture parent for later recalculation
- `_after_delete_page()`: Recalculate old parent

### Recalculation Propagation Rules

**Statement, Invoice, Sale**:
- **Copy**: Recalculate new page and new parent
- **Move**: Recalculate self, old parent, new parent
- **Delete**: Recalculate old parent

**Transfer**:
- **Copy**: Recalculate new parent and new target (if `transferTo` is set)
- **Move**: Recalculate old parent and new parent (target not recalculated)
- **Delete**: Recalculate old parent and old target (if `transferTo` is set)

**Fee**:
- **Copy**: Recalculate new parent
- **Move**: Recalculate old parent and new parent
- **Delete**: Recalculate old parent

### Special Cases

- **Transfer target changes**: When `modify_target_info()` changes `transferTo`, it explicitly recalculates:
  - Old target page (if exists and different from new)
  - New target page (if exists)
  - Parent page (statement)

This ensures all affected pages have up-to-date derived values.

---

## 9. Legacy System Reference

The accounting system is a Python port of the legacy PHP system. The original implementation is in `legacy/books/php/`:

- **Account.php**: Account management with type-based grouping
- **Statement.php**: Statement management with calculated totals
- **Transfer.php**: Transfer management with incoming/outgoing views
- **Fee.php**: Fee management
- **Invoice.php**: Invoice management with expense category organization
- **Sale.php**: Sale management with customer information
- **FiscalPeriod.php**: Fiscal period management
- **ExpenseCategory.php**: Expense category container

### Key Differences

1. **Database Schema**: Legacy system used separate tables (`accounts`, `statements`, `transfers`, etc.). New system uses single `pages` table with `metadata` JSON field.

2. **Metadata Storage**: Legacy system had dedicated columns. New system uses JSON metadata with automatic attribute extraction.

3. **Method Grouping**: Both systems use grouped modification methods, but Python uses snake_case while PHP used camelCase.

4. **Derived Field Calculation**: Both systems compute derived fields, but Python uses lazy computation pattern while PHP computed on-demand.

5. **Table Views**: Both systems default to table view, but Python uses `getChildrenOf()` class method while PHP used static `getChildrenOf()` function.

### Migration Notes

When migrating data from legacy system:
- Account `type` maps directly
- Statement fields map directly (dates, balances, interest, finance charge)
- Transfer fields map directly (date, amount, fee, transferTo)
- Fee fields map directly (date, fee)
- Invoice fields map directly (date, reference, total, tax, shipping)
- Sale fields map directly (all customer and cost fields)
- FiscalPeriod fields map directly (startDate, endDate)

Derived fields (`balanced`, `totalIncoming`, etc.) are recomputed automatically on first access.

---

## Summary

The accounting system provides comprehensive financial tracking built on the Henhouse Page system. All modules follow consistent patterns:

- Extend `Page` base class
- Store custom fields in `metadata` JSON
- Provide grouped modification methods
- Support derived field calculation
- Default to table view
- Register MCP tools for programmatic access
- Include TypeScript frontend for web UI
- Use lifecycle hooks for recalculation propagation

The system matches the legacy PHP implementation's functionality while leveraging the modern Henhouse architecture for better maintainability and extensibility.


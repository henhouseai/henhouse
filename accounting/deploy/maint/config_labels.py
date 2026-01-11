"""Config labels for migration daemon."""

from hh.render.config.config_registry import register_label

@register_label('migration_status_header', 'Migration Status', '🔄')
@register_label('migration_daemon_header', 'Migration Daemon', '🔄')
@register_label('migration_double_check_header', 'Migration Double Check', '🔍')
@register_label('migration_account_double_check_header', 'Migration Account Double Check', '🔍')
@register_label('migration_start_header', 'Migration Start', '▶️')
@register_label('migration_stop_header', 'Migration Stop', '⏸️')
@register_label('migration_add_phase_header', 'Migration Add Phase', '➕')
@register_label('migration_set_phase_status_header', 'Migration Set Phase Status', '✏️')
# Note: orphan_pages is already registered in hh.deploy.maint.config_labels
@register_label('orphan_accounts', 'Accounts Missing Pages', '💰')
@register_label('orphan_statements', 'Statements Missing Pages', '📊')
@register_label('orphan_transfers', 'Transfers Missing Pages', '💸')
@register_label('orphan_fees', 'Fees Missing Pages', '💳')
@register_label('orphan_invoices', 'Invoices Missing Pages', '🧾')
@register_label('orphan_sales', 'Sales Missing Pages', '🛒')
@register_label('orphan_fiscalPeriods', 'Fiscal Periods Missing Pages', '📅')
@register_label('unexpected_page_classes', 'Pages with Unexpected Classes', '🚨')
def _register_config():
    pass


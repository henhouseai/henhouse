from hh.render.config.config_registry import register_label

@register_label('page_class_statement',                'Statement:',                  '📊')
@register_label('page_openingBalance',                 'Opening Balance:',            '💰')
@register_label('page_closingBalance',                 'Closing Balance:',            '💰')
@register_label('page_interestEarned',                'Interest Earned:',            '💵')
@register_label('page_financeCharge',                  'Finance Charge:',             '💳')
@register_label('page_totalIncoming',                  'Total Incoming:',            '⬆️')
@register_label('page_totalOutgoing',                  'Total Outgoing:',            '⬇️')
@register_label('page_totalFees',                      'Total Fees:',                 '💳')
@register_label('page_unaccountedMoney',               'Unaccounted Money:',          '❓')
def _register_config():
    pass


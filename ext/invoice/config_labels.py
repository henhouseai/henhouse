from hh.render.config.config_registry import register_label

@register_label('page_class_invoice',                  'Invoice:',                    '📄')
@register_label('page_reference',                      'Reference:',                  '🔖')
@register_label('page_total',                          'Total:',                      '💰')
@register_label('page_tax',                            'Tax:',                        '📊')
@register_label('page_shipping',                       'Shipping:',                   '📦')
@register_label('page_balanced',                       'Balanced:',                   '✅')
def _register_config():
    pass


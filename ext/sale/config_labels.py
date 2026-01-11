from hh.render.config.config_registry import register_label

@register_label('page_class_sale',                     'Sale:',                       '💵')
@register_label('page_receiptNum',                     'Receipt #:',                  '🧾')
@register_label('page_saleType',                       'Sale Type:',                  '📋')
@register_label('page_customerName',                  'Customer Name:',              '👤')
@register_label('page_address',                        'Address:',                    '📍')
@register_label('page_city',                           'City:',                       '📍')
@register_label('page_state',                          'State:',                      '📍')
@register_label('page_postalCode',                     'Postal Code:',               '📮')
@register_label('page_country',                        'Country:',                   '🌍')
def _register_config():
    pass


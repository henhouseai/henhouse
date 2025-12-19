from hh.render.config.config_registry import register_label

@register_label('page_status',                      'Status:',                    '📊')
@register_label('page_sort_order',                  'Sort Order:',                '🔢')
@register_label('page_started_ts',                 'Started:',                   '⬜')
@register_label('page_ended_ts',                    'Ended:',                     '✅')
def _register_config():
    pass

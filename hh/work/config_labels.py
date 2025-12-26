from hh.render.config.config_registry import register_label

@register_label('page_status',                      'Status:',                    '📊')
@register_label('page_sort_order',                  'Sort Order:',                '🔢')
@register_label('page_started_ts',                 'Started:',                   '⬜')
@register_label('page_ended_ts',                    'Ended:',                     '✅')
@register_label('work_log',                         'Work Log',                   '📝')
@register_label('work_meta',                        'Work Meta',                  '🧠')
@register_label('work_files_touched',               'Files Touched',              '📁')
@register_label('work_deviations',                  'Deviations',                 '🚨')
def _register_config():
    pass

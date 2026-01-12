from hh.render.config.config_registry import register_label

@register_label('page_status',                      'Status:',                    '📊')
@register_label('page_sort_order',                  'Sort Order:',                '🔢')
@register_label('page_started_ts',                 'Started:',                   '⬜')
@register_label('page_ended_ts',                    'Ended:',                     '✅')
@register_label('work_log',                         'Work Log',                   '📝')
@register_label('work_meta',                        'Work Meta',                  '🧠')
@register_label('work_files_touched',               'Files Touched',              '📁')
@register_label('work_deviations',                  'Deviations',                 '🚨')
@register_label('l_modify_work_meta_header',        'Work Meta Modification'           )
@register_label('work_meta_action',                 'Action:',                    '⚡')
@register_label('work_meta_field',                  'Field:',                     '📋')
@register_label('work_meta_success',                'Success:',                   '✅')
@register_label('work_meta_new_values',             'New Values:',                '📝')
@register_label('work_meta_removed_keys',           'Removed Keys:',              '🗑️')
@register_label('l_modify_work_status_header',      'Work Status Modification'         )
@register_label('work_status_new_status',           'New Status:',                '📊')
@register_label('work_status_old_status',           'Old Status:',                '📊')
@register_label('work_status_success',              'Success:',                   '✅')
def _register_config():
    pass

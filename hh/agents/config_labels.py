from hh.render.config.config_registry import register_label

@register_label('agent_list_header',                  'Agent List',                   '📋')
@register_label('agent_id',                           'Agent ID:',                    '🤖')
@register_label('agent_name',                         'Agent Name:',                  '🤖')
@register_label('filters',                           'Filters:',                    '🔍')
@register_label('gate_status',                        'Gate Status:',                 '🚪')
@register_label('terminated',                         'Terminated:',                  '🚫')
@register_label('purge',                              'Purge:',                      '🗑️')
@register_label('operation',                          'Operation:',                  '🔗')
@register_label('status_active',                      'Status:',                      '🟢')
@register_label('status_inactive',                    'Status:',                      '🔴')
@register_label('gate_started_ts',                    'Gate Started:',                '⏰')
@register_label('role_terminated',                    'Role:',                        '👤')
@register_label('session_id',                         'Session ID:',                  '🔗')
@register_label('runs',                               'Runs:',                        '🏃')
@register_label('role_active',                        'Role:',                        '👤')
@register_label('role_inactive',                      'Role:',                        '👤')
@register_label('agent',                              'Agent:',                       '🤖')
@register_label('purge_header',                       'Agent Purge'                   )
@register_label('timeclock_header',                   'Timeclock Punch'               )
def _register_config():
    pass


from hh.render.config.config_registry import register_label

@register_label('install_header',                      'Installation Status',            '🔧')
@register_label('groups_created',                      'Groups Created:',                '👥')
@register_label('users_created',                       'Users Created:',                 '👤')
@register_label('ssh_keys',                            'SSH Keys:',                      '🔑')
@register_label('human_scripts',                       'Human Scripts:',                 '📜')
@register_label('root_scripts',                        'Root Scripts:',                  '👑')
@register_label('ownership',                           'Project Ownership:',              '👑')
@register_label('uninstall_header',                    'Uninstall Status',               '🗑️')
@register_label('users_removed',                       'Users Removed:',                 '👤')
@register_label('project_directory',                    'Project Directory:',              '📁')
@register_label('groups_deleted',                      'Groups Deleted:',                '👥')
@register_label('safety_checks',                       'Safety Checks:',                 '🔍')
@register_label('install_cursor_header',                'Cursor Installation Status',      '💻')
@register_label('users_processed',                      'Users Processed:',               '👥')
@register_label('success_count',                        'Successful:',                     '✅')
@register_label('failed_count',                        'Failed:',                         '❌')
@register_label('username',                            'Username:',                       '👤')
@register_label('config_status',                      'Status:',                        '🔸')
@register_label('template_location',                   'Template Location:',              '📁')
@register_label('template_created',                  'Template Created:',               '✅')
@register_label('next_steps',                         'Next Steps:',                    '➡️')
def _register_config():
    pass


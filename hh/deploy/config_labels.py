from hh.render.config.config_registry import register_label

@register_label('project_header',                      'Deployment Status',               '🚀')
@register_label('human_scripts',                       'Human Scripts:',                 '📜')
@register_label('root_scripts',                        'Root Scripts:',                  '👑')
@register_label('ownership',                           'Project Ownership:',              '👑')
@register_label('uninstall_header',                    'Uninstall Status',               '🗑️')
@register_label('project_directory',                    'Project Directory:',              '📁')
@register_label('safety_checks',                       'Safety Checks:',                 '🔍')
@register_label('install_cursor_header',                'Cursor Installation Status',      '💻')
@register_label('success_count',                        'Successful:',                     '✅')
@register_label('failed_count',                        'Failed:',                         '❌')
@register_label('username',                            'Username:',                       '👤')
@register_label('config_status',                      'Status:',                        '🔸')
@register_label('template_location',                   'Template Location:',              '📁')
@register_label('template_created',                  'Template Created:',               '✅')
@register_label('next_steps',                         'Next Steps:',                    '📝')
@register_label('deploy_header',                       'Deploy',                          '🚀')
@register_label('remove_header',                       'Remove',                          '🗑️')
@register_label('install_header',                      'Install',                         '⚙️')
@register_label('install_summary',                     'Installation Summary',            '📋')
def _register_config():
    pass

from hh.render.config.config_registry import register_label

@register_label('upgrade_header',                        'Upgrade Status',                  '⬆️')
@register_label('target_header',                         'Target Project:',                  '📁')
@register_label('backup_created',                        'Backup Created:',                 '💾')
@register_label('context_backup_created',                 'Context Backup Created:',          '📚')
@register_label('file_restored',                         'File Restored:',                  '🔄')
@register_label('backup_reminder',                       'Reminder:',                       '💡')
@register_label('test_reminder',                         'Reminder:',                       '💡')
def _register_config():
    pass


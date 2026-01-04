from hh.render.config.config_registry import register_label

@register_label('upgrade_header',                        'Upgrade Status',                  '⬆️')
@register_label('target_header',                         'Target Project:',                  '📁')
@register_label('backup_created',                        'Backup Created:',                 '💾')
@register_label('context_backup_created',                 'Context Backup Created:',          '📚')
@register_label('file_restored',                         'File Restored:',                  '🔄')
@register_label('backup_reminder',                       'Reminder:',                       '💡')
@register_label('test_reminder',                         'Reminder:',                       '💡')

# Generic difference categories (used for all folders)
@register_label('diff_lost_header',                      'Total lost files',                '❌')
@register_label('diff_lost',                             'Will be lost',                    '❌')
@register_label('diff_restored_header',                  'Total restored files',            '✅')
@register_label('diff_restored',                         'Will be restored',                '✅')
@register_label('diff_created_header',                  'Total created files',             '➕')
@register_label('diff_created',                          'Will be created',                 '➕')
@register_label('diff_updated_header',                  'Total updated files',             '🔄')
@register_label('diff_updated',                          'Will be updated',                 '🔄')
@register_label('diff_preserved_header',                 'Total preserved files',           '❌')
@register_label('diff_preserved',                        'Would be updated but preserved',  '❌')
def _register_config():
    pass


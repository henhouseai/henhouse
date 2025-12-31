from hh.render.config.config_registry import register_label

@register_label('upgrade_header',                        'Upgrade Status',                  '⬆️')
@register_label('target_header',                         'Target Project:',                  '📁')
@register_label('backup_created',                        'Backup Created:',                 '💾')
@register_label('context_backup_created',                 'Context Backup Created:',          '📚')
@register_label('file_restored',                         'File Restored:',                  '🔄')
@register_label('backup_reminder',                       'Reminder:',                       '💡')
@register_label('test_reminder',                         'Reminder:',                       '💡')

# HH folder difference categories
@register_label('hh_diff_header',                        'hh/ folder differences',          '📁')
@register_label('hh_diff_lost_header',                   'Will be lost',                    '❌')
@register_label('hh_diff_lost',                          '',                                '')
@register_label('hh_diff_restored_header',                'Will be restored',                '✅')
@register_label('hh_diff_restored',                      '',                                '')
@register_label('hh_diff_created_header',                'Will be created',                 '➕')
@register_label('hh_diff_created',                       '',                                '')
@register_label('hh_diff_updated_header',                 'Will be updated',                 '🔄')
@register_label('hh_diff_updated',                       '',                                '')
@register_label('hh_diff_preserved_header',              'Would be updated but preserved',  '❌')
@register_label('hh_diff_preserved',                     '',                                '')

# Context folder difference categories
@register_label('context_diff_header',                   'context/ folder differences',     '📚')
@register_label('context_diff_lost_header',               'Will be lost',                    '❌')
@register_label('context_diff_lost',                     '',                                '')
@register_label('context_diff_restored_header',          'Will be restored',                '✅')
@register_label('context_diff_restored',                  '',                                '')
@register_label('context_diff_created_header',            'Will be created',                 '➕')
@register_label('context_diff_created',                   '',                                '')
@register_label('context_diff_updated_header',            'Will be updated',                 '🔄')
@register_label('context_diff_updated',                   '',                                '')
@register_label('context_diff_preserved_header',          'Would be updated but preserved',  '❌')
@register_label('context_diff_preserved',                 '',                                '')
def _register_config():
    pass


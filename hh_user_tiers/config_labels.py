from hh.render.config.config_registry import register_label

@register_label('groups_created',                      'Groups Created:',                '👥')
@register_label('users_created',                       'Users Created:',                 '👤')
@register_label('ssh_keys',                            'SSH Keys:',                      '🔑')
@register_label('users_removed',                       'Users Removed:',                 '👤')
@register_label('groups_deleted',                      'Groups Deleted:',                '👥')
@register_label('users_processed',                      'Users Processed:',               '👥')
def _register_config():
    pass

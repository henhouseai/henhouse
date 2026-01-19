from hh.render.config.config_registry import register_label

# Flask module deployment render labels
@register_label('flask_summary',                       'Flask:',                          '🌐')

# Flask daemon detail table labels
@register_label('flask_detail_header',                 'Flask Daemons',                   '🌐')
@register_label('daemon_guest',                        'Guest',                           '👤')
@register_label('daemon_verified',                     'Verified',                        '✅')
@register_label('daemon_admin',                        'Admin',                           '👑')
@register_label('daemon_root',                         'Root',                            '🔑')
@register_label('daemon_media',                        'Media',                           '🎬')

# Flask removal labels
@register_label('flask_stopped',                       'Flask Stopped',                   '🛑')
@register_label('maintenance_stopped',                 'Maintenance Stopped',             '🛑')
def _register_config():
    pass

from hh.render.config.config_registry import register_label

# Flask daemon detail table labels
@register_label('flask_detail_header',                 'Flask Daemons',                   '🌐')
@register_label('daemon_guest',                        'guest:',                          '👤')
@register_label('daemon_verified',                     'verified:',                       '✅')
@register_label('daemon_admin',                        'admin:',                          '👑')
@register_label('daemon_root',                         'root:',                           '🔑')
@register_label('daemon_media',                        'media:',                          '🎬')
@register_label('deployed_app',                        'Deployed:',                       '📦')
@register_label('media_server',                        'Media Server:',                   '🎬')
def _register_config():
    pass

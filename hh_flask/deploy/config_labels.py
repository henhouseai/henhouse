from hh.render.config.config_registry import register_label

# Flask module deployment render labels
@register_label('flask_summary',                       'Flask:',                          '🌐')

# Flask daemon detail table labels (state-based)
@register_label('flask_detail_header',                 'Flask Daemons',                   '🌐')
@register_label('daemon_started',                      'Started',                         '✅')
@register_label('daemon_stopped',                      'Stopped',                         '🛑')
@register_label('daemon_restarted',                    'Restarted',                       '🔄')

# Flask removal labels
@register_label('flask_stopped',                       'Flask Stopped',                   '🛑')
@register_label('maintenance_stopped',                 'Maintenance Stopped',             '🛑')
def _register_config():
    pass

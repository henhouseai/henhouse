from hh.render.config.config_registry import register_label

# Maintenance summary contribution labels
@register_label('maintenance_summary',                    'Maintenance:',                    '🧰')

# Maintenance daemon detail table labels (state-based)
@register_label('maint_detail_header',                    'Maintenance Daemons',             '🧰')
@register_label('maint_started',                          'Started',                         '✅')
@register_label('maint_stopped',                          'Stopped',                         '🛑')
@register_label('maint_restarted',                        'Restarted',                       '🔄')
@register_label('maint_failed',                           'Failed',                          '❌')
@register_label('maint_error',                            'Error',                           '💥')
def _register_config():
    pass

from hh.render.config.config_registry import register_label

@register_label('maintenance_start_header', 'Maintenance Daemon Start', '🧰')
@register_label('maintenance_stop_header', 'Maintenance Daemon Stop', '🛑')
@register_label('maintenance_status_header', 'Maintenance Daemon Status', '📊')
@register_label('maintenance_header', 'Maintenance', '🧩')
@register_label('maintenance', 'Maintenance', '🧩')


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

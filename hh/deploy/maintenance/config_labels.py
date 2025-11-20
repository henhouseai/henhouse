from hh.render.config.config_registry import register_label

@register_label('maintenance_start_header', 'Maintenance Daemon Start', '🧰')
@register_label('maintenance_stop_header', 'Maintenance Daemon Stop', '🛑')
@register_label('maintenance_status_header', 'Maintenance Daemon Status', '📊')
@register_label('maintenance', 'Maintenance', '🧩')
def _register_config():
    pass



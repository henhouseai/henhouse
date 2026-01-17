from hh.render.config.config_registry import register_label

# Maintenance daemon detail table labels
@register_label('maint_header',                           'Maintenance Daemons',             '🧰')
@register_label('maint_main',                             'main:',                           '🔧')
@register_label('maint_ext',                              'ext:',                            '🔩')
@register_label('deployed_worker',                        'Worker:',                         '⚙️')
def _register_config():
    pass

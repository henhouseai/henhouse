from hh.render.config.config_registry import register_label

@register_label('help_topic',                         'Help:',                        '❓')
@register_label('help_section',                       'Section:',                     '🔸')
@register_label('help_child',                         'Category:',                    '📁')
@register_label('help_file',                          'Command:',                     '📄')
@register_label('help_header',                        'Help System'                    )
def _register_config():
    pass


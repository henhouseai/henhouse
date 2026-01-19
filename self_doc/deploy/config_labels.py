from hh.render.config.config_registry import register_label

# Self-doc module deployment render labels
@register_label('context_summary',                     'Context:',                        '📂')
@register_label('context_detail_header',               'Context Items Deployed',          '📂')
@register_label('context_item',                        'Item:',                           '📄')
def _register_config():
    pass

from hh.render.config.config_registry import register_label

@register_label('ask',                  'Ask:',              '❓')
@register_label('ask_todo',             'Todo Ask:',         '⏳')
@register_label('ask_doing',            'Doing Ask:',        '🔄')
@register_label('ask_review',           'Review Ask:',       '👀')
@register_label('ask_done',             'Done Ask:',         '✅')
def _register_config():
    pass

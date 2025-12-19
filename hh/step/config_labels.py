from hh.render.config.config_registry import register_label

@register_label('step',                  'Step:',              '👣')
@register_label('step_todo',             'Todo Step:',         '⏳')
@register_label('step_doing',            'Doing Step:',        '🔄')
@register_label('step_review',           'Review Step:',       '👀')
@register_label('step_done',             'Done Step:',         '✅')
def _register_config():
    pass

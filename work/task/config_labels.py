from hh.render.config.config_registry import register_label

@register_label('task',                  'Task:',              '📝')
@register_label('task_todo',             'Todo Task:',         '⏳')
@register_label('task_doing',            'Doing Task:',        '🔄')
@register_label('task_review',           'Review Task:',       '👀')
@register_label('task_done',             'Done Task:',         '✅')
def _register_config():
    pass

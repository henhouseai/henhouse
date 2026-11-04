from hh.render.config.config_registry import register_label

@register_label('work_docket',                  'Work Docket:',              '📋')
@register_label('work_docket_todo',             'Todo Work Docket:',         '⏳')
@register_label('work_docket_doing',            'Doing Work Docket:',        '🔄')
@register_label('work_docket_review',            'Review Work Docket:',       '👀')
@register_label('work_docket_done',              'Done Work Docket:',        '✅')
def _register_config():
    pass


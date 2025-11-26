from hh.render.config.config_registry import register_label

@register_label('action_error',                      'Action Error:',                '⚡')
@register_label('backend_error',                      'Backend Error:',               '🔧')
@register_label('request_error',                      'Request Error:',               '📨')
@register_label('registry_error',                     'Registry Error:',              '📋')
@register_label('connection_error',                   'Connection Error:',            '🔌')
@register_label('json_error',                        'JSON Error:',                  '📄')
@register_label('syntax_error',                       'Syntax Error:',                '📝')
@register_label('link_resolution_error',             'Link Resolution Error:',        '🔗')
@register_label('dependency_error',                   'Dependency Error:',            '📦')
@register_label('deployment_error',                   'Deployment Error:',            '🖥️')
@register_label('error_message',                      'Error Message:',               '🚨')
@register_label('error_code',                         'Error Code:',                  '🔢')
@register_label('error_source',                       'Error Source:',                '🎯')
@register_label('retry',                              'Retry:',                       '🔄')
@register_label('retryable',                          'Retryable:',                   '🔄')
def _register_config():
    pass


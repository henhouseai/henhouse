from hh.render.config.config_registry import register_label

@register_label('list',                               'List:',                        '📋')
@register_label('loaded',                             'Loaded:',                      '✅')
@register_label('found',                              'Found:',                       '🔲')
@register_label('failed',                             'Failed:',                      '❌')
@register_label('args',                               'Action Args:',                 '⚙️')
@register_label('function',                           'Function:',                    '🔧')
@register_label('function_name',                      'Function:',                    '🔧')
@register_label('command_list_header',                'Command List:'                 )
@register_label('backend_list_header',                'Backend List:'                 )
@register_label('action_list_header',                 'Action List:'                  )
@register_label('parser_list_header',                 'Parser List:'                  )
@register_label('mcp_list_header',                    'MCP List:'                      )
@register_label('http_list_header',                   'HTTP List:'                    )
def _register_config():
    pass


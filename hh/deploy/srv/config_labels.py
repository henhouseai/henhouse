from hh.render.config.config_registry import register_label

@register_label('project_header',                     'Project:',                        '📁')
@register_label('deploy_header',                      'Deployment Status',               '🚀')
@register_label('code_deployed',                      'Code Deployed:',                  '✅')
@register_label('deployment_cleaned',                 'Deployment Cleaned:',             '🧹')
@register_label('cache_cleaned',                      'Cache Cleaned:',                  '🧹')
@register_label('flask_deployed',                     'Flask App Deployed:',             '🌐')
@register_label('context_deployed',                   'Context Deployed:',               '📂')
@register_label('ownership_set',                      'Ownership Set:',                  '👤')
@register_label('cache_permissions',                  'Cache Permissions:',              '🔒')
@register_label('js_count',                           'JS Files Deployed:',              '📜')
@register_label('css_count',                          'CSS Files Deployed:',             '🎨')
@register_label('misc_count',                         'Misc Files Deployed:',            '📦')
@register_label('flask_restart',                      'Flask Restart:',                 '🔁')
@register_label('maintenance_restart',                'Maintenance Restart:',            '🧰')
@register_label('project_info',                       'Project Info:',                   'ℹ️')
def _register_config():
    pass


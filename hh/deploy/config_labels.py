from hh.render.config.config_registry import register_label

# Deployment summary table header
@register_label('project_header',                      'Deployment Status',               '🚀')

# Deploy, Remove, and Install action headers
@register_label('deploy_header',                       'Deploy',                          '🚀')
@register_label('remove_header',                       'Remove',                          '🗑️')
@register_label('install_header',                      'Install',                         '⚙️')
@register_label('install_summary',                     'Installation Summary',            '📋')
def _register_config():
    pass

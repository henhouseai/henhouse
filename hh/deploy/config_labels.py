from hh.render.config.config_registry import register_label

# Deployment summary table header
@register_label('project_header',                      'Deployment Status',               '🚀')

# Deploy and Remove action headers
@register_label('deploy_header',                       'Deploy',                          '🚀')
@register_label('remove_header',                       'Remove',                          '🗑️')
def _register_config():
    pass

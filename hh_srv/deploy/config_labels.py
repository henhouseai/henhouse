from hh.render.config.config_registry import register_label

# SRV module deployment render labels
@register_label('srv_summary',                         'Server:',                         '🌐')
@register_label('srv_detail_header',                   'Server Infrastructure',           '⚙️')
@register_label('directory_sterilization',             'Directory Sterilization',         '🗑️')
@register_label('site_prepare',                        'Site Prepare',                    '📁')
@register_label('base_permissions',                    'Base Permissions',                '🔒')
@register_label('cache_permissions',                   'Cache Permissions',               '🔑')
@register_label('client_files_deploy',                 'Client Files',                    '📄')
@register_label('site_javascript',                     'Site JavaScript',                 '📜')
@register_label('site_css_deploy',                     'Site CSS',                        '🎨')
@register_label('site_misc_deploy',                    'Site Misc',                       '📦')

# SRV module removal labels
@register_label('srv_removal_summary',                 'Server',                          '🌐')
@register_label('deployment_path',                     'Deployment Path',                 '📁')
@register_label('files_removed',                       'Files Removed',                   '🗑️')
@register_label('manifest_cleared',                    'Manifest Cleared',                '📋')
def _register_config():
    pass

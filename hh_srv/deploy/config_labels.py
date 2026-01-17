from hh.render.config.config_registry import register_label

# Summary table labels
@register_label('project_header',                      'Deployment Status',               '🚀')
@register_label('context_deployed',                    'Context Items:',                  '📂')
@register_label('site_files',                          'Site Files:',                     '🌐')
@register_label('cache_cleaned',                       'Cache Cleaned:',                  '🧹')
@register_label('flask_summary',                       'Flask:',                          '🌐')
@register_label('nginx_summary',                       'NGINX:',                          '🌐')
@register_label('nginx_reloaded',                      'NGINX Reloaded:',                 '🔄')

# Context detail table labels
@register_label('context_detail_header',               'Context Items Deployed',          '📂')
@register_label('context_item',                        'Item:',                           '📄')

# Client files detail table labels
@register_label('client_detail_header',                'Client Files Deployed',           '📋')
@register_label('client_file',                         'File:',                           '📄')


# Permissions detail table labels
@register_label('perms_header',                        'Permissions Set',                 '🔒')
@register_label('perm_row',                            '',                                '🔑')

# Modules detail table labels
@register_label('modules_detail_header',               'Modules Deployed',                '📦')
@register_label('module_item',                         'Module:',                         '📦')

# Site files detail table labels
@register_label('site_detail_header',                  'Site Files Deployed',             '🌐')
@register_label('site_js',                             'JavaScript:',                     '📜')
@register_label('site_css',                            'CSS:',                            '🎨')
@register_label('site_misc',                           'Miscellaneous:',                  '📦')

# Removal summary table labels
@register_label('flask_stopped',                       'Flask Stopped:',                  '🛑')
@register_label('maintenance_stopped',                 'Maintenance Stopped:',            '🛑')
@register_label('domains_removed',                     'Domains Removed:',                '🌐')
@register_label('deployment_path',                     'Deployment Path:',                '📁')
@register_label('files_removed',                       'Files Removed:',                  '🗑️')
@register_label('manifest_cleared',                    'Manifest Cleared:',               '📋')
def _register_config():
    pass

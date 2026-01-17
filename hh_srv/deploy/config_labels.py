from hh.render.config.config_registry import register_label

# Summary table labels
@register_label('project_header',                      'Deployment Status',               '🚀')
@register_label('modules_deployed',                    'Modules Deployed:',               '📦')
@register_label('context_deployed',                    'Context Items:',                  '📂')
@register_label('site_files',                          'Site Files:',                     '🌐')
@register_label('cache_cleaned',                       'Cache Cleaned:',                  '🧹')
@register_label('flask_summary',                       'Flask:',                          '🌐')
@register_label('maintenance_summary',                 'Maintenance:',                    '🧰')
@register_label('nginx_summary',                       'NGINX:',                          '🌐')
@register_label('nginx_reloaded',                      'NGINX Reloaded:',                 '🔄')

# Context detail table labels
@register_label('context_detail_header',               'Context Items Deployed',          '📂')
@register_label('context_item',                        '',                                '📄')

# Client files detail table labels
@register_label('client_detail_header',                'Client Files Deployed',           '📋')
@register_label('client_file',                         '',                                '📄')

# Permissions detail table labels
@register_label('perms_header',                        'Permissions Set',                 '🔒')
@register_label('perm_base',                           'Base:',                           '📁')
@register_label('perm_flask_logs',                     'Flask Logs:',                     '📝')
@register_label('perm_git',                            'Git:',                            '📦')
@register_label('perm_site',                           'Site:',                           '🌐')
@register_label('perm_cache',                          'Cache:',                          '💾')
@register_label('perm_maint_logs',                     'Maintenance Logs:',               '📝')

# Operations detail table labels
@register_label('ops_header',                          'Deployment Operations',           '⚙️')
@register_label('op_git_preserve',                     'Git Preserved:',                  '📦')
@register_label('op_sterilize',                        'Directory Sterilized:',           '🧹')
@register_label('op_git_restore',                      'Git Restored:',                   '📦')
@register_label('op_framework_cleanup',                'Framework Cleaned:',              '🧹')
@register_label('op_site_prepare',                     'Site Directory:',                 '📁')

# Modules detail table labels
@register_label('modules_detail_header',               'Modules Deployed',                '📦')
@register_label('module_item',                         '',                                '📦')

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

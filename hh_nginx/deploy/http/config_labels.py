from hh.render.config.config_registry import register_label

# NGINX module deployment render labels
@register_label('nginx_summary',                      'NGINX:',                         '🌐')
@register_label('domain_setting',                     '',                               '⚙️')

# NGINX-specific HTTP deployment labels
@register_label('http_deploy_header',                 'HTTP Deployment Status',         '🌐')
@register_label('http_deploy_ssl_header',             'HTTP SSL Deployment Status',    '🔒')
@register_label('http_status_header',                 'HTTP Site Deployment Status',    '📊')
@register_label('domain_header',                      'Domain:',                        '🌐')
@register_label('certificate_path',                   'Certificate Path:',              '🔑')
@register_label('nginx_active',                       'Nginx Active:',                  '✅')
@register_label('nginx_deployed',                     'Nginx Config Deployed:',         '🌐')
@register_label('port',                               'Port:',                          '🔌')
@register_label('http_config_path',                   'Config File Path:',              '🌍')
@register_label('main_domain',                        'Main Domain:',                   '🌐')
@register_label('subdomain',                          'Subdomain:',                     '🔗')
@register_label('http_remove_header',                 'HTTP Removal Status',            '🧹')
@register_label('bind_ips',                           'Bound to:',                      '🔗')
@register_label('client_ip_access',                   'Client IP Access:',              '🛡️')
@register_label('nginx_enabled_sites',                'Nginx Enabled Sites:',           '🌐')

# NGINX site listing labels
@register_label('active_henhouse_header',             'Active Henhouse Sites',          '✅')
@register_label('available_henhouse_header',          'Available Henhouse Sites',       '📦')
@register_label('active_other_header',                'Active Other Sites',             '🌍')
@register_label('available_other_header',             'Available Other Sites',          '📁')
@register_label('service_header',                     'Service Status:',                '👋')
@register_label('active_service',                     'Service (Active):',              '✅')
@register_label('inactive_service',                   'Service (Inactive):',            '❌')
@register_label('summary_header',                     'Summary:',                       '📈')
@register_label('site_header',                        'Site:',                          '🌐')
@register_label('site_http',                          'HTTP:',                          '🌐')
@register_label('site_https',                         'HTTP + SSL:',                    '🔒')
@register_label('active_henhouse',                    'Active Henhouse:',               '✅')
@register_label('available_henhouse',                 'Available Henhouse:',            '📦')
@register_label('active_other',                       'Active Other:',                  '🌍')
@register_label('available_other',                    'Available Other:',               '📁')
def _register_config():
    pass


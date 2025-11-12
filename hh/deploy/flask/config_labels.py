from hh.render.config.config_registry import register_label

@register_label('flask_start_header',                 'Flask Daemon Start Status',        '🚀')
@register_label('flask_stop_header',                  'Flask Daemon Stop Status',         '🛑')
@register_label('flask_status_header',                'Flask Daemon Status',              '📊')
@register_label('daemon_status_header',                'Daemon:',                         '🤖')
@register_label('daemon_started',                      'Started:',                        '✅')
@register_label('daemon_restarted',                     'Restarted:',                     '🔁')
@register_label('daemon_running',                      'Running:',                        '🟢')
@register_label('daemon_failed',                       'Failed:',                         '❌')
@register_label('daemon_not_found',                    'Not Found:',                      '⚠️')
@register_label('daemon_error',                        'Error:',                          '💥')
@register_label('daemon_stopped',                      'Stopped:',                        '🔴')
@register_label('daemon_not_running',                   'Not Running:',                   '⚪')
@register_label('daemon_not_deployed',                  'Not Deployed:',                  '📭')
def _register_config():
    pass


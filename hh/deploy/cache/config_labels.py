from hh.render.config.config_registry import register_label

@register_label('cache_cleared',                      'Cache Cleared:',                 '🧹')
@register_label('clear_cache_header',                  'Cache Clear Status',             '🧹')
@register_label('item_type',                          'Type:',                          '📋')
@register_label('file_path',                          'Path:',                          '📄')
@register_label('rebuild_cache_header',               'Cache Rebuild Summary',          '🧰')
@register_label('rebuild_cache_summary_header',       'Cache Targets:',                 '📦')
@register_label('rebuild_cache_summary_row',          'Target:',                        '📦')
@register_label('rebuild_cache_details_header',       'Run Details:',                   'ℹ️')
@register_label('rebuild_cache_details_row',          'Detail:',                        '📋')
@register_label('rebuild_cache_errors_header',        'Errors:',                        '⚠️')
@register_label('rebuild_cache_errors_row',           'Error:',                         '⚠️')
def _register_config():
    pass


from hh.render.config.config_registry import register_label

@register_label('page_file_path',                    'Path:',                      '📁')
@register_label('page_language',                     'Language:',                  '💬')
@register_label('source_code_file',                  'Source Code File:',          '📝')
@register_label('source_code_file_unknown',          'Unknown Source Code File:',   '❓')
@register_label('source_code_file_python',           'Python Source Code File:',   '🐍')
@register_label('source_code_file_markdown',         'Markdown Source Code File:', '📝')
@register_label('source_code_file_text',            'Text Source Code File:',      '📄')
@register_label('source_code_file_javascript',      'JavaScript Source Code File:', '🟨')
@register_label('source_code_file_css',              'CSS Source Code File:',      '🎨')
@register_label('source_code_file_typescript',      'TypeScript Source Code File:', '🔷')
@register_label('source_code_file_html',            'HTML Source Code File:',      '🌐')
@register_label('source_code_file_ini',            'INI Source Code File:',      '📋')
@register_label('source_code_file_powershell',    'PowerShell Source Code File:', '⚡')
@register_label('source_code_file_json',          'JSON Source Code File:',      '📦')
def _register_config():
    pass


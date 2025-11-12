from hh.render.config.config_registry import register_label

@register_label('git_repo',                            'Git Repository:',                '📦')
@register_label('pull_project_header',                  'Project Pull Status',            '📥')
@register_label('current_branch',                       'Current Branch:',                '🌿')
@register_label('branch_switched',                      'Branch Switched:',               '🔄')
@register_label('short_hash',                           'Commit Hash:',                   '🔗')
@register_label('commit_message',                       'Commit Message:',                '💬')
@register_label('time_ago',                             'Committed:',                      '⏰')
@register_label('push_project_header',                  'Project Push Status',            '📤')
@register_label('push_message',                         'Message:',                        '💬')
@register_label('branch',                               'Branch:',                         '🌿')
@register_label('has_changes',                          'Has Changes:',                    '📝')
@register_label('stage_file_created',                    'Stage File Created:',             '📄')
def _register_config():
    pass


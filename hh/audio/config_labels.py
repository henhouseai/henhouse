from hh.render.config.config_registry import register_label

@register_label('show_audio_header',                  'Audio Details',                '🎵')
@register_label('audio_id',                           'Audio ID:',                    '🆔')
@register_label('audio_caption',                      'Caption:',                     '📝')
@register_label('audio_mime_type',                    'MIME Type:',                   '🧾')
@register_label('audio_max_filesize',                 'Max Filesize:',                '💾')
@register_label('audio_duration_seconds',             'Duration (s):',                '⏱️')
@register_label('audio_bitrate',                      'Bitrate:',                     '📊')
@register_label('audio_num_instances',                'Instances:',                   '🎵')
@register_label('audio_file_path',                    'File Path:',                   '📁')
@register_label('audio_uploaded',                     'Uploaded:',                    '⏰')
@register_label('audio_usage_header',                'Used By Pages:',               '🔗')
@register_label('audio_usage_item',                   'Page:',                        '📄')
@register_label('audio_instances_header',             'Audio Instances:',             '🎵')
@register_label('audio_instance_item',                'Instance:',                    '🎵')
@register_label('audio_visibility',                  'Visibility:',                  '👀')
@register_label('audio_view_count',                   'View Count:',                  '👀')
@register_label('audio_username',                     'Username:',                    '👤')
@register_label('extra_data_audio_id',                'Audio ID:',                    '🆔')
@register_label('set_audio_visibility_header',        'Audio Visibility Modification', '👀')
@register_label('modify_audio_caption_header',         'Audio Caption Modification',   '📝')
def _register_config():
    pass

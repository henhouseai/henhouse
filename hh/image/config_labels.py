from hh.render.config.config_registry import register_label

@register_label('show_image_header',                  'Image Details',                '🖼️')
@register_label('image_id',                           'Image ID:',                    '🆔')
@register_label('image_caption',                      'Caption:',                     '📝')
@register_label('image_aspect_ratio',                 'Aspect Ratio:',                '📐')
@register_label('image_max_width',                    'Max Width:',                   '📏')
@register_label('image_max_height',                   'Max Height:',                  '📏')
@register_label('image_max_filesize',                  'Max Filesize:',               '💾')
@register_label('image_num_instances',                'Instances:',                   '🎨')
@register_label('image_file_path',                    'File Path:',                   '📁')
@register_label('image_uploaded',                     'Uploaded:',                    '⏰')
@register_label('image_usage_header',                 'Used By Pages:',               '🔗')
@register_label('image_usage_item',                   'Page:',                        '📄')
@register_label('instances_header',                   'Image Instances:',             '🎨')
@register_label('instance_item',                      'Instance:',                    '🎨')
@register_label('image_visibility',                   'Visibility:',                  '👁️')
@register_label('image_view_count',                   'View Count:',                  '👀')
@register_label('image_username',                     'Username:',                    '👤')
@register_label('image_path_header',                  'Path:',                        '🔸')
@register_label('image_path',                         'Path:',                        '🔸')
@register_label('extra_actions_header',               'Extra Actions:',               'ℹ️')
@register_label('extra_actions_item',                 'Action:',                      '📋')
@register_label('extra_data_image_id',                'Image ID:',                    '🆔')
@register_label('extra_data_old_caption',             'Old Caption:',                 '📝')
@register_label('extra_data_new_caption',             'New Caption:',                 '📝')
def _register_config():
    pass


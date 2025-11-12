from hh.render.config.config_registry import register_label

@register_label('page_link_header',                  'Page Link',                    '🔗')
@register_label('image_link_header',                 'Image Link',                   '🔗')
@register_label('image_header',                      'Image',                        '🔗')
@register_label('custom_header',                     'Custom Decorator',             '✨')
@register_label('unknown_header',                    'Unknown Element',              '❓')
@register_label('image_link_page',                   'Page',                         '📄')
@register_label('image_link_image',                  'Image',                        '🎨')
@register_label('image_row',                         'Image',                        '🎨')
@register_label('custom_value',                      'Value',                        '✨')
@register_label('unknown_row',                       'Unknown Element',              '❓')
@register_label('caption',                           'Caption',                      '📝')
@register_label('filename',                          'Filename',                    '📄')
def _register_config():
    pass


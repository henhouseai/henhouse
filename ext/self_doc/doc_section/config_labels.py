from hh.render.config.config_registry import register_label

@register_label('doc_section', 'Section:', '📝')
@register_label('doc_section_level', 'Section Level:', '🔢')
@register_label('doc_section_sort_order', 'Sort Order:', '🔢')
@register_label('doc_section_type', 'Section Type:', '📋')
@register_label('modify_doc_section_info_header', 'Doc Section Info Modification')
def _register_config():
    pass
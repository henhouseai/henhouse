from hh.render.config.config_registry import register_label

@register_label('document', 'Document:', '📄')
@register_label('document_output_filename', 'Output Filename:', '📄')
@register_label('document_output_format', 'Output Format:', '⚙️')
@register_label('modify_document_info_header', 'Document Info Modification')
def _register_config():
    pass
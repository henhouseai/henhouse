from hh.render.config.config_registry import register_label

@register_label("file_info_header", "File Info", "📁")
@register_label("file_name", "Name", "🏷️")
@register_label("file_mime", "MIME Type", "🧾")
@register_label("file_size_bytes", "Size (bytes)", "📏")
@register_label("file_visibility", "Visibility", "🔒")
@register_label("file_uploaded", "Uploaded", "📅")
@register_label("file_last_modified", "Last Modified", "🛠️")
def _register_config():
    pass


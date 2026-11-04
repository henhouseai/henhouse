from hh.render.config.config_registry import register_label

@register_label("file_info_header", "File Info", "📁")
@register_label("show_file_header", "File Details", "📁")
@register_label("file_id", "File ID:", "🆔")
@register_label("file_name", "Name", "📄")
@register_label("file_description", "Description:", "📝")
@register_label("file_mime", "MIME Type", "🧾")
@register_label("file_size_bytes", "Size (bytes)", "📏")
@register_label("file_path", "File Path:", "📁")
@register_label("file_visibility", "Visibility", "🔒")
@register_label("file_uploaded", "Uploaded", "📅")
@register_label("file_last_modified", "Last Modified", "⏰")
@register_label("file_usage_header", "Used By Pages:", "🔗")
@register_label("file_usage_item", "Page:", "📄")
@register_label("modify_file_description_header", "File Description Modification", "📝")
@register_label("extra_data_file_id", "File ID:", "🆔")
@register_label("extra_data_old_description", "Old Description:", "📝")
@register_label("extra_data_new_description", "New Description:", "📝")
def _register_config():
    pass


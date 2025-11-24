from hh.render.config.config_registry import register_label


@register_label("orphan_check_header", "Orphan Check Results", "🧹")
@register_label("orphan_pages", "Pages Missing Parents", "📄")
@register_label("orphan_link_sources", "Links Missing Source Pages", "🔗")
@register_label("orphan_link_targets", "Links Missing Target Pages", "🎯")
@register_label("orphan_image_pages", "Image Links Missing Pages", "🖼️")
@register_label("orphan_image_targets", "Image Links Missing Images", "🧩")
@register_label("orphan_image_group_pages", "Image Groups Missing Pages", "🗃️")
@register_label("orphan_image_group_images", "Image Groups Missing Images", "🗂️")
@register_label("orphan_file_group_pages", "File Groups Missing Pages", "📁")
@register_label("orphan_file_group_files", "File Groups Missing Files", "📦")
@register_label("orphan_type", "Orphan type", "")
@register_label("ids", "IDs", "")
@register_label("maintenance_ping_header", "Maintenance Ping", "📡")
@register_label("page_cache_refresh_header", "Page Cache Refresh", "📄")
@register_label("page_cache_refresh_processed", "Pages Cached", "⚙️")
@register_label("page_cache_refresh_remaining", "Pages Remaining", "⏳")
@register_label("page_cache_refresh_errors", "Cache Errors", "⚠️")
def _register_config():
    pass


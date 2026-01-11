from hh.render.config.config_registry import register_label

# OCR Status field configs
@register_label('ocr_status', 'OCR Status:', '📄')
@register_label('ocr_success', 'OCR Success', '✅')
@register_label('ocr_error', 'OCR Error', '❌')
@register_label('ocr_processing', 'OCR Processing', '⏳')
@register_label('ocr_pending', 'OCR Pending', '⏸️')

# OCR Data field configs
@register_label('ocr_text', 'OCR Text:', '📝')
@register_label('ocr_timestamps', 'OCR Timestamps:', '⏰')
@register_label('ocr_confidence', 'OCR Confidence:', '📊')
@register_label('ocr_images_processed', 'Images Processed:', '🎨')
@register_label('ocr_images_failed', 'Images Failed:', '⚠️')

# OCR Image-specific field configs
@register_label('ocr_image_id', 'Image ID:', '🎨')
@register_label('ocr_timestamp', 'Processed:', '⏰')

def _register_config():
    pass

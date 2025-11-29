from __future__ import annotations
from typing import Optional, Dict, Any, List


def render_tile(img_html: str, target_width: int, caption_html: str = "", extra_class: str = "") -> str:
    classes = ["tileWrapper"]
    if extra_class:
        classes.append(extra_class)
    class_attr = " ".join(classes)
    tile_text_class = "tileText" + (" emptyTileText" if len(caption_html) == 0 else "")
    return (
        f"<div class=\"{class_attr}\">"
        f"{img_html}"
        f"<div class=\"{tile_text_class}\" style=\"width: {int(target_width)}px;\">{caption_html}</div>"
        f"</div>"
    )


def render_tile_link(href: str, img_html: str, target_width: int, caption_html: str = "", extra_class: str = "", link_id: Optional[str] = None) -> str:
    a_attrs = (
        f'id="{link_id}"' if link_id else f'href="{href}"'
    )
    return f"<a class=\"tileLink\" {a_attrs}>{render_tile(img_html, target_width, caption_html, extra_class)}</a>"


def render_image_tile(image_data: Dict[str, Any], target_width: int = 300, caption: Optional[str] = None) -> str:
    """Render a single image tile HTML.
    
    Args:
        image_data: Image data dict with 'id', 'caption', 'instances' (list of dicts with 'src', 'width', 'height')
        target_width: Target width for image (default 300)
        caption: Optional caption override (uses image_data['caption'] if not provided)
    
    Returns:
        HTML string for image tile
    """
    image_id = image_data.get('id')
    instances = image_data.get('instances', [])
    image_caption = caption if caption is not None else image_data.get('caption', '')
    
    # Find best instance for target width
    best_instance = None
    if instances:
        for instance in instances:
            width = instance.get('width', 0)
            if width >= target_width:
                if best_instance is None or width < best_instance.get('width', 0):
                    best_instance = instance
        # If no instance is large enough, use largest available
        if best_instance is None:
            best_instance = max(instances, key=lambda x: x.get('width', 0))
    
    # Build img tag
    if best_instance and best_instance.get('src'):
        src_path = best_instance['src']
        img_src = f'/srv/images/{src_path}'
        img_html = f'<img src="{img_src}" alt="{image_caption}" style="width: {target_width}px;">'
    else:
        # Fallback if no instance
        img_html = f'<img src="" alt="{image_caption}" style="width: {target_width}px;">'
    
    return render_tile(img_html, target_width, image_caption)


def render_image_tile_link(image_data: Dict[str, Any], target_width: int = 300, link_href: Optional[str] = None, caption: Optional[str] = None) -> str:
    """Render an image tile wrapped in a link.
    
    Args:
        image_data: Image data dict with 'id', 'caption', 'instances'
        target_width: Target width for image (default 300)
        link_href: Optional link URL (defaults to /img/{image_id})
        caption: Optional caption override
    
    Returns:
        HTML string for image tile link
    """
    image_id = image_data.get('id')
    if link_href is None and image_id:
        from hh.render.html.link_helpers import create_image_link
        link_href = create_image_link(image_id)
    elif link_href is None:
        link_href = '#'
    
    tile_html = render_image_tile(image_data, target_width, caption)
    return f'<a class="tileLink" href="{link_href}">{tile_html}</a>'



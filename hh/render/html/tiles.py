from __future__ import annotations
from typing import Optional


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



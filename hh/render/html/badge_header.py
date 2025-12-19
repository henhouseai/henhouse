from __future__ import annotations
from typing import Dict, List, Any


def _li(inner: str, el_id: str | None = None) -> str:
    if el_id:
        return f"<li id=\"{el_id}\">{inner}</li>"
    return f"<li>{inner}</li>"


def render_badge_header(
    *,
    page_id: int,
    class_name: str,
    data_groups: Dict[str, Dict[str, Any]],
    fields: Dict[str, Dict[str, Any]],
    values: Dict[str, Any],
    admin: bool,
) -> str:
    """
    Render legacy-style badge header block.

    data_groups: { group_name: { 'label': str } }
    fields: {
        field_name: {
            'dataGroup': str,
            'dataType': 'currency'|'page'|'browser'|'select'|...,
            'label': str,
            'capName': str,
            'selectOptions': Optional[Dict[value, label]]
        }
    }
    values: { field_name: value or object depending on dataType }
    """
    pieces: List[str] = []
    pieces.append(f"<div id=\"pageHeader_{page_id}\" class=\"dBBadgeHeader\">")

    for group_name, group_cfg in data_groups.items():
        label = group_cfg.get('label', group_name)
        pieces.append(f"<ul id=\"{group_name}\" class=\"dBBadge\">")
        header_inner = (
            f"<a id=\"modify_{class_name}_{group_name}_{page_id}\">{label}</a>"
            if admin
            else label
        )
        pieces.append(_li(header_inner, el_id=None).replace("<li>", "<li class=\"header\">", 1))

        for field_name, field_cfg in fields.items():
            if field_cfg.get('dataGroup') != group_name:
                continue
            cap_name = field_cfg.get('capName', field_name.capitalize())
            data_type = field_cfg.get('dataType', 'text')
            value = values.get(field_name)

            rendered_value = ''
            if data_type == 'currency':
                try:
                    if value is not None:
                        rendered_value = f"{float(value):0.2f}"
                    else:
                        rendered_value = '&nbsp;'
                except (ValueError, TypeError):
                    rendered_value = str(value) if value is not None else '&nbsp;'
            elif data_type == 'page':
                rendered_value = str(value) if value is not None else '&nbsp;'
            elif data_type == 'browser':
                rendered_value = str(value) if value is not None else '&nbsp;'
            elif data_type == 'select':
                options = field_cfg.get('selectOptions', {}) or {}
                option_value = options.get(value, value)
                rendered_value = str(option_value) if option_value is not None else '&nbsp;'
            else:
                rendered_value = '' if value is None else str(value)

            val_html = (
                f"<div class=\"dBBadgeLabel\">{field_cfg.get('label', cap_name)}</div>"
                f"<div class=\"dBBadgeValue\">{rendered_value}</div>"
            )
            pieces.append(_li(val_html, el_id=f"{group_name}{cap_name}"))

        pieces.append("</ul>")

    pieces.append("</div><div class=\"clear\"></div>")
    return "".join(pieces)



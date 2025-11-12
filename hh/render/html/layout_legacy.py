from __future__ import annotations
from typing import List, Optional, Sequence


def _wrap(tag: str, inner: str, attrs: str = "") -> str:
    if attrs:
        return f"<{tag} {attrs}>{inner}</{tag}>"
    return f"<{tag}>{inner}</{tag}>"


def render_header(path_html: str, title: str) -> str:
    display = path_html if path_html else title
    return (
        "<div id=\"header\">" + display + "</div>"
    )


def render_menu(
    *,
    admin: bool,
    user_info_html: str = "",
    site_links_html: str = "",
    application_action_links_html: str = "",
    user_action_links_html: str = "",
) -> str:
    parts: List[str] = []
    if admin:
        if user_info_html:
            parts.append(user_info_html)
        if site_links_html:
            parts.append(site_links_html)
        if application_action_links_html:
            parts.append(application_action_links_html)
    else:
        if user_action_links_html:
            parts.append(user_action_links_html)
        if site_links_html:
            parts.append(site_links_html)
    inner = "\n".join(parts)
    return (
        "<div id=\"menu\">\n" + inner + "\n</div>"
    )


def render_content_wrapper_header(title: str) -> str:
    return f"<div class=\"contentWrapperHeader\">{title}</div>"


def render_content_wrapper(
    content_divs: Sequence[str],
    content_wrapper_class: str = "",
) -> str:
    class_attr = (
        f"contentWrapper {content_wrapper_class}".strip()
        if content_wrapper_class
        else "contentWrapper"
    )
    inner = "\n".join(content_divs)
    return f"<div class=\"{class_attr}\">\n{inner}\n</div>"


def render_footer() -> str:
    return "<div id=\"footer\"></div>"


def render_wrapper(
    *,
    header_html: str,
    menu_html: str,
    content_holder_html: str,
    footer_html: str,
) -> str:
    return (
        "<div id=\"wrapper\">\n"
        + header_html
        + "\n"
        + menu_html
        + "\n"
        + content_holder_html
        + "\n"
        + footer_html
        + "\n</div>"
    )


def render_content_holder(title: str, content_wrapper_html: str) -> str:
    return (
        "<div id=\"contentHolder\">\n"
        + render_content_wrapper_header(title)
        + "\n"
        + content_wrapper_html
        + "\n</div>"
    )


def render_legacy_body(
    *,
    title: str,
    path_html: str = "",
    admin: bool = False,
    user_info_html: str = "",
    site_links_html: str = "",
    application_action_links_html: str = "",
    user_action_links_html: str = "",
    content_divs: Sequence[str] = (),
    content_wrapper_class: str = "",
) -> str:
    header_html = render_header(path_html, title)
    menu_html = render_menu(
        admin=admin,
        user_info_html=user_info_html,
        site_links_html=site_links_html,
        application_action_links_html=application_action_links_html,
        user_action_links_html=user_action_links_html,
    )
    content_wrapper_html = render_content_wrapper(content_divs, content_wrapper_class)
    content_holder_html = render_content_holder(title, content_wrapper_html)
    footer_html = render_footer()
    return render_wrapper(
        header_html=header_html,
        menu_html=menu_html,
        content_holder_html=content_holder_html,
        footer_html=footer_html,
    )


def render_error_body(error_message_html: str, title: str = "ERROR") -> str:
    content = (
        f"<div class=\"contentHeader\">ERROR</div>\n"
        f"<div class=\"content\">{error_message_html}</div>"
    )
    content_wrapper = render_content_wrapper([content])
    return render_wrapper(
        header_html=render_header("", title),
        menu_html="<div id=\"menu\"></div>",
        content_holder_html=render_content_holder(title, content_wrapper),
        footer_html=render_footer(),
    )



from hh.page.page import Page
from hh.page.page_class_registry import register_page_class


@register_page_class('subpage')
class SubPage(Page):
    """
    A page class that allows hierarchical URLs without global links.
    Enables tree-structured paths like /alice/projects/project1

    Key differences from base Page:
    - auto_link_name() = False (no global links)
    - allow_duplicate_names() = True (inherited from Page, allows same names under different parents)
    """

    @classmethod
    def auto_link_name(cls) -> bool:
        """SubPages don't create global links - found via parent traversal."""
        return False
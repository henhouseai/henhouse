from __future__ import annotations
from typing import Union


def create_page_link(page_id: Union[int, str]) -> str:
    """Create a page link URL for the given page ID."""
    return f'show-page?id={page_id}'


def create_image_link(image_id: Union[int, str]) -> str:
    """Create an image link URL for the given image ID."""
    return f'show-image?id={image_id}'


def create_image_file_link(src_path: str) -> str:
    """Create an image file link URL for the given source path."""
    return f'/srv/images/{src_path}'


def create_file_link(src_path: str) -> str:
    """Create a file link URL for the given source path."""
    return f'/srv/files/{src_path}'


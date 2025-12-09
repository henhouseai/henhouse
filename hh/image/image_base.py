from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Protocol


class BaseImage(Protocol):
    id: int
    gateway: Any
    caption: Optional[str]
    visibility: Optional[int]
    username: Optional[str]
    comments: Optional[str]
    uploaded: Optional[dt.datetime]
    last_modified: Optional[dt.datetime]
    view_count: Optional[int]
    instances: Optional[List[Dict[str, Any]] | List[Any]]
    cached_usage: Optional[List[Dict[str, Any]] | List[Any]]
    _cache_needs_refresh: bool

    def flag_image_modification(self, comments: str) -> bool: ...
    def validate_caption(self, caption: str) -> bool: ...
    def get_instances(self) -> List[Dict[str, Any]]: ...
    def get_usage_count(self) -> int: ...
    def _get_usage_data(self) -> List[Dict[str, Any]]: ...
    def _flag_cache_refresh(self) -> None: ...
    def _dump_json(self, value: Any) -> str: ...
    def get_image_data(self) -> Dict[str, Any]: ...
    def get_instances_data(self) -> List[Dict[str, Any]]: ...


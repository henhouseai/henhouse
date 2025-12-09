from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Protocol


class BaseFile(Protocol):
    id: int
    gateway: Any
    file_name: Optional[str]
    file_path: Optional[str]
    description: Optional[str]
    mime_type: Optional[str]
    size_bytes: Optional[int]
    username: Optional[str]
    uploaded: Optional[dt.datetime]
    last_modified: Optional[dt.datetime]
    comments: Optional[str]
    visibility: Optional[int]
    pages: List[Any] | List[Dict[str, Any]]
    _cache_needs_refresh: bool

    def _flag_cache_refresh(self) -> None: ...
    def flag_file_modification(self, comments: str) -> bool: ...
    def get_usage_data(self) -> List[Dict[str, Any]]: ...
    def _dump_json(self, value: Any) -> str: ...


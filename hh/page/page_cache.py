from __future__ import annotations
from typing import Optional, List, Dict, Any
import json
import datetime as dt
from decimal import Decimal

from hh.gateway.connection.connection import r_query, u_query, c_query
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_method_registry import register_page_mixin_methods
from hh.page.page_registry import invalidate_page_cache_entry
from hh.tp.tp import TextProcessor

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None


@register_debug_init
def _initialize_page_cache_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


CACHE_VERSION = "v1"


@register_page_mixin_methods
def _register_cache_methods():
    return {
        'refresh_cached_page': {'mixin_method': '_refresh_cached_page', 'decorator': 'write'},
        'ensure_cache_entry': {'mixin_method': '_ensure_cache_entry', 'decorator': 'write'},
        'load_cached_payload': {'mixin_method': '_load_cached_payload', 'decorator': 'read'},
        'clear_cached_payload_state': {'mixin_method': '_clear_cached_payload_state', 'decorator': 'read'},
        'get_cached_prepared_text_if_current': {'mixin_method': '_get_cached_prepared_text_if_current', 'decorator': 'read'},
    }


class PageCacheMixin:

    def _load_cached_payload(self) -> Optional[Dict[str, Any]]:
        trace_in()
        if not getattr(self, "cache_hydrated", False):
            trace_out()
            return None
        page_data = self.get_page_data()
        if self.cached_prepared_text is not None:
            page_data = dict(page_data)
            page_data["prepared_text"] = self.cached_prepared_text
        payload = {
            "page": page_data,
            "children_by_class": self.cached_children_by_class or {},
            "images": self.cached_images or [],
            "badge_headers": self.cached_badge_headers or {},
            "upper_content": self.cached_upper_content or [],
            "lower_content": self.cached_lower_content or [],
            "_cache_info": {
                "source_last_modified": self.cache_source_last_modified,
                "cache_built_at": self.cache_built_at,
                "version": CACHE_VERSION,
            },
        }
        trace_out()
        return payload

    def _ensure_cache_entry(self) -> bool:
        trace_in()
        try:
            existing = r_query(
                self.conn,
                "SELECT 1 FROM pages WHERE id = %s",
                (self.id,),
                use_secondary=True,
            )
        except Exception as exc:
            warn(f"Failed to check cache entry for page {self.id}: {exc}")
            report_error("connection", f"Failed to verify cache for page {self.id}")
            trace_out()
            return False

        if existing:
            trace_out()
            return True

        metadata_json = self._serialize_metadata()
        now = dt.datetime.utcnow()
        try:
            c_query(
                self.conn,
                """
                    INSERT INTO pages (
                        id,
                        parent_id,
                        class,
                        name,
                        link,
                        text,
                        metadata,
                        prepared_text,
                        children_summary,
                        image_summary,
                        file_summary,
                        links_out,
                        source_last_modified,
                        cache_built_at,
                        cache_version
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    self.id,
                    self.parent,
                    self.class_name,
                    self.name,
                    self.link,
                    self.text,
                    metadata_json,
                    None,
                    None,
                    None,
                    None,
                    None,
                    now,
                    now,
                    CACHE_VERSION,
                ),
                use_secondary=True,
            )
            debug(f"Created cache entry for page {self.id}")
        except Exception as exc:
            warn(f"Failed to insert cache entry for page {self.id}: {exc}")
            report_error("connection", f"Failed to create cache entry for page {self.id}")
            trace_out()
            return False

        trace_out()
        return True

    def _refresh_cached_page(
        self,
        new_text: Optional[str] = None,
        preprocessed_payload: Optional[List[Dict[str, Any]]] = None,
        cache_payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        trace_in()
        if not self._ensure_cache_entry():
            trace_out()
            return False

        metadata_json = self._serialize_metadata()
        if preprocessed_payload is None:
            source_text = new_text if new_text is not None else (self.text or "")
            if source_text is not None:
                processor = TextProcessor()
                generated = processor.preprocess(source_text)
                if generated is not None:
                    preprocessed_payload = generated
                    debug(f"Generated prepared text for page {self.id} inside refresh_cached_page")
                else:
                    warn(f"Failed to preprocess text for page {self.id} while refreshing cache")
        prepared_json = (
            json.dumps(preprocessed_payload, ensure_ascii=False)
            if preprocessed_payload is not None
            else None
        )
        now = dt.datetime.utcnow()
        children_json = None
        images_json = None
        file_summary_json = None
        links_json = None
        if cache_payload:
            children_json = self._dump_json(cache_payload.get("children_by_class", {}) or {})
            images_json = self._dump_json(cache_payload.get("images", []) or [])
            file_summary = {
                "upper_content": cache_payload.get("upper_content", []) or [],
                "lower_content": cache_payload.get("lower_content", []) or [],
            }
            file_summary_json = self._dump_json(file_summary)
            links_json = self._dump_json(cache_payload.get("badge_headers", {}) or {})
        try:
            affected = u_query(
                self.conn,
                """
                    UPDATE pages
                    SET text = %s,
                        prepared_text = %s,
                        name = %s,
                        link = %s,
                        metadata = %s,
                        children_summary = %s,
                        image_summary = %s,
                        file_summary = %s,
                        links_out = %s,
                        parent_id = %s,
                        class = %s,
                        source_last_modified = %s,
                        cache_built_at = %s,
                        cache_version = %s
                    WHERE id = %s
                """,
                (
                    new_text,
                    prepared_json,
                    self.name,
                    self.link,
                    metadata_json,
                    children_json,
                    images_json,
                    file_summary_json,
                    links_json,
                    self.parent,
                    self.class_name,
                    now,
                    now,
                    CACHE_VERSION,
                    self.id,
                ),
                use_secondary=True,
            )
            debug(
                f"Refreshed cache for page {self.id}: rows={affected}, "
                f"text_len={0 if new_text is None else len(new_text)}, "
                f"prepared={'yes' if prepared_json else 'no'}"
            )
        except Exception as exc:
            warn(f"Failed to update cache for page {self.id}: {exc}")
            report_error("connection", f"Failed to update cache for page {self.id}")
            trace_out()
            return False

        invalidate_page_cache_entry(self.id)
        trace_out()
        return not is_error()

    def _serialize_metadata(self) -> str:
        metadata = getattr(self, 'metadata', {}) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return self._dump_json(metadata)

    def _dump_json(self, value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(',', ':'),
            default=self._json_default,
        )

    def _json_default(self, value: Any):
        if isinstance(value, (dt.datetime, dt.date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (bytes, bytearray)):
            try:
                return value.decode('utf-8')
            except Exception:
                return value.decode('utf-8', errors='ignore')
        if isinstance(value, set):
            return list(value)
        return value

    def _clear_cached_payload_state(self) -> None:
        trace_in()
        self.cached_prepared_text = None
        self.cached_children_by_class = None
        self.cached_images = None
        self.cached_file_summary = None
        self.cached_badge_headers = None
        self.cached_upper_content = None
        self.cached_lower_content = None
        self.cache_built_at = None
        self.cache_source_last_modified = None
        self.cache_hydrated = False
        trace_out()

    def _get_cached_prepared_text_if_current(self) -> Optional[List[Dict[str, Any]]]:
        trace_in()
        try:
            row = r_query(
                self.conn,
                """
                    SELECT text, prepared_text
                    FROM pages
                    WHERE id = %s
                """,
                (self.id,),
                use_secondary=True,
            )
        except Exception as exc:
            warn(f"Failed to load cached prepared text for page {self.id}: {exc}")
            trace_out()
            return None

        if not row:
            trace_out()
            return None

        cache_row = row[0]
        cached_text = cache_row.get('text') or ""
        current_text = (self.text or "")
        if cached_text != current_text:
            debug(f"Cached text mismatch for page {self.id}; forcing reprocess")
            trace_out()
            return None

        prepared_blob = cache_row.get('prepared_text')
        if prepared_blob in (None, '', b''):
            trace_out()
            return None

        if isinstance(prepared_blob, (bytes, bytearray)):
            prepared_blob = prepared_blob.decode('utf-8')

        try:
            prepared_payload = json.loads(prepared_blob) if isinstance(prepared_blob, str) else prepared_blob
            trace_out()
            return prepared_payload
        except (ValueError, TypeError):
            warn(f"Failed to decode cached prepared text for page {self.id}")
            trace_out()
            return None


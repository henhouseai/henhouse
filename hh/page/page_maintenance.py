from typing import Dict, TYPE_CHECKING
import re

from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)

if TYPE_CHECKING:
    from hh.page.page_base import BasePage
else:
    class BasePage:
        pass

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None


@register_debug_init
def _initialize_page_maintenance_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)




class PageMaintenanceMixin(BasePage):
    def regex_text(
        self,
        *,
        old_name: str,
        new_name: str,
    ) -> Dict[str, object]:
        trace_in()
        result: Dict[str, object] = {
            "page_id": self.id,
            "processed": 0,
            "modified": False,
        }

        if not old_name or not new_name:
            trace_out()
            return result

        existing_text = self.text or ""
        replacements = [
            (f"[[{old_name}]]", f"[[{new_name}]]"),
            (f"[[{old_name}][", f"[[{new_name}]["),
            (f"{{{{{old_name}}}}}", f"{{{{{new_name}}}}}"),
            (f"{{{{{old_name}}}{{", f"{{{{{new_name}}}{{"),
        ]

        updated_text = existing_text
        for pattern, replacement in replacements:
            updated_text = re.sub(re.escape(pattern), replacement, updated_text)

        if updated_text != existing_text:
            if not self.modify_text(updated_text):
                raise RuntimeError(f"Failed to update text for page {self.id}")
            result["processed"] = 1
            result["modified"] = True

        trace_out()
        return result


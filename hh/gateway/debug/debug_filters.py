from __future__ import annotations
from typing import List, Dict, Optional

def parse_list_arg(list_arg: str) -> List[str]:
    """Parse comma-separated list argument"""
    if not list_arg:
        return []
    try:
        import re
        items = re.findall(r"'([^']*)'|\"([^\"]*)\"|([^,]+)", list_arg)
        parsed_list = [item[0] or item[1] or item[2] for item in items]
        return [item.strip() for item in parsed_list if item.strip()]
    except Exception:
        return []

class FilterMixin:
    """Mixin class providing shared filtering functionality for debug systems"""
    
    def __init__(self):
        self.whitelist: List[str] = ["*"]
        self.graylist: List[str] = []
        self.blacklist: List[str] = []
        self.summary_limit: int = 10
        self._seen_combinations: Dict[str, int] = {}
        self._total_combinations: Dict[str, int] = {}
    
    def is_whitelisted(self, module: str) -> bool:
        for whitelist_entry in self.whitelist:
            if whitelist_entry.startswith('*') and whitelist_entry.endswith('*'):
                pattern = whitelist_entry[1:-1]
                if pattern in module:
                    return True
            elif whitelist_entry.startswith('*'):
                pattern = whitelist_entry[1:]
                if module.endswith(pattern):
                    return True
            elif whitelist_entry.endswith('*'):
                pattern = whitelist_entry[:-1]
                if module.startswith(pattern):
                    return True
            else:
                if module == whitelist_entry:
                    return True
        return False
    
    def is_graylisted(self, filename: str) -> bool:
        if not self.graylist:
            return True
        for graylist_entry in self.graylist:
            if graylist_entry.startswith('*') and graylist_entry.endswith('*'):
                pattern = graylist_entry[1:-1]
                if pattern in filename:
                    return True
            elif graylist_entry.startswith('*'):
                pattern = graylist_entry[1:]
                if filename.endswith(pattern):
                    return True
            elif graylist_entry.endswith('*'):
                pattern = graylist_entry[:-1]
                if filename.startswith(pattern):
                    return True
            else:
                if filename == graylist_entry:
                    return True
        return False
    
    def is_blacklisted(self, function: str) -> bool:
        for blacklist_entry in self.blacklist:
            if blacklist_entry.startswith('*') and blacklist_entry.endswith('*'):
                pattern = blacklist_entry[1:-1]
                if pattern in function:
                    return True
            elif blacklist_entry.startswith('*'):
                pattern = blacklist_entry[1:]
                if function.endswith(pattern):
                    return True
            elif blacklist_entry.endswith('*'):
                pattern = blacklist_entry[:-1]
                if function.startswith(pattern):
                    return True
            else:
                if function == blacklist_entry:
                    return True
        return False
    
    def should_show_message(self, combination: str, will_be_shown: bool = True) -> bool:
        self._total_combinations[combination] = self._total_combinations.get(combination, 0) + 1
        no_limit = False
        if self.summary_limit <= 0:
            no_limit = True
        current_shown_count = self._seen_combinations.get(combination, 0)
        current_total_count = self._total_combinations.get(combination, 0)
        will_show = ((current_shown_count < self.summary_limit) or no_limit) and will_be_shown
        if will_show:
            self._seen_combinations[combination] = current_shown_count + 1
            return True
        return False
    
    def set_whitelist(self, items: List[str]) -> None:
        self.whitelist = items
    
    def set_graylist(self, items: List[str]) -> None:
        self.graylist = items
    
    def set_blacklist(self, items: List[str]) -> None:
        self.blacklist = items
    
    def set_summary_limit(self, limit: int) -> None:
        self.summary_limit = limit
    
    def clear_combinations(self) -> None:
        self._seen_combinations.clear()
        self._total_combinations.clear()

__all__ = [
    "parse_list_arg",
    "FilterMixin",
]

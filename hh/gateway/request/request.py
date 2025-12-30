from __future__ import annotations
from typing import List, Optional, Any, Union
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

NO_GROUPS = {
    'fluff': ['desc', 'summary', 'main_header', 'sub_header'],
    'headers': ['header', 'main_header', 'sub_header']
}

class Request:
    raw_argv: List[str]
    command: Optional[str]
    no_flags: List[str]
    string_args: dict[str, Any]
    num_args: dict[str, Union[int, float]]  # Numeric arguments (int or float)
    flag_args: List[str]
    extra_commands: List[str]
    extra_command_defaults: dict[str, Any]
    def __init__(self, raw_argv: List[str], skip_parse: bool = False):
        trace_in()
        self.raw_argv = raw_argv
        self.command = None
        self.no_flags = []
        self.string_args = {}
        self.num_args = {}
        self.flag_args = []
        self.extra_commands = []
        self.extra_command_defaults = {}
        log(f"Request initialized with raw_argv: {raw_argv}")
        if not skip_parse:
            try:
                from hh.gateway.request.grammar_parser import parse_request
                parsed_request = parse_request(raw_argv)
                if parsed_request:
                    self.command = parsed_request.command
                    self.string_args = parsed_request.string_args
                    self.num_args = parsed_request.num_args
                    self.flag_args = parsed_request.flag_args
                    self.no_flags = parsed_request.no_flags
                    self.extra_commands = parsed_request.extra_commands
                    self.extra_command_defaults = parsed_request.extra_command_defaults
                    if self.command:
                        self.command = self.command.replace('-', '_')
                    self.extra_commands = [cmd.replace('-', '_') for cmd in self.extra_commands if cmd]
                    log(f"Request populated with grammar parsing: command={self.command}, flags={len(self.flag_args)}, no_flags={len(self.no_flags)}")
                else:
                    warn("Grammar parsing failed, using fallback")
                    if raw_argv:
                        self.command = raw_argv[0]
                        log(f"Using first argv as command: {self.command}")
                    else:
                        self.command = None
                        log("No argv provided, command set to None")
            except Exception as e:
                warn(f"Error during grammar parsing: {e}")
                if raw_argv:
                    self.command = raw_argv[0]
                    log(f"Using first argv as command after error: {self.command}")
                else:
                    self.command = None
                    log("No argv provided after error, command set to None")
        log(f"Request setup complete: command='{self.command}', flags={len(self.flag_args)}, no_flags={len(self.no_flags)}, string_args={len(self.string_args)}")
        trace_out()
    
    def add_synthetic_arg(self, name: str, value: Any = None, arg_type: str = "string") -> None:
        trace_in()
        if arg_type == "no_flag":
            self.no_flags.append(name)
            log(f"Request added synthetic no_flag: {name}")
        elif arg_type == "bool":
            self.flag_args.append(name)
            log(f"Request added synthetic flag: {name}")
        elif arg_type == "int":
            self.num_args[name] = value
            self.string_args[name] = str(value)
            log(f"Request added synthetic int: {name}={value}")
        else:
            self.string_args[name] = value
            try:
                # Try to convert to number (int or float)
                num_value = float(value) if '.' in str(value) or 'e' in str(value).lower() else int(value)
                self.num_args[name] = num_value
                log(f"Successfully converted string to number: {name}={num_value}")
            except (ValueError, TypeError):
                log(f"Could not convert to number, keeping as string: {name}={value}")
            log(f"Request added synthetic string: {name}={value}")
        trace_out()

    def is_no(self, flag_name: str) -> bool:
        trace_in()
        flag_kebab = flag_name.replace('_', '-')
        for no_flag in self.no_flags:
            if flag_kebab == no_flag.replace('_', '-'):
                log(f"Flag '{flag_name}' is directly disabled")
                trace_out()
                return True
        for group_name, members in NO_GROUPS.items():
            if flag_kebab in [m.replace('_', '-') for m in members]:
                for no_flag in self.no_flags:
                    if f"no_{group_name}".replace('_', '-') == no_flag.replace('_', '-'):
                        log(f"Flag '{flag_name}' is disabled via no-groups (group: {group_name})")
                        trace_out()
                        return True
        trace_out()
        return False
    
    def is_set(self, name: str) -> bool:
        trace_in()
        name_kebab = name.replace('_', '-')
        # Check if it exists in string_args
        for key in self.string_args.keys():
            if name_kebab == key.replace('_', '-'):
                log(f"Arg '{name}' is set in string_args")
                trace_out()
                return True
        # Check if it exists in num_args
        for key in self.num_args.keys():
            if name_kebab == key.replace('_', '-'):
                log(f"Arg '{name}' is set in num_args")
                trace_out()
                return True
        # Check if it exists in flag_args
        for key in self.flag_args:
            if name_kebab == key.replace('_', '-'):
                log(f"Arg '{name}' is set in flag_args")
                trace_out()
                return True
        log(f"Arg '{name}' is not set")
        trace_out()
        return False

    def get_arg(self, name: str) -> Any:
        trace_in()
        name_kebab = name.replace('_', '-')
        result: Any
        # Check num_args first (prioritize numeric values)
        for key in self.num_args.keys():
            if name_kebab == key.replace('_', '-'):
                result = self.num_args[key]
                log(f"Found num arg: {name}={result}")
                trace_out()
                return result
        # Fall back to string_args
        for key in self.string_args.keys():
            if name_kebab == key.replace('_', '-'):
                result = self.string_args[key]
                log(f"Found string arg: {name}={result}")
                trace_out()
                return result
        for key in self.flag_args:
            if name_kebab == key.replace('_', '-'):
                result = True
                log(f"Found flag arg: {name}={result}")
                trace_out()
                return result
        result = ""
        trace_out()
        return result
    
    def has_command(self) -> bool:
        trace_in()
        has_cmd = self.command is not None
        log(f"has_command result: {has_cmd}")
        trace_out()
        return has_cmd
    
    def get_command(self) -> Optional[str]:
        trace_in()
        result = self.command
        log(f"get_command result: {result}")
        trace_out()
        return result
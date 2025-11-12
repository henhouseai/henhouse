from __future__ import annotations
from hh.gateway.request.parser import ParsedCommandStream, ParsedValue
from hh.gateway.request.request import Request
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

def build_request(parsed: ParsedCommandStream, request: Request) -> Request:
    trace_in()
    if not parsed:
        warn("Empty parsed command stream provided")
        trace_out()
        return request
    if not parsed.primary_command:
        warn("No primary command in parsed stream")
        trace_out()
        return request
    request.command = parsed.primary_command.name
    log(f"Set primary command: '{request.command}'")
    if parsed.primary_command.default_value:
        _add_default_value(request, parsed.primary_command.name, parsed.primary_command.default_value)
        log(f"Added primary command default value: '{parsed.primary_command.default_value.raw}'")
    else:
        log("Primary command has no default value")
    additional_count = 0
    for command in parsed.additional_commands:
        if command.default_value:
            _add_default_value(request, command.name, command.default_value)
            log(f"Added additional command default value: '{command.name}'='{command.default_value.raw}'")
        else:
            log(f"Additional command '{command.name}' has no default value")
        additional_count += 1
    log(f"Processed {additional_count} additional commands")
    no_flag_count = 0
    flag_count = 0
    string_arg_count = 0
    for flag in parsed.flags:
        if flag.is_no:
            request.no_flags.append(flag.name)
            no_flag_count += 1
            log(f"Added no-flag: '{flag.name}'")
        else:
            if flag.value:
                request.string_args[flag.name] = flag.value.raw
                string_arg_count += 1
                if flag.value.as_int is not None:
                    request.int_args[flag.name] = flag.value.as_int
                    log(f"Added flag with int value: '{flag.name}'={flag.value.as_int}")
                else:
                    log(f"Added flag with string value: '{flag.name}'='{flag.value.raw}'")
            else:
                request.flag_args.append(flag.name)
                flag_count += 1
                log(f"Added boolean flag: '{flag.name}'")
    log(f"Processed flags: {no_flag_count} no-flags, {flag_count} boolean flags, {string_arg_count} value flags")
    request.extra_commands = [cmd.name for cmd in parsed.additional_commands]
    request.extra_command_defaults = {
        cmd.name: cmd.default_value.raw if cmd.default_value else None
        for cmd in parsed.additional_commands
    }
    log(f"Built request: command='{request.command}', flags={len(request.flag_args)}, no_flags={len(request.no_flags)}, string_args={len(request.string_args)}, extra_commands={len(request.extra_commands)}")
    trace_out()
    return request

def _add_default_value(request: Request, command_name: str, value: ParsedValue) -> None:
    trace_in()
    if not request:
        warn("No request object provided to _add_default_value")
        trace_out()
        return
    if not command_name:
        warn("Empty command name provided to _add_default_value")
        trace_out()
        return
    if not value:
        warn("No value provided to _add_default_value")
        trace_out()
        return
    request.string_args[command_name] = value.raw
    log(f"Added string value for '{command_name}': '{value.raw}'")
    if value.as_int is not None:
        request.int_args[command_name] = value.as_int
        log(f"Added int value for '{command_name}': {value.as_int}")
    else:
        log(f"No int value for '{command_name}' (raw='{value.raw}')")
    log(f"Added command default value: '{command_name}'='{value.raw}' (as_int={value.as_int})")
    trace_out()

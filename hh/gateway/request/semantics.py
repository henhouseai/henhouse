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
    additional_count = len(parsed.additional_commands)
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
                if flag.value.as_value is not None:
                    request.num_args[flag.name] = flag.value.as_value
                    log(f"Added flag with numeric value: '{flag.name}'={flag.value.as_value}")
                    string_arg_count += 1
                else:
                    request.string_args[flag.name] = flag.value.raw
                    log(f"Added flag with string value: '{flag.name}'='{flag.value.raw}'")
                    string_arg_count += 1
            else:
                request.flag_args.append(flag.name)
                flag_count += 1
                log(f"Added boolean flag: '{flag.name}'")
    log(f"Processed flags: {no_flag_count} no-flags, {flag_count} boolean flags, {string_arg_count} value flags")
    request.extra_commands = [cmd.name for cmd in parsed.additional_commands]
    request.extra_command_defaults = {cmd.name: None for cmd in parsed.additional_commands}
    log(f"Built request: command='{request.command}', flags={len(request.flag_args)}, no_flags={len(request.no_flags)}, string_args={len(request.string_args)}, extra_commands={len(request.extra_commands)}")
    trace_out()
    return request


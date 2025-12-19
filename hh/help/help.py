from __future__ import annotations
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.help.help_query import HelpQuery
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error

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

@register_action("help")
@register_command("help")
def help() -> bool:
    trace_in()
    gateway = get_gateway()
    try:
        # Get topic and section from gateway instead of function parameters
        topic = gateway.get_arg('topic')
        section = gateway.get_arg('section')
        
        if not topic:
            topic = 'help'
            log("No topic provided, defaulting to 'help'")
        
        log(f"Getting help for topic: {topic}, section: {section}")
        if section:
            help_query = HelpQuery(topic, section)
            log(f"Created HelpQuery for single section: {topic}/{section}")
        else:
            help_query = HelpQuery(topic)
            log(f"Created HelpQuery for all sections: {topic}")
        result = help_query.json_output()
        log(f"Help query completed successfully")
        import json
        result_data = json.loads(result)
        gateway.response.set_action_response(success_payload(result_data))
        trace_out()
        return True
    except Exception as e:
        warn(f"Help menu action failed: {e}")
        report_error("backend", f"Failed to get help menu: {str(e)}")
        trace_out()
        return False

def main() -> None:
    import sys
    from pathlib import Path
    tools_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(tools_dir))
    args = sys.argv[1:]
    if len(args) == 0:
        args = ['help']
    if len(args) < 1 or len(args) > 2:
        print('Must specify 1 or 2 arguments: topic [section]')
        return
    if len(args) == 1:
        topic = args[0]
        help_query = HelpQuery(topic)
    else:
        topic = args[0]
        section = args[1]
        help_query = HelpQuery(topic, section)
    print(help_query.json_output())

if __name__ == "__main__":
    main()

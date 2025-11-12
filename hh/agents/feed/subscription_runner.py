from __future__ import annotations
import argparse
import sys
from hh.gateway.connection.decorators import db_read
from hh.agents.feed.subscription_service import subscribe, unsubscribe
from hh.agents.feed.subscription_cli import build_subscription_options, add_common_subscribe_args, add_common_unsubscribe_args
from hh.agents.feed.subscription_spec import SUBSCRIPTION_SPECS
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
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

def get_target_id_arg_name(spec_key: str) -> str:
    trace_in()
    if spec_key == "agent":
        result = "target-agent-id"
    elif spec_key == "operator":
        result = "operator-id"
    elif spec_key == "sidecar":
        result = "sidecar-file-id"
    elif spec_key == "keyword":
        result = "keyword-id"
    elif spec_key == "docket":
        result = "docket-id"
    else:
        result = f"{spec_key}-id"
    log(f"Target ID arg name for {spec_key}: {result}")
    trace_out()
    return result

@register_action('subscription_runner')
@register_command('subscribe_agent', action_args=['agent', 'subscribe'])
@register_command('subscribe_ask', action_args=['ask', 'subscribe'])
@register_command('subscribe_task', action_args=['task', 'subscribe'])
@register_command('subscribe_step', action_args=['step', 'subscribe'])
@register_command('subscribe_sidecar', action_args=['sidecar', 'subscribe'])
@register_command('subscribe_keyword', action_args=['keyword', 'subscribe'])
@register_command('subscribe_docket', action_args=['docket', 'subscribe'])
@register_command('subscribe_operator', action_args=['operator', 'subscribe'])
@register_command('unsubscribe_agent', action_args=['agent', 'unsubscribe'])
@register_command('unsubscribe_ask', action_args=['ask', 'unsubscribe'])
@register_command('unsubscribe_task', action_args=['task', 'unsubscribe'])
@register_command('unsubscribe_step', action_args=['step', 'unsubscribe'])
@register_command('unsubscribe_sidecar', action_args=['sidecar', 'unsubscribe'])
@register_command('unsubscribe_keyword', action_args=['keyword', 'unsubscribe'])
@register_command('unsubscribe_docket', action_args=['docket', 'unsubscribe'])
@register_command('unsubscribe_operator', action_args=['operator', 'unsubscribe'])
@db_read
def subscription_runner(conn, argv=None):
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False  
    if not argv:
        argv = sys.argv[1:]
        log("Using sys.argv for argument parsing")
    else:
        log(f"Using provided argv: {argv}")
    if len(argv) < 2:
        warn("Insufficient arguments provided")
        report_error("action", "Usage: <spec_key> <operation> [args...]")
        trace_out()
        return False
    spec_key = argv[0]
    operation = argv[1]
    remaining_args = argv[2:]
    log(f"Processing subscription: spec_key={spec_key}, operation={operation}")
    if spec_key not in SUBSCRIPTION_SPECS:
        warn(f"Unknown spec_key '{spec_key}'")
        report_error("action", f"Unknown spec_key '{spec_key}'. Available: {', '.join(SUBSCRIPTION_SPECS.keys())}")
        trace_out()
        return False
    if operation not in ["subscribe", "unsubscribe"]:
        warn(f"Unknown operation '{operation}'")
        report_error("action", f"Unknown operation '{operation}'. Available: subscribe, unsubscribe")
        trace_out()
        return False
    ap = argparse.ArgumentParser(description=f"{operation.capitalize()} {spec_key}")
    if operation == "subscribe":
        add_common_subscribe_args(ap)
        log("Added subscribe arguments to parser")
    else:
        add_common_unsubscribe_args(ap)
        log("Added unsubscribe arguments to parser")
    target_id_arg = get_target_id_arg_name(spec_key)
    ap.add_argument(f"--{target_id_arg}", type=int, required=True, help=f"{spec_key.capitalize()} ID to {operation}")
    log(f"Added target ID argument: --{target_id_arg}")
    try:
        args = ap.parse_args(remaining_args)
        log("Arguments parsed successfully")
    except SystemExit:
        warn("Argument parsing failed")
        report_error("action", "Invalid arguments provided")
        trace_out()
        return False
    target_id_attr = target_id_arg.replace("-", "_")
    if not hasattr(args, target_id_attr):
        warn(f"Expected argument '--{target_id_arg}' not found")
        report_error("action", f"Expected argument '--{target_id_arg}' not found")
        trace_out()
        return False
    target_id = getattr(args, target_id_attr)
    log(f"Retrieved target ID: {target_id}")
    if not isinstance(target_id, int) or target_id <= 0:
        warn(f"Invalid target ID: {target_id}")
        report_error("action", f"{spec_key.capitalize()} ID must be a positive integer, got: {target_id}")
        trace_out()
        return False
    subscription_options = {}
    if operation == "subscribe":
        subscription_options = build_subscription_options(args)
        log(f"Built subscription options: {subscription_options}")
    
    log(f"Executing {operation} for {spec_key} {target_id}")
    if operation == "subscribe":
        result = subscribe(spec_key=spec_key, agent_id=args.agent_id, target_id=target_id, options=subscription_options)
    else:
        result = unsubscribe(spec_key=spec_key, agent_id=args.agent_id, target_id=target_id)
    
    if isinstance(result, dict):
        result["type"] = "subscription_runner"
        log(f"Subscription operation completed: {result.get('subscription_created', result.get('subscription_removed', 'unknown'))}")
        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True
    else:
        warn(f"Unexpected result type: {type(result)}")
        report_error("backend", f"Unexpected result type: {type(result)}")
        trace_out()
        return False

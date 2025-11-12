from __future__ import annotations
import argparse
from typing import Dict, Union
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

def build_subscription_options(args) -> Dict[str, Union[str, bool]]:
    trace_in()
    opts = {}
    if getattr(args, "all_back_data", False):
        opts["all_back_data"] = True
        log("Added all_back_data option")
    if getattr(args, "since_timestamp", None):
        opts["since_timestamp"] = args.since_timestamp
        log(f"Added since_timestamp option: {args.since_timestamp}")
    if getattr(args, "new_only", False):
        opts["new_only"] = True
        log("Added new_only option")
    if not opts:
        opts["all_back_data"] = True
        log("No options specified, defaulting to all_back_data")
    log(f"Built subscription options: {opts}")
    trace_out()
    return opts

def add_common_subscribe_args(parser: argparse.ArgumentParser) -> None:
    trace_in()
    parser.add_argument("--agent-id", type=int, required=True, help="Agent ID")
    parser.add_argument("--badge-ts", required=True, help="Agent badge timestamp")
    parser.add_argument("--all-back-data", action="store_true", help="Include all historical data")
    parser.add_argument("--since-timestamp", help="Include data since timestamp")
    parser.add_argument("--new-only", action="store_true", help="Only include new data")
    log("Added common subscribe arguments to parser")
    trace_out()

def add_common_unsubscribe_args(parser: argparse.ArgumentParser) -> None:
    trace_in()
    parser.add_argument("--agent-id", type=int, required=True, help="Agent ID")
    parser.add_argument("--badge-ts", required=True, help="Agent badge timestamp")
    log("Added common unsubscribe arguments to parser")
    trace_out()

def add_target_id_arg(parser: argparse.ArgumentParser, target_type: str) -> None:
    trace_in()
    parser.add_argument(f"--{target_type}-id", type=int, required=True, 
                       help=f"{target_type.capitalize()} ID to subscribe to")
    log(f"Added target ID argument for {target_type}")
    trace_out()

def add_target_agent_id_arg(parser: argparse.ArgumentParser) -> None:
    trace_in()
    parser.add_argument("--target-agent-id", type=int, required=True, 
                       help="Target agent ID to subscribe to")
    log("Added target agent ID argument")
    trace_out()

def add_operator_id_arg(parser: argparse.ArgumentParser) -> None:
    trace_in()
    parser.add_argument("--operator-id", type=int, required=True, 
                       help="Operator ID to subscribe to")
    log("Added operator ID argument")
    trace_out()

def add_sidecar_file_id_arg(parser: argparse.ArgumentParser) -> None:
    trace_in()
    parser.add_argument("--sidecar-file-id", type=int, required=True, 
                       help="Sidecar file ID to subscribe to")
    log("Added sidecar file ID argument")
    trace_out()

def add_keyword_id_arg(parser: argparse.ArgumentParser) -> None:
    trace_in()
    parser.add_argument("--keyword-id", type=int, required=True, 
                       help="Keyword ID to subscribe to")
    log("Added keyword ID argument")
    trace_out()

def add_docket_id_arg(parser: argparse.ArgumentParser) -> None:
    trace_in()
    parser.add_argument("--docket-id", type=int, required=True, 
                       help="Docket ID to subscribe to")
    log("Added docket ID argument")
    trace_out()

#!/usr/bin/env python3
from __future__ import annotations
import sys

def main(argv=None) -> int:
    # Import AFTER changing directory to avoid shadowing the http module
    from hh.gateway.gateway import get_gateway
    from hh.gateway.error.error_store import is_error
    
    argv = argv or sys.argv[1:]
    from hh.gateway.gateway import init_gateway
    gateway = init_gateway(argv, "http")
    result = gateway.dispatch()
    # Get output from gateway response
    if gateway and gateway.response:
        print(gateway.response.get_output())
    if is_error():
        print("errors: gateway reported errors for this request", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


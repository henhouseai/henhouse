#!/usr/bin/env python3
from __future__ import annotations
import sys

def main(argv=None) -> int:
    # Import AFTER changing directory to avoid shadowing the http module
    from hh.gateway.gateway import get_gateway
    from hh.gateway.error.error_store import is_error

    argv = argv or sys.argv[1:]

    # Handle SubPage URL resolution: convert --path to --id
    processed_argv = []
    path_value = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--path' and i + 1 < len(argv):
            path_value = argv[i + 1]
            i += 2  # Skip the --path and its value
        else:
            processed_argv.append(arg)
            i += 1

    # If we have a path, resolve it to a page ID
    if path_value is not None:
        try:
            from hh.page.page_registry import resolve_path
            # Initialize gateway temporarily for path resolution
            temp_gateway = init_gateway(["show-page"], "http")
            resolved_page = resolve_path(path_value)

            if resolved_page:
                processed_argv.extend(['--id', str(resolved_page.id)])
            else:
                # Path resolution failed - fallback to treating as name
                processed_argv.extend(['--name', path_value])

        except Exception as e:
            # Path resolution error - fallback to treating as name
            processed_argv.extend(['--name', path_value])

    from hh.gateway.gateway import init_gateway
    gateway = init_gateway(processed_argv, "http")
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


#!/usr/bin/env python3
from __future__ import annotations
import sys

def main(argv=None) -> int:
    # Import AFTER changing directory to avoid shadowing the http module
    from hh.gateway.gateway import get_gateway
    from hh.gateway.error.error_store import is_error

    argv = argv or sys.argv[1:]

    # Handle SubPage URL resolution: resolve base page + subpath
    processed_argv = []
    subpath_value = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--subpath' and i + 1 < len(argv):
            subpath_value = argv[i + 1]
            i += 2  # Skip the --subpath and its value
        else:
            processed_argv.append(arg)
            i += 1

    # If we have a subpath, resolve it using the base page from name/id
    if subpath_value is not None:
        try:
            from hh.page.page_registry import resolve_path as resolve_subpath
            # Initialize gateway temporarily for path resolution
            temp_gateway = init_gateway(["show-page"], "http")

            # The processed_argv now contains --name or --id for the base page
            # We need to resolve the base page first, then apply subpath
            base_page = None

            # Check if we have a name or id argument
            name_arg = None
            id_arg = None
            final_argv = []

            j = 0
            while j < len(processed_argv):
                arg = processed_argv[j]
                if arg == '--name' and j + 1 < len(processed_argv):
                    name_arg = processed_argv[j + 1]
                    j += 2
                elif arg == '--id' and j + 1 < len(processed_argv):
                    id_arg = processed_argv[j + 1]
                    j += 2
                else:
                    final_argv.append(arg)
                    j += 1

            # Resolve base page
            if id_arg:
                from hh.page.page_registry import get_page
                base_page = get_page(int(id_arg))
            elif name_arg:
                from hh.page.page_registry import find_page
                base_page = find_page(str(name_arg))

            if base_page:
                # Apply subpath resolution
                resolved_page = resolve_subpath(base_page, subpath_value)
                if resolved_page:
                    final_argv.extend(['--id', str(resolved_page.id)])
                else:
                    # Subpath resolution failed - use base page
                    final_argv.extend(['--id', str(base_page.id)])
            else:
                # Base page not found - keep original args
                final_argv = processed_argv

            processed_argv = final_argv

        except Exception as e:
            # Path resolution error - keep original args
            pass

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


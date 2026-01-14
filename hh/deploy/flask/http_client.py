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

    # First pass: extract subpath and build initial processed_argv
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--subpath' and i + 1 < len(argv):
            subpath_value = argv[i + 1]
            i += 2  # Skip the --subpath and its value
        else:
            processed_argv.append(arg)
            i += 1

    # If we have a subpath, resolve it
    if subpath_value is not None:
        try:
            from hh.page.page_registry import resolve_path as resolve_subpath, get_page, find_page
            # Initialize gateway temporarily for path resolution
            temp_gateway = init_gateway(["show-page"], "http")

            # Find the base page argument in processed_argv
            base_page = None
            final_argv = []
            skip_next = False

            for j, arg in enumerate(processed_argv):
                if skip_next:
                    skip_next = False
                    continue

                if arg == '--name' and j + 1 < len(processed_argv):
                    name_arg = processed_argv[j + 1]
                    base_page = find_page(str(name_arg))
                    skip_next = True  # Skip the name value
                elif arg == '--id' and j + 1 < len(processed_argv):
                    id_arg = processed_argv[j + 1]
                    base_page = get_page(int(id_arg))
                    skip_next = True  # Skip the id value
                else:
                    final_argv.append(arg)

            if base_page:
                # Apply subpath resolution
                resolved_page = resolve_subpath(base_page, subpath_value)
                if resolved_page:
                    final_argv.extend(['--id', str(resolved_page.id)])
                    print(f"DEBUG: Resolved subpath '{subpath_value}' to page {resolved_page.id}", file=sys.stderr)
                else:
                    # Subpath resolution failed - use base page
                    final_argv.extend(['--id', str(base_page.id)])
                    print(f"DEBUG: Subpath '{subpath_value}' not resolved, using base page {base_page.id}", file=sys.stderr)
            else:
                # Base page not found - keep original args
                final_argv = processed_argv
                print(f"DEBUG: Base page not found for subpath '{subpath_value}'", file=sys.stderr)

            processed_argv = final_argv

        except Exception as e:
            # Path resolution error - keep original args
            print(f"DEBUG: Subpath resolution error: {e}", file=sys.stderr)
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


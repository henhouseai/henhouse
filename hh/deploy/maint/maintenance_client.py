#!/usr/bin/env python3
from __future__ import annotations

import sys

from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import is_error


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    gateway = get_gateway()
    gateway.dispatch(argv, "maintenance")
    output = gateway.response.get_output()
    if output:
        print(output)
    if is_error():
        print("errors: gateway reported errors for this request", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


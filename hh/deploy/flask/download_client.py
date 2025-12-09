#!/usr/bin/env python3
from __future__ import annotations

import io
import sys

from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import is_error


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    gateway = get_gateway()
    gateway.dispatch(argv, "download")
    output = gateway.response.get_output()
    if output:
        print(output)
    return 1 if is_error() else 0


if __name__ == "__main__":
    raise SystemExit(main())


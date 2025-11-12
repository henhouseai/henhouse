from __future__ import annotations
import sys
from hh.gateway import get_gateway

def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    gateway = get_gateway()
    print(gateway.dispatch(argv, "parser"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations
import sys
from hh.gateway import init_gateway

def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    gateway = init_gateway(argv, "parser")
    print(gateway.dispatch())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

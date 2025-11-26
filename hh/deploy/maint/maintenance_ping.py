#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_CYCLES = 5
DEFAULT_DELAY = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Loop maintenance commands via maintenance_client.py",
    )
    parser.add_argument(
        "command",
        help="Maintenance command to run (e.g. page_cache_refresh)",
    )
    parser.add_argument(
        "command_args",
        nargs=argparse.REMAINDER,
        help="Additional args passed to the maintenance command",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=DEFAULT_CYCLES,
        help=f"Number of cycles to run (default: {DEFAULT_CYCLES})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"Seconds to wait between cycles (default: {DEFAULT_DELAY})",
    )
    return parser.parse_args()


def find_project_root() -> Path:
    """Walk up from this file until we find the project root (contains hh/)."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / "hh").is_dir():
            return current
        current = current.parent
    raise RuntimeError("Could not locate project root (hh/ directory)")


def maintenance_client_path() -> Path:
    return Path(__file__).resolve().with_name("maintenance_client.py")


def build_command(
    command_name: str,
    extra_args: Iterable[str],
    include_log: bool,
) -> List[str]:
    cmd = [sys.executable, str(maintenance_client_path()), command_name]
    if include_log and "-log" not in extra_args and "--log" not in extra_args:
        cmd.append("-log")
    cmd.extend(extra_args)
    return cmd


def run_subprocess(cmd: List[str]) -> Tuple[int, str]:
    """Run subprocess and return (exit_code, output)."""
    project_root = find_project_root()
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    if pythonpath:
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{pythonpath}"
    else:
        env["PYTHONPATH"] = str(project_root)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    stdout, stderr = process.communicate()
    exit_code = process.returncode
    return exit_code, stdout


def parse_response(output: str) -> Optional[Dict[str, Any]]:
    """Parse JSON response from output."""
    if not output.strip():
        return None
    try:
        return json.loads(output.strip())
    except json.JSONDecodeError:
        return None


def build_error_summary(errors: List[Dict]) -> Dict[str, Any]:
    """Build error summary with counts by type and duplicate detection."""
    if not errors:
        return {"total": 0, "by_type": {}, "duplicates": []}
    
    by_type = defaultdict(list)
    seen = defaultdict(int)
    
    for err in errors:
        err_type = err.get("type", "unknown")
        content = err.get("content", "")
        by_type[err_type].append(content)
        key = (err_type, content)
        seen[key] += 1
    
    duplicates = [(k, v) for k, v in seen.items() if v > 1]
    
    return {
        "total": len(errors),
        "by_type": dict(by_type),
        "duplicates": duplicates,
    }


def build_debug_summary(entries: List[Dict]) -> Dict[str, Any]:
    """Build debug summary with nested module/file/function structure."""
    if not entries:
        return {"total": 0, "by_level": {}}
    
    by_level = defaultdict(list)
    
    for entry in entries:
        level = entry.get("L", "log")
        by_level[level].append(entry)
    
    level_trees = {}
    for level, level_entries in by_level.items():
        level_trees[level] = build_level_tree(level_entries)
    
    return {
        "total": len(entries),
        "by_level": dict(by_level),
        "level_trees": level_trees,
    }


def build_level_tree(entries: List[Dict]) -> Dict[str, Any]:
    """Build nested tree: module -> file -> function with timestamps."""
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    module_times = defaultdict(list)
    file_times = defaultdict(list)
    
    for entry in entries:
        module = entry.get("F", "unknown")
        file = entry.get("I", "unknown")
        func = entry.get("U", "unknown")
        timestamp = entry.get("T", 0)
        
        tree[module][file][func] += 1
        module_times[module].append(timestamp)
        file_times[(module, file)].append(timestamp)
    
    result = {}
    for module in tree:
        times = module_times[module]
        first_t = min(times) if times else 0
        last_t = max(times) if times else 0
        
        files_data = {}
        for file in tree[module]:
            ftimes = file_times[(module, file)]
            file_first = min(ftimes) if ftimes else 0
            file_last = max(ftimes) if ftimes else 0
            files_data[file] = {
                "first_t": file_first,
                "last_t": file_last,
                "functions": dict(tree[module][file]),
            }
        
        result[module] = {
            "first_t": first_t,
            "last_t": last_t,
            "files": files_data,
        }
    
    return result


def print_error_summary(summary: Dict[str, Any]) -> None:
    """Print formatted error summary."""
    total = summary["total"]
    if total == 0:
        print("Errors: none")
        return
    
    print(f"Errors: {total} total")
    for err_type, messages in summary["by_type"].items():
        count = len(messages)
        first_msg = messages[0] if messages else ""
        if len(first_msg) > 60:
            first_msg = first_msg[:57] + "..."
        print(f"  - {err_type}: {count} ({first_msg})")
    
    if summary["duplicates"]:
        print("  Duplicates detected:")
        for (err_type, content), count in summary["duplicates"]:
            short_content = content[:40] + "..." if len(content) > 40 else content
            print(f"    - {err_type}: '{short_content}' x{count}")


def print_debug_summary(summary: Dict[str, Any]) -> None:
    """Print formatted debug summary with nested tree structure."""
    total = summary["total"]
    if total == 0:
        print("Debug: none")
        return
    
    print(f"\nDebug: {total} entries")
    
    level_trees = summary.get("level_trees", {})
    by_level = summary.get("by_level", {})
    
    level_order = ["warn", "log", "debug"]
    other_levels = [l for l in level_trees.keys() if l not in level_order]
    
    for level in level_order + other_levels:
        if level not in level_trees:
            continue
        
        tree = level_trees[level]
        count = len(by_level.get(level, []))
        print(f"\n{level.upper()} ({count} entries):")
        
        sorted_modules = sorted(tree.items(), key=lambda x: x[1]["first_t"])
        
        for module, module_data in sorted_modules:
            first_t = module_data["first_t"]
            last_t = module_data["last_t"]
            print(f"  - {module} ({first_t:.3f}s / {last_t:.3f}s)")
            
            files = module_data["files"]
            sorted_files = sorted(files.items(), key=lambda x: x[1]["first_t"])
            
            for file, file_data in sorted_files:
                file_first = file_data["first_t"]
                file_last = file_data["last_t"]
                print(f"    - {file} ({file_first:.3f}s / {file_last:.3f}s)")
                
                for func, func_count in file_data["functions"].items():
                    print(f"      - {func} ({func_count})")


def print_summary(exit_code: int, response: Optional[Dict[str, Any]]) -> None:
    """Print full summary of response."""
    if response is None:
        print("Response: PARSE FAILED (malformed or empty)")
        print(f"Exit code: {exit_code}")
        return
    
    status = response.get("status", "unknown")
    
    expected_exit = 0 if status == "ok" else 1
    match_str = "MATCH" if exit_code == expected_exit else "MISMATCH"
    print(f"Status: {status} (exit code: {exit_code}) - {match_str}")
    
    if exit_code != expected_exit:
        print(f"  WARNING: Exit code {exit_code} does not match status '{status}'")
    
    errors = response.get("errors", [])
    if errors:
        error_summary = build_error_summary(errors)
        print_error_summary(error_summary)
    else:
        print("Errors: none")
    
    debug_data = response.get("debug", {})
    entries = debug_data.get("entries", []) if debug_data else []
    if entries:
        debug_summary = build_debug_summary(entries)
        print_debug_summary(debug_summary)
    else:
        print("Debug: none")
    
    data = response.get("data")
    if data:
        if isinstance(data, dict):
            keys = list(data.keys())
            print(f"\nData: {len(keys)} keys ({', '.join(keys[:5])}{'...' if len(keys) > 5 else ''})")
        else:
            print(f"\nData: {type(data).__name__}")


def run_cycle(command: str, extra_args: Iterable[str]) -> bool:
    """Run a maintenance command cycle, returning success status."""
    first_cmd = build_command(command, extra_args, include_log=False)
    exit_code, output = run_subprocess(first_cmd)
    response = parse_response(output)
    
    print_summary(exit_code, response)
    
    if exit_code == 0:
        return True
    
    print("\n--- Retry with -log ---")
    retry_cmd = build_command(command, extra_args, include_log=True)
    retry_exit_code, retry_output = run_subprocess(retry_cmd)
    retry_response = parse_response(retry_output)
    
    print_summary(retry_exit_code, retry_response)
    
    return retry_exit_code == 0


def main() -> int:
    args = parse_args()
    if args.cycles < 1:
        print("cycles must be >= 1", file=sys.stderr)
        return 1

    for cycle in range(1, args.cycles + 1):
        print(f"\n=== Cycle {cycle}/{args.cycles} ===")
        success = run_cycle(args.command, args.command_args)
        if not success:
            print(f"\nCycle {cycle} failed", file=sys.stderr)
            return 1
        if cycle != args.cycles and args.delay > 0:
            time.sleep(args.delay)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

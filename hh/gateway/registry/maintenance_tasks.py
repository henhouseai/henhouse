"""
Maintenance Task Registry

This module provides a decorator for registering maintenance tasks with metadata
about which worker daemon should run them, what status fields trigger them, etc.

The registry allows worker daemons to dynamically discover which tasks they should run
based on their daemon name (extracted from worker filename).
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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


# Registry structure: {daemon_name: {command_name: task_info}}
_MAINTENANCE_TASK_REGISTRY: Dict[str, Dict[str, Dict[str, Any]]] = {}


def register_maintenance_task(
    command_name: str,
    daemon: str = "maintenance",
    status_field: Optional[str] = None,
    trigger_type: str = "cache_refresh",
    priority: int = 50,
):
    """Decorator to register a maintenance task with daemon and trigger metadata.

    Args:
        command_name: The command name (e.g., "video-cache-refresh")
        daemon: Which worker daemon runs this task (default: "maintenance")
        status_field: Status field that triggers this task (e.g., "stale_video")
        trigger_type: "cache_refresh" or "job_queue" or "periodic"
        priority: Execution priority (higher runs first)

    Example:
        @register_maintenance_task(
            "video-cache-refresh",
            daemon="maintenance",
            status_field="stale_video",
            trigger_type="cache_refresh",
            priority=50
        )
        @register_action("video-cache-refresh")
        def video_cache_refresh():
            # ... implementation
    """
    def decorator(func):
        trace_in()

        # Initialize daemon's registry if needed
        if daemon not in _MAINTENANCE_TASK_REGISTRY:
            _MAINTENANCE_TASK_REGISTRY[daemon] = {}
            log(f"Initialized task registry for daemon: {daemon}")

        # Register this task
        _MAINTENANCE_TASK_REGISTRY[daemon][command_name] = {
            "status_field": status_field,
            "trigger_type": trigger_type,
            "priority": priority,
            "is_job_queue": (trigger_type == "job_queue"),
        }

        log(f"Registered maintenance task: {command_name} -> daemon={daemon}, status_field={status_field}, trigger_type={trigger_type}")
        trace_out()
        return func
    return decorator


def get_tasks_for_daemon(daemon_name: str, status: Dict[str, Any]) -> List[Tuple[str, bool]]:
    """Get work docket for specific daemon based on current status.

    Args:
        daemon_name: Name of the daemon (e.g., "maintenance", "migration")
        status: Status dictionary with counts/flags for various conditions

    Returns:
        List of (command, is_job_queue) tuples to execute
    """
    trace_in()
    tasks = []
    daemon_registry = _MAINTENANCE_TASK_REGISTRY.get(daemon_name, {})

    if not daemon_registry:
        log(f"No registered tasks for daemon: {daemon_name}")
        trace_out()
        return tasks

    # Sort by priority (descending - higher priority runs first)
    sorted_tasks = sorted(
        daemon_registry.items(),
        key=lambda x: x[1]["priority"],
        reverse=True
    )

    for command, task_info in sorted_tasks:
        # Check if task should run based on trigger type
        if task_info["trigger_type"] == "cache_refresh":
            status_field = task_info["status_field"]
            if status_field and status.get(status_field, 0) > 0:
                tasks.append((command, task_info["is_job_queue"]))
                log(f"Task {command} triggered: {status_field}={status.get(status_field, 0)}")
        elif task_info["trigger_type"] == "periodic":
            # Periodic tasks always run
            tasks.append((command, task_info["is_job_queue"]))
            log(f"Periodic task {command} scheduled")
        # job_queue tasks are handled separately via pending_jobs in worker

    log(f"Found {len(tasks)} tasks for daemon {daemon_name}")
    trace_out()
    return tasks


def get_registered_daemons() -> List[str]:
    """Get list of all daemon names that have registered tasks."""
    return list(_MAINTENANCE_TASK_REGISTRY.keys())


def get_daemon_task_count(daemon_name: str) -> int:
    """Get count of registered tasks for a specific daemon."""
    return len(_MAINTENANCE_TASK_REGISTRY.get(daemon_name, {}))

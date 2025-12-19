import os
import subprocess
from pathlib import Path
from typing import Dict, Any
from hh.gateway.registry.registry import register_action
from hh.gateway.registry.registry import register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import success_payload
from hh.gateway.error.error_store import report_error
from datetime import datetime

trace_in = lambda message=None: None
trace_out = lambda message=None: None
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

def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            else:
                print(f"Error: {result.stdout}")
            return False
        if result.stdout:
            print(result.stdout)
        return True
    except Exception as e:
        print(f"Exception running command: {cmd}")
        print(f"Exception: {e}")
        return False

def write_stage_signal(repo_path: str, text: str) -> None:
    """Write stage signal file."""
    stage_path = os.path.join(repo_path, 'stage')
    with open(stage_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text.strip() + "\n")

def sanitize_for_ref(text: str) -> str:
    """Convert arbitrary text to a safe git ref slug."""
    import unicodedata
    import re
    # Unicode normalize and ASCII fold
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lower = ascii_text.strip().lower()
    # Replace whitespace with hyphens first
    lower = re.sub(r"\s+", "-", lower)
    # Replace any disallowed char with '-'
    lower = re.sub(r"[^a-z0-9._-]", "-", lower)
    # Collapse multiple hyphens
    lower = re.sub(r"-+", "-", lower)
    # Trim separators
    return lower.strip("-._")

def build_stage_names(env: str, hook_id: str, desc: str | None) -> tuple[str, str, str]:
    """Build stage branch name, tag, and title."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H%M%S")
    suffix = f"-{sanitize_for_ref(hook_id)}"
    if desc:
        suffix += f"-{sanitize_for_ref(desc)}"
    branch = f"stage/{sanitize_for_ref(env)}/{timestamp}{suffix}"
    title = f"Stage: {hook_id} {desc or ''}".strip()
    return branch, '', title

def run_git(repo_path: str, args: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run git command and return result."""
    import shlex
    cmd = ["git", "-C", repo_path] + args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    if check and proc.returncode != 0:
        raise RuntimeError(f"git command failed ({proc.returncode}):\n$ {' '.join(shlex.quote(a) for a in cmd)}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    return proc.returncode, out, err

@register_action('push_project')
@register_command('push_project')
def push_project() -> bool:
    """Push to stage with message requirement."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    # Get message from command line argument
    message = gateway.get_arg('message')
    if not message or not message.strip():
        warn("Message is required for push_project")
        report_error("action", "Message is required for push_project. Use --message 'your message'")
        trace_out()
        return False

    message = message.strip()
    log(f"Push message: {message}")

    # Detect project context
    from hh.deploy.deploy_utils import detect_project_context
    project_name, repo_root = detect_project_context()
    log(f"Using project: {project_name} at {repo_root}")
    
    # Quick sanity check
    if not os.path.isdir(os.path.join(repo_root, ".git")):
        warn(f"{repo_root} is not a git repository (no .git)")
        report_error("action", f"{repo_root} is not a git repository (no .git)")
        trace_out()
        return False

    try:
        # Write stage signal file containing the message
        write_stage_signal(str(repo_root), message)
        log(f"Created stage signal file with message: {message}")
        
        # Build branch name and title
        branch, tag, title = build_stage_names("linux", message, None)
        log(f"Created branch name: {branch}")
        
        # Create/update branch and commit
        run_git(str(repo_root), ["checkout", "-B", branch])
        log(f"Checked out branch: {branch}")
        
        # Stage everything
        run_git(str(repo_root), ["add", "-A"])
        log("Staged all changes")
        
        # Build commit message with trailers
        trailers = [
            f"Stage-Done: true",
            f"Env: linux",
            f"Hook: {message}",
        ]
        body = "\n".join(trailers)
        
        # Detect if anything to commit
        rc, out, _ = run_git(str(repo_root), ["status", "--porcelain"], check=False)
        has_changes = (rc == 0 and out.strip() != "")
        commit_args = ["commit", "-m", f"{title}\n\n{body}"]
        if not has_changes:
            commit_args.insert(1, "--allow-empty")
            log("No changes detected, creating empty commit")
        else:
            log("Changes detected, creating commit")
        
        run_git(str(repo_root), commit_args)
        log(f"Created commit: {title}")
        
        # Push branch
        run_git(str(repo_root), ["push", "-u", "origin", branch])
        log(f"Pushed branch to origin: {branch}")
        
        # Final result
        result_data = {
            "project_name": project_name,
            "project_path": str(repo_root),
            "message": message,
            "branch": branch,
            "title": title,
            "has_changes": has_changes,
            "stage_file_created": True,
            "status": "pushed"
        }
        gateway.response.set_action_response(success_payload(result_data))
        log(f"Successfully pushed to stage: {branch}")
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Error during stage push: {e}")
        report_error("backend", f"Error during stage push: {e}")
        trace_out()
        return False

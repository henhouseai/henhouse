import subprocess
from pathlib import Path
from typing import List, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway

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

from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

def auto_scan_user_keys(project_owner: str) -> List[str]:
    """Auto-scan user's SSH keys from their home directory."""
    trace_in()
    keys = []
    try:
        user_home = Path(f'/home/{project_owner}')
        ssh_dir = user_home / '.ssh'
        
        # Scan authorized_keys file
        authorized_keys_file = ssh_dir / 'authorized_keys'
        if authorized_keys_file.exists():
            with open(authorized_keys_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        keys.append(line)
            log(f"Found {len(keys)} keys in {project_owner}'s authorized_keys")
        
        # Scan id_rsa.pub if it exists
        id_rsa_pub = ssh_dir / 'id_rsa.pub'
        if id_rsa_pub.exists():
            with open(id_rsa_pub, 'r') as f:
                key = f.read().strip()
                if key and key not in keys:
                    keys.append(key)
                    log(f"Found {project_owner}'s id_rsa.pub key")
        
        # Scan other .pub files
        for pub_file in ssh_dir.glob('*.pub'):
            if pub_file.name != 'id_rsa.pub':
                with open(pub_file, 'r') as f:
                    key = f.read().strip()
                    if key and key not in keys:
                        keys.append(key)
                        log(f"Found {project_owner}'s {pub_file.name} key")
        
    except Exception as e:
        warn(f"Failed to auto-scan keys for {project_owner}: {str(e)}")
    finally:
        trace_out()
    return keys

def generate_ssh_keys(user: str, project_name: str) -> Dict[str, Any]:
    trace_in()
    gateway = get_gateway()
    try:
        user_home = Path(f'/home/{user}')
        ssh_dir = user_home / '.ssh'
        # All users own their own .ssh directories
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        subprocess.run([
            'ssh-keygen', '-t', 'rsa', '-b', '4096', '-f', str(ssh_dir / 'id_rsa'),
            '-N', '', '-C', f'{user}@{project_name}'
        ], check=True, capture_output=True)
        # All users own their own SSH directory and files
        gateway.files.chown(str(ssh_dir), user)
        gateway.files.chown(str(ssh_dir / 'id_rsa'), user)
        gateway.files.chown(str(ssh_dir / 'id_rsa.pub'), user)
        with open(ssh_dir / 'id_rsa.pub', 'r') as f:
            public_key = f.read().strip()
        return {
            "public_key": public_key,
            "private_key_path": str(ssh_dir / 'id_rsa'),
            "public_key_path": str(ssh_dir / 'id_rsa.pub')
        }
    except Exception as e:
        warn(f"Failed to generate SSH keys for {user}: {str(e)}")
        return {"error": str(e)}
    finally:
        trace_out()

def add_user_key(user: str, user_key: str) -> None:
    trace_in()
    gateway = get_gateway()
    try:
        user_home = Path(f'/home/{user}')
        authorized_keys = user_home / '.ssh' / 'authorized_keys'
        with open(authorized_keys, 'a') as f:
            f.write(f'{user_key}\n')
        
        # All users own their own authorized_keys
        gateway.files.chown(str(authorized_keys), user)
        
        log(f"Added user key for {user}")
    except Exception as e:
        warn(f"Failed to add user key for {user}: {str(e)}")
    finally:
        trace_out()

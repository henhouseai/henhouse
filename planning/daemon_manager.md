# Henhouse Daemon Manager System Architecture

This document covers the comprehensive daemon management system that provides auto-scaling, load balancing, and centralized orchestration for all Henhouse daemons including Flask web tiers and maintenance workers.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Current State Analysis](#2-current-state-analysis)
3. [Auto-Scaling Architecture](#3-auto-scaling-architecture)
4. [Meta-Daemon Design](#4-meta-daemon-design)
5. [Flask Tier Scaling](#5-flask-tier-scaling)
6. [Maintenance Worker Scaling](#6-maintenance-worker-scaling)
7. [JSON Configuration System](#7-json-configuration-system)
8. [Coordinated Logging](#8-coordinated-logging)
9. [Implementation Strategy](#9-implementation-strategy)
10. [Technical Challenges](#10-technical-challenges)

## Agent Quick Reference

- **Meta-Daemon**: Central daemon manager that monitors and scales all other daemons
- **Horizontal Scaling**: Multiple workers per daemon type that scale based on load
- **Async Handoff**: Flask apps use fire-and-forget request delegation to sub-daemons
- **JSON State Management**: Dynamic daemon configuration with rolling boxcar dampening
- **Tempo Signaling**: Flask apps ping daemon manager with request frequency metrics
- **Fixed Nginx**: Four main Flask tiers stay on fixed ports, sub-daemons use dynamic ports
- **Cross-Platform**: Full Windows/Unix compatibility for development and deployment

---

## 1. System Overview

The Henhouse Daemon Manager is a sophisticated auto-scaling orchestration system that provides dynamic horizontal scaling for all daemon types in the Henhouse ecosystem. The system is built around a meta-daemon architecture that monitors load patterns and automatically scales daemon pools up and down based on demand.

### Core Design Principles

- **Horizontal Scaling**: Scale out with multiple workers rather than scaling up individual processes
- **Auto-Scaling**: Dynamic scaling based on load metrics with rolling boxcar dampening
- **Fixed Nginx Integration**: Main Flask tiers remain on fixed ports to avoid Nginx restarts
- **Async Handoff**: High-performance request delegation using fire-and-forget patterns
- **Centralized Orchestration**: Single meta-daemon manages all daemon lifecycle decisions
- **Cross-Platform**: Full compatibility across Windows, macOS, and Linux environments

### Architecture Overview

```
Meta-Daemon (Daemon Manager)
    ↓
Monitors Load Metrics & Queue Depths
    ↓
Makes Scaling Decisions (Rolling Boxcar Dampening)
    ↓
Updates JSON Configuration
    ↓
Spawns/Terminates Daemon Instances
    ↓
Flask Tiers (Fixed Ports) ←→ Sub-Daemons (Dynamic Ports)
Maintenance Workers (Pool)
```

### Daemon Types Managed

1. **Flask Web Tiers**: 4 main tiers (guest, verified, admin, root) + dynamic sub-daemons
2. **Maintenance Workers**: Horizontal pool of maintenance task processors
3. **Meta-Daemon**: The daemon manager itself (self-managing)

---

## 2. Current State Analysis

### Existing Flask Architecture

The current Flask system uses a single universal app (`app.py`) deployed with tier suffixes:
- `app_guest.py` (port 5001)
- `app_verified.py` (port 5002) 
- `app_admin.py` (port 5003)
- `app_root.py` (port 5004)

Each Flask app:
- Runs as tier-specific user (`{project}_{tier}`)
- Routes requests to `mcp_client.py` or `http_client.py` via subprocess
- Uses semaphore-based concurrency limiting
- Handles multiple route types (`/mcp`, `/img`, `/`, `/upload-file`)

### Existing Maintenance Architecture

The current maintenance system uses a single monolithic worker (`worker.py`) that:
- Polls for work every 5 seconds
- Processes job queue items and stale cache refreshes
- Updates job statuses and handles error recovery
- Provides intelligent heartbeat logging

### Scaling Limitations

**Current Flask Limitations**:
- Fixed concurrency limits per tier
- No horizontal scaling capability
- Subprocess bottlenecks during high load
- Manual process management

**Current Maintenance Limitations**:
- Single worker processes all maintenance tasks
- No load-based scaling
- Manual multi-worker coordination required

---

## 3. Auto-Scaling Architecture

### Meta-Daemon Design

The daemon manager operates as a meta-daemon that:

1. **Monitors Load Metrics**:
   - Flask request tempo (requests per second per tier)
   - Maintenance job queue depth and processing rates
   - Response times and error rates
   - Resource utilization (CPU, memory)

2. **Makes Scaling Decisions**:
   - Uses rolling boxcar averaging to prevent scaling jitter
   - Applies configurable thresholds for scale-up/scale-down
   - Considers minimum/maximum daemon limits
   - Implements graceful scaling with health checks

3. **Manages Daemon Lifecycle**:
   - Spawns new daemon instances on dynamic ports
   - Terminates idle daemons during low load periods
   - Updates JSON configuration atomically
   - Coordinates graceful shutdowns

4. **Provides Centralized Status**:
   - Real-time daemon health monitoring
   - Performance metrics collection
   - Error tracking and alerting
   - Historical scaling decision logs

### Scaling Algorithms

**Scale-Up Triggers**:
- Flask: Average response time > 2 seconds OR request queue depth > 10
- Maintenance: Pending job count > 50 OR processing lag > 5 minutes
- Resource: CPU usage > 80% for 2+ minutes

**Scale-Down Triggers**:
- Flask: Average response time < 0.5 seconds AND queue depth < 2 for 5+ minutes
- Maintenance: Pending job count < 5 for 10+ minutes
- Resource: CPU usage < 30% for 10+ minutes

**Rolling Boxcar Dampening**:
```python
class ScalingDecision:
    def __init__(self, window_size=10):
        self.metrics_window = deque(maxlen=window_size)
        self.decision_threshold = 0.7  # 70% of samples must agree
    
    def should_scale_up(self, current_metric):
        self.metrics_window.append(current_metric > scale_up_threshold)
        return sum(self.metrics_window) / len(self.metrics_window) > self.decision_threshold
```

---

## 4. Meta-Daemon Design

### Core Responsibilities

The meta-daemon (`daemon_manager.py`) serves as the central orchestrator with these responsibilities:

1. **Load Monitoring**:
   - Receives tempo signals from Flask tiers
   - Monitors maintenance worker status and queue depths
   - Tracks resource utilization across all daemons
   - Maintains historical metrics for trend analysis

2. **Scaling Decisions**:
   - Applies rolling boxcar averaging to prevent jitter
   - Makes scale-up/scale-down decisions based on thresholds
   - Coordinates scaling across multiple daemon types
   - Implements graceful scaling with health verification

3. **Configuration Management**:
   - Maintains authoritative JSON configuration file
   - Provides atomic updates to daemon pool configurations
   - Handles configuration versioning and rollback
   - Ensures consistency across all daemon instances

4. **Process Lifecycle**:
   - Spawns new daemon instances with proper user/permissions
   - Allocates dynamic ports and manages port conflicts
   - Monitors daemon health and implements auto-restart
   - Coordinates graceful shutdowns during scale-down

### Meta-Daemon Implementation

```python
@register_action("daemon_manager")
@register_command("daemon_manager")
def daemon_manager() -> bool:
    """Meta-daemon for managing all Henhouse daemons."""
    trace_in()
    gateway = get_gateway()
    
    action = gateway.get_arg("action") or "run"
    
    if action == "run":
        return run_meta_daemon()
    elif action == "status":
        return get_daemon_status()
    elif action == "scale":
        return manual_scale_command()
    elif action == "stop":
        return stop_meta_daemon()
    
    trace_out()
    return True

def run_meta_daemon():
    """Main meta-daemon loop."""
    while RUNNING:
        # Collect metrics from all daemon types
        flask_metrics = collect_flask_metrics()
        maintenance_metrics = collect_maintenance_metrics()
        
        # Make scaling decisions
        flask_decisions = make_flask_scaling_decisions(flask_metrics)
        maintenance_decisions = make_maintenance_scaling_decisions(maintenance_metrics)
        
        # Execute scaling actions
        execute_scaling_decisions(flask_decisions, maintenance_decisions)
        
        # Update configuration
        update_daemon_configuration()
        
        # Sleep until next check
        time.sleep(SCALING_CHECK_INTERVAL)
```

### Tempo Signaling System

Flask tiers send tempo signals to the meta-daemon:

```python
# In Flask app after async handoff
async def signal_tempo(tier, request_type):
    """Signal request tempo to meta-daemon."""
    tempo_data = {
        "tier": tier,
        "timestamp": time.time(),
        "request_type": request_type,
        "response_time": calculate_response_time()
    }
    
    # Fire-and-forget signal to meta-daemon
    asyncio.create_task(send_tempo_signal(tempo_data))

async def send_tempo_signal(tempo_data):
    """Send tempo signal to meta-daemon via local socket/pipe."""
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                "http://127.0.0.1:9999/tempo", 
                json=tempo_data,
                timeout=0.1  # Very short timeout
            )
    except:
        pass  # Fire-and-forget, ignore failures
```

---

## 5. Flask Tier Scaling

### Fixed Tier + Dynamic Sub-Daemon Architecture

The Flask scaling system maintains the existing 4-tier structure while adding horizontal scaling capability:

**Fixed Tier Daemons** (Never change - no Nginx restarts needed):
- `guest` tier: Port 5001 (main daemon)
- `verified` tier: Port 5002 (main daemon)  
- `admin` tier: Port 5003 (main daemon)
- `root` tier: Port 5004 (main daemon)

**Dynamic Sub-Daemons** (Scale up/down based on load):
- `guest` sub-daemons: Ports 5011, 5012, 5013, etc.
- `verified` sub-daemons: Ports 5021, 5022, 5023, etc.
- `admin` sub-daemons: Ports 5031, 5032, 5033, etc.
- `root` sub-daemons: Ports 5041, 5042, 5043, etc.

### Async Handoff Implementation

The main Flask tiers act as "dumb" load balancers using async handoff:

```python
import asyncio
import aiohttp
import json
from collections import deque

class FlaskLoadBalancer:
    def __init__(self, tier):
        self.tier = tier
        self.round_robin_counter = 0
        self.config_cache = None
        self.config_last_read = 0
        
    def get_daemon_config(self):
        """Read daemon config with caching."""
        now = time.time()
        if now - self.config_last_read > 1.0:  # Refresh every second
            try:
                with open('/srv/henhouse/daemon_config.json', 'r') as f:
                    self.config_cache = json.load(f)
                self.config_last_read = now
            except:
                pass  # Use cached config on read failure
        return self.config_cache
    
    def get_next_daemon_port(self):
        """Get next available sub-daemon port via round-robin."""
        config = self.get_daemon_config()
        if not config:
            return None
            
        active_daemons = config.get('active_daemons', {}).get('flask', {}).get(self.tier, [])
        if not active_daemons:
            return None
            
        # Round-robin through available daemons
        self.round_robin_counter = (self.round_robin_counter + 1) % len(active_daemons)
        return active_daemons[self.round_robin_counter]['port']

# Flask route handler with async handoff
load_balancer = FlaskLoadBalancer(TIER_SUFFIX)

@app.route('/<path:path>')
async def async_handoff_handler(path):
    """Handle request with async handoff to sub-daemon."""
    target_port = load_balancer.get_next_daemon_port()
    
    if target_port and target_port != current_port:
        # Async handoff to sub-daemon
        asyncio.create_task(handoff_request(target_port, path, request))
        
        # Signal tempo to meta-daemon
        asyncio.create_task(signal_tempo(TIER_SUFFIX, "handoff"))
        
        return "Request handed off", 202  # HTTP 202 Accepted
    
    # Handle locally if no sub-daemons available
    return handle_request_locally(path)

async def handoff_request(target_port, path, original_request):
    """Fire-and-forget handoff to sub-daemon."""
    try:
        async with aiohttp.ClientSession() as session:
            # Reconstruct request for sub-daemon
            request_data = {
                'path': path,
                'method': original_request.method,
                'headers': dict(original_request.headers),
                'args': dict(original_request.args),
                'form': dict(original_request.form),
                'json': original_request.get_json(silent=True)
            }
            
            await session.post(
                f'http://127.0.0.1:{target_port}/handle',
                json=request_data,
                timeout=30
            )
    except Exception as e:
        # Log handoff failures but don't block main thread
        logging.error(f"Handoff to port {target_port} failed: {e}")
```

### Sub-Daemon Spawning

The meta-daemon spawns sub-daemons using the same Flask app with different ports:

```python
def spawn_flask_sub_daemon(tier, port):
    """Spawn a new Flask sub-daemon for the specified tier."""
    trace_in()
    
    project_name = get_project_name()
    user = f"{project_name}_{tier}"
    app_path = f"/srv/{project_name}/{project_name}_{tier}.py"
    log_file = f"/srv/{project_name}/logs/flask_{project_name}_{tier}_{port}.log"
    
    # Environment variables for sub-daemon
    env = os.environ.copy()
    env.update({
        'PORT': str(port),
        'LOG_FILE': log_file,
        'SUB_DAEMON': 'true',  # Flag to indicate this is a sub-daemon
        'MAIN_TIER_PORT': str(get_main_tier_port(tier))
    })
    
    # Spawn sub-daemon process
    cmd = ['python3', app_path]
    process = subprocess.Popen(
        cmd,
        env=env,
        cwd=f"/srv/{project_name}",
        user=user,  # Run as tier-specific user
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE
    )
    
    # Verify sub-daemon started successfully
    time.sleep(2)
    if process.poll() is None:
        log(f"Successfully spawned {tier} sub-daemon on port {port} (PID: {process.pid})")
        return process.pid
    else:
        warn(f"Failed to spawn {tier} sub-daemon on port {port}")
        return None
```

### Port Allocation Strategy

```python
class PortAllocator:
    """Manages dynamic port allocation for sub-daemons."""
    
    PORT_RANGES = {
        'guest': (5011, 5019),
        'verified': (5021, 5029), 
        'admin': (5031, 5039),
        'root': (5041, 5049)
    }
    
    def allocate_port(self, tier):
        """Allocate next available port for tier."""
        start_port, end_port = self.PORT_RANGES[tier]
        active_ports = self.get_active_ports(tier)
        
        for port in range(start_port, end_port + 1):
            if port not in active_ports:
                return port
        
        return None  # No ports available
    
    def get_active_ports(self, tier):
        """Get list of currently active ports for tier."""
        config = load_daemon_config()
        active_daemons = config.get('active_daemons', {}).get('flask', {}).get(tier, [])
        return [daemon['port'] for daemon in active_daemons]
```

---

## 6. Maintenance Worker Scaling

### Horizontal Maintenance Worker Pool

The maintenance scaling system creates a pool of maintenance workers that process jobs concurrently:

**Scaling Metrics**:
- Pending job count in `maintenance_jobs` table
- Average job processing time
- Queue depth trends over time
- Worker utilization rates

**Scaling Thresholds**:
- Scale up: Pending jobs > 50 OR processing lag > 5 minutes
- Scale down: Pending jobs < 5 for 10+ minutes AND multiple workers active

### Maintenance Worker Coordination

Unlike Flask tiers, maintenance workers need coordination to avoid processing the same jobs:

```python
class MaintenanceWorkerPool:
    """Manages pool of maintenance workers with job coordination."""
    
    def __init__(self):
        self.worker_id = f"worker_{uuid.uuid4().hex[:8]}"
        self.heartbeat_interval = 30  # seconds
        
    def claim_job(self, job_type):
        """Atomically claim a job from the queue."""
        gateway = get_gateway()
        
        # Use database transaction to atomically claim job
        with gateway.conn.transaction():
            # Find available job
            jobs = gateway.conn.read(
                """
                SELECT id FROM maintenance_jobs 
                WHERE status = 'pending' AND job_type = %s
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
                FOR UPDATE
                """,
                [job_type]
            )
            
            if not jobs:
                return None
                
            job_id = jobs[0]['id']
            
            # Claim the job
            gateway.conn.update(
                """
                UPDATE maintenance_jobs 
                SET status = 'running', 
                    worker_id = %s,
                    started_at = NOW(6)
                WHERE id = %s
                """,
                [self.worker_id, job_id]
            )
            
            return job_id
    
    def send_heartbeat(self):
        """Send heartbeat to meta-daemon."""
        heartbeat_data = {
            'worker_id': self.worker_id,
            'timestamp': time.time(),
            'status': 'active',
            'jobs_processed': self.jobs_processed_count,
            'current_job': self.current_job_id
        }
        
        # Send to meta-daemon via local communication
        send_worker_heartbeat(heartbeat_data)
```

### Maintenance Worker Spawning

```python
def spawn_maintenance_worker():
    """Spawn a new maintenance worker."""
    trace_in()
    
    project_root = find_project_root()
    worker_script = project_root / "hh" / "deploy" / "maintenance" / "worker.py"
    
    # Generate unique worker ID
    worker_id = f"maint_{int(time.time())}_{os.getpid()}"
    
    # Environment for worker
    env = os.environ.copy()
    env.update({
        'WORKER_ID': worker_id,
        'WORKER_MODE': 'pool',  # Indicates this is part of a worker pool
        'META_DAEMON_PORT': '9999'  # For heartbeat communication
    })
    
    # Spawn worker process
    cmd = [sys.executable, str(worker_script), '--worker-id', worker_id]
    process = subprocess.Popen(
        cmd,
        env=env,
        cwd=str(project_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE
    )
    
    # Verify worker started
    time.sleep(2)
    if process.poll() is None:
        log(f"Successfully spawned maintenance worker {worker_id} (PID: {process.pid})")
        return {
            'worker_id': worker_id,
            'pid': process.pid,
            'started_at': time.time()
        }
    else:
        warn(f"Failed to spawn maintenance worker {worker_id}")
        return None
```

### Job Queue Coordination

To prevent race conditions, maintenance workers use database-level coordination:

```python
def get_next_maintenance_task(worker_id):
    """Get next maintenance task with atomic claiming."""
    gateway = get_gateway()
    
    # Try to claim a job from the queue first
    job_id = claim_job_atomically(worker_id)
    if job_id:
        return ('job_queue', job_id)
    
    # If no queued jobs, check for stale cache items
    stale_task = find_stale_cache_task()
    if stale_task:
        return ('cache_refresh', stale_task)
    
    return None

def claim_job_atomically(worker_id):
    """Atomically claim a job using database locking."""
    gateway = get_gateway()
    
    try:
        # Use SELECT FOR UPDATE to prevent race conditions
        with gateway.conn.transaction():
            jobs = gateway.conn.read(
                """
                SELECT id, job_type FROM maintenance_jobs
                WHERE status = 'pending'
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                []
            )
            
            if not jobs:
                return None
            
            job = jobs[0]
            
            # Claim the job
            gateway.conn.update(
                """
                UPDATE maintenance_jobs
                SET status = 'running',
                    worker_id = %s,
                    started_at = NOW(6),
                    updated_at = NOW(6)
                WHERE id = %s
                """,
                [worker_id, job['id']]
            )
            
            return job['id']
            
    except Exception as e:
        warn(f"Failed to claim job atomically: {e}")
        return None
```

---

## 7. JSON Configuration System

### Configuration File Structure

The daemon manager maintains a comprehensive JSON configuration file that serves as the single source of truth for all daemon states:

```json
{
    "version": "1.0",
    "project_name": "henhouse",
    "last_updated": "2024-01-15T10:30:00.123Z",
    "meta_daemon": {
        "pid": 12340,
        "started_at": "2024-01-15T09:00:00.000Z",
        "status": "running",
        "config_file": "/srv/henhouse/daemon_config.json",
        "log_file": "/srv/henhouse/logs/daemon_manager.log"
    },
    "scaling_config": {
        "maintenance": {
            "min_workers": 1,
            "max_workers": 8,
            "scale_up_threshold": 50,
            "scale_down_threshold": 5,
            "scale_check_interval": 30,
            "boxcar_window_size": 10,
            "boxcar_threshold": 0.7
        },
        "flask": {
            "guest": {
                "min_workers": 1,
                "max_workers": 4,
                "base_port": 5001,
                "sub_port_range": [5011, 5019],
                "scale_up_response_time": 2.0,
                "scale_down_response_time": 0.5,
                "scale_up_queue_depth": 10,
                "scale_down_queue_depth": 2
            },
            "verified": {
                "min_workers": 1,
                "max_workers": 4,
                "base_port": 5002,
                "sub_port_range": [5021, 5029],
                "scale_up_response_time": 2.0,
                "scale_down_response_time": 0.5,
                "scale_up_queue_depth": 10,
                "scale_down_queue_depth": 2
            },
            "admin": {
                "min_workers": 1,
                "max_workers": 4,
                "base_port": 5003,
                "sub_port_range": [5031, 5039],
                "scale_up_response_time": 2.0,
                "scale_down_response_time": 0.5,
                "scale_up_queue_depth": 10,
                "scale_down_queue_depth": 2
            },
            "root": {
                "min_workers": 1,
                "max_workers": 4,
                "base_port": 5004,
                "sub_port_range": [5041, 5049],
                "scale_up_response_time": 2.0,
                "scale_down_response_time": 0.5,
                "scale_up_queue_depth": 10,
                "scale_down_queue_depth": 2
            }
        }
    },
    "active_daemons": {
        "maintenance": [
            {
                "worker_id": "maint_1704441000_12345",
                "pid": 12345,
                "status": "running",
                "started_at": "2024-01-15T09:00:00.000Z",
                "last_heartbeat": "2024-01-15T10:29:45.123Z",
                "jobs_processed": 127,
                "current_job": 456
            },
            {
                "worker_id": "maint_1704441030_12346", 
                "pid": 12346,
                "status": "running",
                "started_at": "2024-01-15T09:00:30.000Z",
                "last_heartbeat": "2024-01-15T10:29:50.456Z",
                "jobs_processed": 98,
                "current_job": null
            }
        ],
        "flask": {
            "guest": [
                {
                    "daemon_id": "guest_main",
                    "port": 5001,
                    "pid": 12347,
                    "status": "running",
                    "is_main": true,
                    "started_at": "2024-01-15T09:00:00.000Z",
                    "last_tempo": "2024-01-15T10:29:55.789Z",
                    "requests_per_minute": 45.2,
                    "avg_response_time": 1.2
                },
                {
                    "daemon_id": "guest_sub_1",
                    "port": 5011,
                    "pid": 12348,
                    "status": "running", 
                    "is_main": false,
                    "started_at": "2024-01-15T09:15:00.000Z",
                    "last_tempo": "2024-01-15T10:29:58.123Z",
                    "requests_per_minute": 38.7,
                    "avg_response_time": 0.8
                }
            ],
            "verified": [
                {
                    "daemon_id": "verified_main",
                    "port": 5002,
                    "pid": 12349,
                    "status": "running",
                    "is_main": true,
                    "started_at": "2024-01-15T09:00:00.000Z",
                    "last_tempo": "2024-01-15T10:29:52.456Z",
                    "requests_per_minute": 12.3,
                    "avg_response_time": 0.6
                }
            ],
            "admin": [
                {
                    "daemon_id": "admin_main",
                    "port": 5003,
                    "pid": 12350,
                    "status": "running",
                    "is_main": true,
                    "started_at": "2024-01-15T09:00:00.000Z",
                    "last_tempo": "2024-01-15T10:29:47.789Z",
                    "requests_per_minute": 3.1,
                    "avg_response_time": 0.4
                }
            ],
            "root": [
                {
                    "daemon_id": "root_main",
                    "port": 5004,
                    "pid": 12351,
                    "status": "running",
                    "is_main": true,
                    "started_at": "2024-01-15T09:00:00.000Z",
                    "last_tempo": "2024-01-15T10:29:43.123Z",
                    "requests_per_minute": 1.8,
                    "avg_response_time": 0.3
                }
            ]
        }
    },
    "scaling_history": [
        {
            "timestamp": "2024-01-15T09:15:00.000Z",
            "action": "scale_up",
            "daemon_type": "flask",
            "tier": "guest",
            "reason": "avg_response_time exceeded 2.0s",
            "before_count": 1,
            "after_count": 2,
            "new_daemon": {
                "daemon_id": "guest_sub_1",
                "port": 5011,
                "pid": 12348
            }
        }
    ],
    "performance_metrics": {
        "last_collected": "2024-01-15T10:30:00.000Z",
        "maintenance": {
            "pending_jobs": 23,
            "processing_rate": 4.2,
            "avg_job_time": 12.5,
            "queue_depth_trend": [25, 23, 21, 23, 20]
        },
        "flask": {
            "guest": {
                "total_requests_per_minute": 83.9,
                "avg_response_time": 1.0,
                "queue_depth": 3,
                "error_rate": 0.02
            },
            "verified": {
                "total_requests_per_minute": 12.3,
                "avg_response_time": 0.6,
                "queue_depth": 0,
                "error_rate": 0.01
            },
            "admin": {
                "total_requests_per_minute": 3.1,
                "avg_response_time": 0.4,
                "queue_depth": 0,
                "error_rate": 0.0
            },
            "root": {
                "total_requests_per_minute": 1.8,
                "avg_response_time": 0.3,
                "queue_depth": 0,
                "error_rate": 0.0
            }
        }
    }
}
```

### Atomic Configuration Updates

The daemon manager ensures atomic updates to prevent race conditions:

```python
class DaemonConfigManager:
    """Manages atomic updates to daemon configuration."""
    
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.lock_path = Path(f"{config_path}.lock")
        self.backup_path = Path(f"{config_path}.backup")
        
    def update_config(self, update_func):
        """Atomically update configuration using file locking."""
        import fcntl
        
        # Acquire exclusive lock
        with open(self.lock_path, 'w') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            
            try:
                # Read current config
                current_config = self.load_config()
                
                # Create backup
                self.create_backup(current_config)
                
                # Apply updates
                updated_config = update_func(current_config)
                
                # Write atomically using temp file + rename
                temp_path = Path(f"{self.config_path}.tmp")
                with open(temp_path, 'w') as f:
                    json.dump(updated_config, f, indent=2, default=str)
                
                # Atomic rename
                temp_path.rename(self.config_path)
                
                return updated_config
                
            except Exception as e:
                # Restore from backup on failure
                self.restore_backup()
                raise e
            finally:
                # Lock automatically released when file closes
                pass
    
    def add_daemon(self, daemon_type, tier, daemon_info):
        """Add new daemon to configuration."""
        def update_func(config):
            if daemon_type not in config['active_daemons']:
                config['active_daemons'][daemon_type] = {}
            if tier not in config['active_daemons'][daemon_type]:
                config['active_daemons'][daemon_type][tier] = []
                
            config['active_daemons'][daemon_type][tier].append(daemon_info)
            config['last_updated'] = datetime.now().isoformat()
            return config
            
        return self.update_config(update_func)
    
    def remove_daemon(self, daemon_type, tier, daemon_id):
        """Remove daemon from configuration."""
        def update_func(config):
            if (daemon_type in config['active_daemons'] and 
                tier in config['active_daemons'][daemon_type]):
                
                daemons = config['active_daemons'][daemon_type][tier]
                config['active_daemons'][daemon_type][tier] = [
                    d for d in daemons if d.get('daemon_id') != daemon_id
                ]
                
            config['last_updated'] = datetime.now().isoformat()
            return config
            
        return self.update_config(update_func)
```

### Configuration Caching Strategy

Flask tiers cache configuration to minimize file I/O:

```python
class ConfigCache:
    """Cached configuration reader for Flask tiers."""
    
    def __init__(self, config_path, cache_ttl=1.0):
        self.config_path = config_path
        self.cache_ttl = cache_ttl
        self.cached_config = None
        self.last_read = 0
        self.last_mtime = 0
        
    def get_config(self):
        """Get configuration with caching and mtime checking."""
        now = time.time()
        
        # Check if cache is still valid
        if (self.cached_config and 
            now - self.last_read < self.cache_ttl):
            return self.cached_config
            
        # Check if file has been modified
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if (self.cached_config and 
                current_mtime <= self.last_mtime):
                # File hasn't changed, refresh cache timestamp
                self.last_read = now
                return self.cached_config
        except OSError:
            # File doesn't exist or can't be read
            return self.cached_config
            
        # Read fresh configuration
        try:
            with open(self.config_path, 'r') as f:
                self.cached_config = json.load(f)
            self.last_read = now
            self.last_mtime = current_mtime
        except (OSError, json.JSONDecodeError) as e:
            # Keep using cached config on read failure
            log(f"Failed to read config: {e}")
            
        return self.cached_config
    
    def get_active_daemons(self, daemon_type, tier):
        """Get active daemons for specific type and tier."""
        config = self.get_config()
        if not config:
            return []
            
        return (config.get('active_daemons', {})
                     .get(daemon_type, {})
                     .get(tier, []))
```

---

## 8. Coordinated Logging

### Multi-Daemon Logging Challenges

With multiple daemons writing to log files simultaneously, coordination is essential to prevent:
- Log line interleaving
- Race conditions during file writes
- Lost log messages
- Corrupted log files

### Logging Architecture Options

**Option 1: Log Coordinator Service (Recommended)**

A dedicated logging service that all daemons send messages to:

```python
class LogCoordinator:
    """Centralized logging coordinator for all daemons."""
    
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.message_queue = asyncio.Queue()
        self.log_files = {}  # daemon_type -> file handle
        self.running = True
        
    async def start(self):
        """Start the log coordinator service."""
        # Create log processing task
        asyncio.create_task(self.process_log_messages())
        
        # Start HTTP server for log message reception
        app = web.Application()
        app.router.add_post('/log', self.receive_log_message)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 9998)
        await site.start()
        
        log("Log coordinator started on port 9998")
        
    async def receive_log_message(self, request):
        """Receive log message from daemon."""
        try:
            log_data = await request.json()
            await self.message_queue.put(log_data)
            return web.Response(status=200)
        except Exception as e:
            return web.Response(status=400, text=str(e))
    
    async def process_log_messages(self):
        """Process log messages from queue."""
        while self.running:
            try:
                # Get log message from queue
                log_data = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                # Write to appropriate log file
                await self.write_log_message(log_data)
                
            except asyncio.TimeoutError:
                # Flush all log files periodically
                await self.flush_all_logs()
                continue
            except Exception as e:
                print(f"Log coordinator error: {e}")
    
    async def write_log_message(self, log_data):
        """Write log message to appropriate file."""
        daemon_type = log_data.get('daemon_type', 'unknown')
        daemon_id = log_data.get('daemon_id', 'unknown')
        timestamp = log_data.get('timestamp')
        level = log_data.get('level', 'INFO')
        message = log_data.get('message', '')
        
        # Determine log file
        log_file_key = f"{daemon_type}_{daemon_id}"
        if log_file_key not in self.log_files:
            log_path = self.log_dir / f"{log_file_key}.log"
            self.log_files[log_file_key] = open(log_path, 'a', buffering=1)
        
        # Write formatted log entry
        log_file = self.log_files[log_file_key]
        formatted_message = f"{timestamp} [{level}] [{daemon_id}] {message}\n"
        log_file.write(formatted_message)
```

**Daemon-Side Logging Client**:

```python
class DaemonLogger:
    """Logging client for daemons to send messages to coordinator."""
    
    def __init__(self, daemon_type, daemon_id):
        self.daemon_type = daemon_type
        self.daemon_id = daemon_id
        self.coordinator_url = "http://127.0.0.1:9998/log"
        self.session = None
        
    async def log_message(self, level, message):
        """Send log message to coordinator."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        log_data = {
            'daemon_type': self.daemon_type,
            'daemon_id': self.daemon_id,
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        
        try:
            async with self.session.post(
                self.coordinator_url, 
                json=log_data,
                timeout=0.5
            ) as response:
                pass  # Fire-and-forget
        except:
            # Fallback to stderr on coordinator failure
            print(f"[{self.daemon_id}] {level}: {message}")
    
    def info(self, message):
        asyncio.create_task(self.log_message('INFO', message))
        
    def warn(self, message):
        asyncio.create_task(self.log_message('WARN', message))
        
    def error(self, message):
        asyncio.create_task(self.log_message('ERROR', message))
```

**Option 2: File Locking (Simpler Alternative)**

For simpler deployments, use file locking for coordinated writes:

```python
import fcntl
import time

class AtomicLogger:
    """Thread-safe logger using file locking."""
    
    def __init__(self, log_file, daemon_id):
        self.log_file = log_file
        self.daemon_id = daemon_id
        
    def log(self, level, message):
        """Write log message with file locking."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        formatted_message = f"{timestamp} [{level}] [{self.daemon_id}] {message}\n"
        
        # Retry logic for lock acquisition
        for attempt in range(3):
            try:
                with open(self.log_file, 'a') as f:
                    # Acquire exclusive lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    f.write(formatted_message)
                    f.flush()
                    # Lock automatically released when file closes
                    break
            except IOError:
                # Lock acquisition failed, retry with backoff
                time.sleep(0.01 * (2 ** attempt))
        else:
            # Fallback to stderr if all retries failed
            print(f"[{self.daemon_id}] {level}: {message}")
```

**Option 3: Separate Log Files + Aggregator**

Each daemon writes to its own log file, with optional aggregation:

```python
class SeparateFileLogger:
    """Each daemon writes to separate log file."""
    
    def __init__(self, log_dir, daemon_type, daemon_id):
        self.log_file = Path(log_dir) / f"{daemon_type}_{daemon_id}.log"
        self.daemon_id = daemon_id
        
    def log(self, level, message):
        """Write to daemon-specific log file."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        formatted_message = f"{timestamp} [{level}] [{self.daemon_id}] {message}\n"
        
        with open(self.log_file, 'a') as f:
            f.write(formatted_message)
            f.flush()

class LogAggregator:
    """Optional aggregator to merge daemon logs chronologically."""
    
    def __init__(self, log_dir, output_file):
        self.log_dir = Path(log_dir)
        self.output_file = output_file
        
    def aggregate_logs(self, time_range=None):
        """Merge all daemon logs into single chronological file."""
        log_entries = []
        
        # Read all daemon log files
        for log_file in self.log_dir.glob("*_*.log"):
            with open(log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        log_entries.append(line.strip())
        
        # Sort chronologically
        log_entries.sort(key=lambda x: x.split(' ')[0:2])
        
        # Write aggregated log
        with open(self.output_file, 'w') as f:
            for entry in log_entries:
                f.write(entry + '\n')
```

### Recommended Logging Strategy

For the daemon manager system, **Option 1 (Log Coordinator Service)** is recommended because:

1. **Performance**: Async, non-blocking logging for all daemons
2. **Reliability**: No file locking contention or race conditions  
3. **Scalability**: Handles many concurrent daemons efficiently
4. **Flexibility**: Can route different daemon types to different files
5. **Monitoring**: Centralized point for log analysis and alerting

The log coordinator runs as part of the meta-daemon and provides a simple HTTP API for all other daemons to send log messages.

---

## 9. Implementation Strategy

### Phase 2A: Foundation (Weeks 1-2)

**Core Infrastructure**:
1. **JSON Configuration System**
   - Implement `DaemonConfigManager` with atomic updates
   - Create configuration file schema and validation
   - Build configuration caching for Flask tiers
   - Add configuration backup and rollback capabilities
   - **Location**: JSON state/config file in project directory (not deployed)
   - **Cache Integration**: Registered via cache cleanup system so it can be purged safely

2. **Unified Daemon Manager Framework**
   - **CLI Action**: Build CLI action (living under project folder, not deployed) that can `start|stop|status` any daemon
   - **Unified Management**: Same manager understands both web app daemons (four Flask tiers) and maintenance jobs
   - **Behavioral Requirements**:
     - `start`/`stop` with optional job args (`start page-cache`, `stop orphan`, or no args = all jobs)
     - `status` reports each job individually (running/stopped, PID info, last heartbeat, etc.)
     - Must work identically on Windows/Mac/Linux for dev testing
     - Provide hooks so a future cron/systemd entry can invoke the manager on reboot to auto-start everything according to the JSON config
   - **Design Philosophy**: Straightforward—read JSON, exec subprocesses, log results. No hidden state, no new micro-frameworks
   - Implement daemon process management utilities
   - Add cross-platform process discovery and control
   - Build heartbeat and health monitoring system
   - **Future Integration**: Eventually the web UI (root/admin panel) can drive it

3. **Logging Coordination**
   - Implement log coordinator service
   - Create daemon logging clients
   - Add log aggregation and rotation
   - Build log monitoring and alerting

**Deliverables**:
- Unified daemon manager CLI (`daemon-manager start/stop/status`) for Flask tiers + maintenance jobs
- JSON configuration file with manual daemon management
- Coordinated logging system for multiple daemons
- Process management utilities for spawning/terminating daemons

### Phase 2B: Multi-Worker Support (Weeks 3-4)

**Maintenance Worker Pool**:
1. **Worker Coordination**
   - Implement atomic job claiming with database locking
   - Add worker heartbeat and health monitoring
   - Create worker pool management (spawn/terminate)
   - Build job queue coordination and conflict resolution

2. **Flask Sub-Daemon Support**
   - Modify Flask app to support sub-daemon mode
   - Implement port allocation and management
   - Add sub-daemon spawning and health checks
   - Create basic round-robin load balancing

**Deliverables**:
- Multiple maintenance workers processing jobs concurrently
- Flask sub-daemons running on dynamic ports
- Basic load balancing between main and sub-daemons
- Worker health monitoring and auto-restart

### Phase 2C: Auto-Scaling (Weeks 5-6)

**Scaling Algorithms**:
1. **Metrics Collection**
   - Implement tempo signaling from Flask tiers
   - Add maintenance queue depth monitoring
   - Create performance metrics collection
   - Build rolling boxcar averaging system

2. **Scaling Decisions**
   - Implement scale-up/scale-down threshold logic
   - Add rolling boxcar dampening to prevent jitter
   - Create scaling decision logging and history
   - Build manual scaling override commands

**Deliverables**:
- Automatic scaling based on load metrics
- Rolling boxcar dampening to prevent scaling jitter
- Scaling decision history and monitoring
- Manual scaling controls for testing and overrides

### Phase 2D: Async Handoff (Weeks 7-8)

**Flask Request Delegation**:
1. **Async Handoff Implementation**
   - Convert Flask routes to async handlers
   - Implement fire-and-forget request delegation
   - Add request serialization and reconstruction
   - Create sub-daemon request handling endpoints

2. **Load Balancing Enhancement**
   - Implement intelligent load balancing algorithms
   - Add health-based daemon selection
   - Create request routing optimization
   - Build performance monitoring and tuning

**Deliverables**:
- High-performance async request handoff
- Intelligent load balancing across sub-daemons
- Request routing optimization
- Performance monitoring and metrics

### Phase 2E: Production Hardening (Weeks 9-10)

**Reliability and Monitoring**:
1. **Error Handling and Recovery**
   - Implement comprehensive error handling
   - Add automatic daemon restart on failures
   - Create graceful shutdown procedures
   - Build error alerting and notification

2. **Performance Optimization**
   - Optimize configuration caching and updates
   - Tune scaling algorithms and thresholds
   - Implement resource usage monitoring
   - Add performance profiling and optimization

**Deliverables**:
- Production-ready daemon manager with error recovery
- Optimized performance and resource usage
- Comprehensive monitoring and alerting
- Documentation and operational procedures

### Phase 3: Deployment + Nginx Integration

**Deployment Script Integration**:
1. **Deploy Scripts Alignment**
   - Update `hh/deploy/http/deploy_http.py` (and the SSL variant) plus `nginx_config_helpers.py`
   - Accept desired counts per Flask tier (guest/verified/admin/root) and emit Nginx upstream config with that many workers
   - Know how many maintenance daemons to expect and include them in restart routines
   - Allow SSL vs. non-SSL flows via a single script with a flag (non-SSL used only temporarily for Let's Encrypt challenges)

2. **Nginx Reload + Daemon Coordination**
   - After writing configs, the deploy script should call the daemon manager to start/stop the correct number of Flask instances and maintenance jobs
   - Then reload Nginx to pick up new upstream configurations
   - Ensure atomic updates: config changes → daemon restarts → Nginx reload

3. **Auto-Start on Reboot**
   - Provide a root-owned cron/systemd unit that runs the daemon manager (via sudo gateway wrapper)
   - Configured stack comes back automatically after a reboot—no manual intervention
   - Reads JSON config to determine which daemons to start

**Deliverables**:
- Updated deployment scripts with daemon count parameters
- Nginx config generation with dynamic upstream worker counts
- Integrated daemon manager calls in deployment workflow
- Cron/systemd unit for automatic startup on reboot

### Implementation Milestones

**Milestone 1 (Week 2)**: Basic daemon manager with manual scaling
- CLI commands for daemon management
- JSON configuration system
- Coordinated logging

**Milestone 2 (Week 4)**: Multi-worker support
- Multiple maintenance workers
- Flask sub-daemons
- Basic load balancing

**Milestone 3 (Week 6)**: Auto-scaling functionality
- Automatic scaling based on metrics
- Rolling boxcar dampening
- Scaling decision monitoring

**Milestone 4 (Week 8)**: High-performance request handling
- Async handoff implementation
- Intelligent load balancing
- Performance optimization

**Milestone 5 (Week 10)**: Production deployment
- Error recovery and reliability
- Performance tuning
- Monitoring and alerting

### Testing Strategy

**Unit Testing**:
- Configuration management functions
- Scaling algorithm logic
- Process management utilities
- Logging coordination components

**Integration Testing**:
- Multi-daemon coordination
- Database job claiming
- Flask request handoff
- Configuration updates

**Load Testing**:
- Scaling behavior under load
- Performance with multiple workers
- Request handling capacity
- Resource usage patterns

**Deployment Testing**:
- Cross-platform compatibility
- Production environment deployment
- Failure recovery scenarios
- Monitoring and alerting

---

## 10. Technical Challenges

### Challenge 1: Race Conditions in Job Claiming

**Problem**: Multiple maintenance workers attempting to claim the same job simultaneously.

**Solution**: Database-level atomic operations using `SELECT FOR UPDATE SKIP LOCKED`:

```python
def claim_job_atomically(worker_id):
    """Atomically claim job using database locking."""
    with gateway.conn.transaction():
        jobs = gateway.conn.read(
            """
            SELECT id FROM maintenance_jobs
            WHERE status = 'pending'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """,
            []
        )
        
        if jobs:
            job_id = jobs[0]['id']
            gateway.conn.update(
                "UPDATE maintenance_jobs SET status = 'running', worker_id = %s WHERE id = %s",
                [worker_id, job_id]
            )
            return job_id
    return None
```

**Key Points**:
- `SKIP LOCKED` prevents blocking when multiple workers compete
- Transaction ensures atomicity of claim operation
- Worker ID tracking enables job ownership and recovery

### Challenge 2: Configuration File Consistency

**Problem**: Multiple processes reading/writing configuration simultaneously causing corruption or inconsistency.

**Solution**: File locking with atomic writes using temp files:

```python
def atomic_config_update(config_path, update_func):
    """Atomically update configuration file."""
    lock_path = f"{config_path}.lock"
    
    with open(lock_path, 'w') as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        
        # Read current config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Apply updates
        updated_config = update_func(config)
        
        # Write atomically via temp file
        temp_path = f"{config_path}.tmp"
        with open(temp_path, 'w') as f:
            json.dump(updated_config, f, indent=2)
        
        # Atomic rename
        os.rename(temp_path, config_path)
```

**Key Points**:
- Exclusive file locking prevents concurrent modifications
- Temp file + rename ensures atomic updates
- Backup and rollback capabilities for error recovery

### Challenge 3: Port Allocation Conflicts

**Problem**: Multiple sub-daemons attempting to bind to the same port.

**Solution**: Centralized port allocation with conflict detection:

```python
class PortAllocator:
    """Thread-safe port allocation."""
    
    def __init__(self):
        self.allocated_ports = set()
        self.lock = threading.Lock()
    
    def allocate_port(self, tier, preferred_port=None):
        """Allocate port with conflict detection."""
        with self.lock:
            start_port, end_port = self.get_port_range(tier)
            
            if preferred_port and self.is_port_available(preferred_port):
                self.allocated_ports.add(preferred_port)
                return preferred_port
            
            for port in range(start_port, end_port + 1):
                if self.is_port_available(port):
                    self.allocated_ports.add(port)
                    return port
            
            return None  # No ports available
    
    def is_port_available(self, port):
        """Check if port is available for binding."""
        if port in self.allocated_ports:
            return False
            
        # Test actual port binding
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False
```

**Key Points**:
- Thread-safe allocation prevents race conditions
- Actual socket binding test ensures port availability
- Port range segregation by tier prevents conflicts

### Challenge 4: Graceful Daemon Shutdown

**Problem**: Ensuring daemons complete current work before termination during scale-down.

**Solution**: Graceful shutdown protocol with timeout:

```python
class GracefulShutdown:
    """Manages graceful daemon shutdown."""
    
    def __init__(self, daemon_pid, shutdown_timeout=30):
        self.daemon_pid = daemon_pid
        self.shutdown_timeout = shutdown_timeout
    
    def shutdown_daemon(self):
        """Gracefully shutdown daemon with timeout."""
        try:
            # Send SIGTERM for graceful shutdown
            os.kill(self.daemon_pid, signal.SIGTERM)
            
            # Wait for graceful shutdown
            for _ in range(self.shutdown_timeout):
                if not self.is_process_running(self.daemon_pid):
                    return True
                time.sleep(1)
            
            # Force kill if timeout exceeded
            os.kill(self.daemon_pid, signal.SIGKILL)
            return False
            
        except ProcessLookupError:
            # Process already terminated
            return True
    
    def is_process_running(self, pid):
        """Check if process is still running."""
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
```

**Daemon-Side Shutdown Handler**:

```python
class DaemonShutdownHandler:
    """Handles graceful shutdown in daemon processes."""
    
    def __init__(self):
        self.shutdown_requested = False
        self.current_job = None
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown_signal)
        signal.signal(signal.SIGINT, self.handle_shutdown_signal)
    
    def handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signal gracefully."""
        self.shutdown_requested = True
        
        if self.current_job:
            log(f"Graceful shutdown requested, completing job {self.current_job}")
        else:
            log("Graceful shutdown requested, no active job")
    
    def should_continue_processing(self):
        """Check if daemon should continue processing."""
        return not self.shutdown_requested
    
    def complete_current_job(self):
        """Mark current job as complete."""
        self.current_job = None
```

**Key Points**:
- SIGTERM allows daemons to complete current work
- Timeout prevents hung processes from blocking scale-down
- SIGKILL as last resort for unresponsive daemons

### Challenge 5: Cross-Platform Compatibility

**Problem**: Process management differences between Windows and Unix systems.

**Solution**: Platform-specific process management abstraction:

```python
class ProcessManager:
    """Cross-platform process management."""
    
    def __init__(self):
        self.is_windows = sys.platform == 'win32'
    
    def spawn_daemon(self, cmd, env=None, cwd=None, user=None):
        """Spawn daemon process cross-platform."""
        if self.is_windows:
            return self._spawn_windows(cmd, env, cwd)
        else:
            return self._spawn_unix(cmd, env, cwd, user)
    
    def _spawn_windows(self, cmd, env, cwd):
        """Spawn daemon on Windows."""
        return subprocess.Popen(
            cmd,
            env=env,
            cwd=cwd,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
    
    def _spawn_unix(self, cmd, env, cwd, user):
        """Spawn daemon on Unix with user switching."""
        if user and os.getuid() == 0:  # Running as root
            # Switch to specified user
            def preexec_fn():
                import pwd
                pw_record = pwd.getpwnam(user)
                os.setgid(pw_record.pw_gid)
                os.setuid(pw_record.pw_uid)
            
            return subprocess.Popen(
                cmd,
                env=env,
                cwd=cwd,
                preexec_fn=preexec_fn,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
        else:
            return subprocess.Popen(
                cmd,
                env=env,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
    
    def find_processes(self, name_pattern):
        """Find processes by name pattern."""
        if self.is_windows:
            return self._find_processes_windows(name_pattern)
        else:
            return self._find_processes_unix(name_pattern)
    
    def _find_processes_windows(self, name_pattern):
        """Find processes on Windows using tasklist."""
        try:
            result = subprocess.run(
                ['tasklist', '/FO', 'CSV'],
                capture_output=True,
                text=True,
                check=True
            )
            
            processes = []
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                parts = line.split('","')
                if len(parts) >= 2:
                    name = parts[0].strip('"')
                    pid = parts[1].strip('"')
                    if name_pattern in name:
                        processes.append({'name': name, 'pid': int(pid)})
            
            return processes
        except:
            return []
    
    def _find_processes_unix(self, name_pattern):
        """Find processes on Unix using ps."""
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                check=True
            )
            
            processes = []
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 11:
                    pid = int(parts[1])
                    command = ' '.join(parts[10:])
                    if name_pattern in command:
                        processes.append({'name': command, 'pid': pid})
            
            return processes
        except:
            return []
```

**Key Points**:
- Platform detection enables appropriate process management
- Windows uses `CREATE_NO_WINDOW` to prevent console windows
- Unix supports user switching for tier-specific daemons
- Process discovery adapted for platform-specific tools

### Challenge 6: Scaling Decision Jitter

**Problem**: Rapid scaling up/down due to temporary load spikes causing instability.

**Solution**: Rolling boxcar averaging with hysteresis:

```python
class ScalingDecisionEngine:
    """Prevents scaling jitter using rolling averages."""
    
    def __init__(self, window_size=10, threshold=0.7):
        self.window_size = window_size
        self.threshold = threshold
        self.metrics_history = deque(maxlen=window_size)
        self.last_scale_action = None
        self.last_scale_time = 0
        self.min_scale_interval = 60  # Minimum seconds between scaling actions
    
    def should_scale_up(self, current_metric, scale_up_threshold):
        """Determine if should scale up based on rolling average."""
        # Add current metric to history
        self.metrics_history.append(current_metric > scale_up_threshold)
        
        # Need minimum samples
        if len(self.metrics_history) < self.window_size:
            return False
        
        # Check if enough samples exceed threshold
        exceeding_count = sum(self.metrics_history)
        exceeding_ratio = exceeding_count / len(self.metrics_history)
        
        # Prevent rapid scaling
        if (time.time() - self.last_scale_time) < self.min_scale_interval:
            return False
        
        # Hysteresis: require higher threshold if last action was scale-down
        effective_threshold = self.threshold
        if self.last_scale_action == 'scale_down':
            effective_threshold += 0.1  # Require 80% instead of 70%
        
        should_scale = exceeding_ratio >= effective_threshold
        
        if should_scale:
            self.last_scale_action = 'scale_up'
            self.last_scale_time = time.time()
        
        return should_scale
    
    def should_scale_down(self, current_metric, scale_down_threshold):
        """Determine if should scale down based on rolling average."""
        # Add current metric to history (inverted for scale-down)
        self.metrics_history.append(current_metric < scale_down_threshold)
        
        # Need minimum samples
        if len(self.metrics_history) < self.window_size:
            return False
        
        # Check if enough samples are below threshold
        below_count = sum(self.metrics_history)
        below_ratio = below_count / len(self.metrics_history)
        
        # Prevent rapid scaling
        if (time.time() - self.last_scale_time) < self.min_scale_interval:
            return False
        
        # Hysteresis: require higher threshold if last action was scale-up
        effective_threshold = self.threshold
        if self.last_scale_action == 'scale_up':
            effective_threshold += 0.1  # Require 80% instead of 70%
        
        should_scale = below_ratio >= effective_threshold
        
        if should_scale:
            self.last_scale_action = 'scale_down'
            self.last_scale_time = time.time()
        
        return should_scale
```

**Key Points**:
- Rolling window smooths out temporary spikes
- Hysteresis prevents rapid oscillation between scale-up/scale-down
- Minimum interval prevents excessive scaling frequency
- Configurable thresholds allow tuning for different workloads

---

This comprehensive daemon manager design provides a robust foundation for auto-scaling Henhouse daemons while maintaining the existing architecture's stability and cross-platform compatibility. The implementation strategy breaks down the complex system into manageable phases, each building upon the previous foundation to create a production-ready auto-scaling daemon orchestration system.

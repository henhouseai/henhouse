from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from hh.gateway.connection.connection import r_query
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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

class TrainingMatrix:
    """Core training logic and gate resolution for agent onboarding."""
    
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[3]
        self.training_dir = self.project_root / "bootstrap" / "training"
    
    def _parse_versioned_json(self, text: str) -> Dict[str, Any]:
        """Strip leading // VERSION: lines when present and parse JSON."""
        trace_in()
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("// VERSION:"):
            result = json.loads("\n".join(lines[1:]))
        else:
            result = json.loads(text)
        trace_out()
        return result
    
    def load_gate_config(self, role: str) -> Dict[str, Any]:
        """Load training gate configuration for specific role."""
        trace_in()
        config_file = self.training_dir / f"{role}_gates.json"
        if not config_file.exists():
            warn(f"Training config file not found: {config_file}")
            trace_out()
            return {"gates": []}
        try:
            config_text = config_file.read_text(encoding="utf-8")
            config = self._parse_versioned_json(config_text)
            log(f"Loaded training config for role {role}: {len(config.get('gates', []))} gates")
            trace_out()
            return config
        except Exception as e:
            warn(f"Failed to load training config for role {role}: {e}")
            trace_out()
            return {"gates": []}
    
    def build_training_matrix(self) -> Dict[str, Any]:
        """Build complete training matrix from all gate configuration files."""
        trace_in()
        all_docs: Dict[str, Dict[str, Any]] = {}
        role_docs: Dict[str, List[str]] = {}
        
        for config_file in self.training_dir.glob("*_gates.json"):
            try:
                data = self._parse_versioned_json(config_file.read_text(encoding="utf-8"))
                role = data.get("role")
                gates = data.get("gates", [])
                if role not in role_docs:
                    role_docs[role] = []
                for gate in gates:
                    doc_path = gate.get("doc_path", "")
                    if doc_path:
                        all_docs.setdefault(doc_path, {"path": doc_path, "filename": Path(doc_path).name})
                        role_docs[role].append(doc_path)
            except Exception as e:
                warn(f"Failed to process training config {config_file}: {e}")
                continue
        
        result = {"documents": list(all_docs.values()), "role_docs": role_docs}
        log(f"Built training matrix: {len(result['documents'])} documents, {len(role_docs)} roles")
        trace_out()
        return result
    
    def discover_roles(self) -> List[str]:
        """Discover available roles from training gate files."""
        trace_in()
        roles: List[str] = []
        for config_file in self.training_dir.glob("*_gates.json"):
            try:
                data = self._parse_versioned_json(config_file.read_text(encoding="utf-8"))
                role = str(data.get("role", "")).strip()
                if role and role != "general" and role not in roles:
                    roles.append(role)
            except Exception:
                continue
        roles.sort()
        log(f"Discovered {len(roles)} roles: {roles}")
        trace_out()
        return roles
    
    def get_next_gate(self, conn, agent_id: int, role: str) -> Optional[Tuple[str, str, str]]:
        """Get next incomplete training gate for agent. Returns (doc_path, filename, question) or None."""
        trace_in()
        general_cfg = self.load_gate_config("general")
        role_cfg = self.load_gate_config(role)
        combined = general_cfg.get("gates", []) + role_cfg.get("gates", [])
        
        for gate in combined:
            doc_path = gate.get("doc_path", "")
            question = gate.get("question", "")
            if not doc_path and not question:
                continue
            
            # Check if this gate is completed
            if doc_path:
                query = "SELECT response FROM agent_onboarding_responses WHERE agent_id=%s AND path=%s ORDER BY created_ts DESC LIMIT 1"
                results = r_query(conn, query, [agent_id, doc_path])
                if results:
                    response = (results[0].get("response") or "").strip()
                    if response not in {"Viewed document; answer pending", "", None}:
                        continue  # Already completed
            
            if doc_path and not self._has_completed(conn, agent_id, doc_path):
                log(f"Found next gate for agent {agent_id}: {doc_path}")
                trace_out()
                return doc_path, Path(doc_path).name, question
            if not doc_path and question and not self._has_completed(conn, agent_id, doc_path):
                log(f"Found question-only gate for agent {agent_id}")
                trace_out()
                return doc_path, "", question
        
        log(f"No more gates found for agent {agent_id}")
        trace_out()
        return None
    
    def _has_completed(self, conn, agent_id: int, doc_path: str) -> bool:
        """Check if agent has completed a specific document."""
        trace_in()
        query = "SELECT response FROM agent_onboarding_responses WHERE agent_id=%s AND path=%s ORDER BY created_ts DESC LIMIT 1"
        results = r_query(conn, query, [agent_id, doc_path])
        if not results:
            trace_out()
            return False
        response = (results[0].get("response") or "").strip()
        completed = response not in {"Viewed document; answer pending", "", None}
        trace_out()
        return completed
    
    def list_required_docs_for(self, agent_id: int, role: str) -> List[str]:
        """Get list of required documents for agent's role."""
        trace_in()
        matrix = self.build_training_matrix()
        docs = []
        # Always include general first
        for doc_path in matrix["role_docs"].get("general", []):
            docs.append(doc_path)
        # Then include role-specific
        for doc_path in matrix["role_docs"].get(role, []):
            if doc_path not in docs:
                docs.append(doc_path)
        log(f"Required docs for agent {agent_id}, role {role}: {len(docs)} documents")
        trace_out()
        return docs

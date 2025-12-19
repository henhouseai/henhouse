"""
Stage Workflow Management
Windows-compatible script for git-based workflow operations.

This script provides:
- Pull changes from stage  
- Review and apply changes via stage
"""

import subprocess
import sys
import os
import json
import shlex
import fnmatch
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

try:
    import msvcrt
except Exception:
    msvcrt = None  # type: ignore[assignment]

PROJECT_ROOT = Path(__file__).resolve().parent

def run_git(repo_path: str, args: List[str], check: bool = True) -> Tuple[int, str, str]:
    cmd = ["git", "-C", repo_path] + args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    if check and proc.returncode != 0:
        raise RuntimeError(f"git command failed ({proc.returncode}):\n$ {' '.join(shlex.quote(a) for a in cmd)}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    return proc.returncode, out, err
def canonical(p: Path) -> Path:
    return Path(os.path.realpath(p)).resolve()

def under_root(root: Path, target: Path) -> bool:
    try:
        return os.path.commonpath([str(root), str(target)]) == str(root)
    except Exception:
        return False

def test_warden_path(h_root: Path, d_root: Path, path: Path) -> Path:
    p = canonical(path)
    sp = str(p)
    if os.name == 'nt':
        if len(sp) >= 3 and sp[1] == ':' and ':' in sp[3:]:
            raise RuntimeError(f"WARDEN BLOCK: ADS stream: {sp}")
        if sp.startswith('\\\\?\\') or sp.startswith('\\\\.\\'):
            raise RuntimeError(f"WARDEN BLOCK: device/UNC path: {sp}")
    if not (under_root(h_root, p) or under_root(d_root, p)):
        raise RuntimeError(f"WARDEN BLOCK: outside allowed roots: {sp}")
    return p

def ensure_parent_dir(p: Path) -> None:
    parent = p.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

def copy_warden_file(h_root: Path, d_root: Path, src: Path, dst: Path) -> None:
    s = test_warden_path(h_root, d_root, src)
    d = test_warden_path(h_root, d_root, dst)
    ensure_parent_dir(d)
    with s.open('rb') as fsrc, d.open('wb') as fdst:
        while True:
            chunk = fsrc.read(1024 * 1024)
            if not chunk:
                break
            fdst.write(chunk)

def remove_warden_file(h_root: Path, d_root: Path, target: Path) -> None:
    t = test_warden_path(h_root, d_root, target)
    if t.exists():
        t.unlink()


def remove_warden_directory(h_root: Path, d_root: Path, target: Path) -> None:
    t = test_warden_path(h_root, d_root, target)
    if t.exists() and t.is_dir():
        shutil.rmtree(t)

def read_bytes(path: Path) -> bytes | None:
    try:
        with path.open('rb') as f:
            return f.read()
    except Exception:
        return None

def path_matches_any(rel_posix: str, patterns: List[str]) -> bool:
    for g in patterns:
        if fnmatch.fnmatch(rel_posix, g):
            return True
    return False

def list_rel_files(root: Path, deny_globs: List[str]) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    root_c = canonical(root)
    for dirpath, _, filenames in os.walk(root_c):
        for name in filenames:
            full = canonical(Path(dirpath) / name)
            try:
                rel = full.relative_to(root_c)
            except ValueError:
                continue
            rel_posix = rel.as_posix()
            if rel_posix == '.git' or rel_posix.startswith('.git/') or '/.git/' in rel_posix:
                continue
            if rel_posix == 'stage.done':
                continue
            if rel_posix == 'stage':
                continue
            if path_matches_any(rel_posix, deny_globs):
                continue
            out[rel_posix] = full
    return out

def detect_bom(b: bytes | None) -> str:
    if not b or len(b) < 2:
        return 'none'
    if len(b) >= 4:
        if b[0:4] == b"\x00\x00\xFE\xFF":
            return 'utf32be'
        if b[0:4] == b"\xFF\xFE\x00\x00":
            return 'utf32le'
    if b[0:2] == b"\xFE\xFF":
        return 'utf16be'
    if b[0:2] == b"\xFF\xFE":
        return 'utf16le'
    if len(b) >= 3 and b[0:3] == b"\xEF\xBB\xBF":
        return 'utf8-bom'
    return 'none'

def has_crlf(b: bytes | None) -> bool:
    if not b or len(b) < 2:
        return False
    return b.find(b"\r\n") != -1

def normalize_eol_lf_file(path: Path) -> bool:
    try:
        with path.open('rb') as f:
            b = f.read()
        if not b:
            return False
        nb = b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if nb != b:
            with path.open('wb') as f:
                f.write(nb)
            return True
        return False
    except Exception:
        return False

def test_indent_spaces(path: Path, max_lines: int = 500) -> bool:
    try:
        with path.open('r', encoding='utf-8', errors='ignore') as f:
            for _ in range(max_lines):
                line = f.readline()
                if line == '':
                    break
                if line.startswith(' '):
                    return True
    except Exception:
        return False
    return False

def build_warnings(added: List[str], modified: List[str], d_root: Path, warn_indent_exts: List[str]) -> List[str]:
    warnings: List[str] = []
    for rel in added + modified:
        p = (d_root / rel).resolve()
        ext = p.suffix.lower()
        b = read_bytes(p)
        bom = detect_bom(b)
        if bom not in ('none', 'utf8-bom'):
            warnings.append(f"ENCODING: {rel} -- {bom} detected")
        expect_crlf = ext in ('.ps1', '.bat')
        crlf = has_crlf(b)
        if expect_crlf and not crlf:
            warnings.append(f"EOL: {rel} -- expected CRLF")
        if not expect_crlf and crlf:
            warnings.append(f"EOL: {rel} -- expected LF")
        if ext in warn_indent_exts and test_indent_spaces(p):
            warnings.append(f"INDENT: {rel} -- leading spaces detected (tabs-only policy)")
    return warnings

def _read_key_stream() -> str:
    if msvcrt is not None:
        ch = msvcrt.getch()
        if ch in (b'\xe0', b'\x00'):
            _ = msvcrt.getch()
            return ''
        if ch in (b'\r', b'\n'):
            return ''
        try:
            return ch.decode('utf-8', errors='ignore').lower()
        except Exception:
            return ''
    else:
        s = input().strip().lower()
        return s[:1] if s else ''

def interactive_review(h_root: Path, d_root: Path, deleted: List[str], added: List[str], modified: List[str], warnings: List[str], manifest: Optional[Dict] = None) -> Tuple[List[str], List[str], List[str]]:
    accepted: List[str] = []
    skipped: List[str] = []
    warn_done: List[str] = []
    renamed_pairs: List[Tuple[str, str]] = []
    try:
        if manifest and 'renamed' in manifest:
            for pair in manifest.get('renamed', []):
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    renamed_pairs.append((pair[0], pair[1]))
    except Exception:
        renamed_pairs = []
    if renamed_pairs:
        ren_old = {o for (o, _n) in renamed_pairs}
        ren_new = {n for (_o, n) in renamed_pairs}
        deleted = [r for r in deleted if r not in ren_old]
        added = [r for r in added if r not in ren_new]
    categories = ['DELETE','RENAME','ADD','EDIT','WARNINGS']
    items_map: Dict[str, List] = {
        'DELETE': deleted,
        'RENAME': renamed_pairs,
        'ADD': added,
        'EDIT': modified,
        'WARNINGS': warnings,
    }
    status_map: Dict[str, List[str]] = {
        'DELETE': ['n'] * len(deleted),
        'RENAME': ['n'] * len(renamed_pairs),
        'ADD': ['n'] * len(added),
        'EDIT': ['n'] * len(modified),
        'WARNINGS': ['n'] * len(warnings),
    }
    total = sum(len(items_map[k]) for k in categories)
    decided = 0
    cat_idx = 0
    pos_idx = 0

    def build_panel(current_cat: int, current_pos: int) -> List[str]:
        labels: List[str] = []
        for k in categories:
            labels.append(f"{k}: {''.join(status_map[k])}")
        inside = '  '.join(labels)
        top = '+' + '-' * (len(inside) + 2) + '+'
        mid1 = f"| {inside} |"
        start = 0
        for i in range(current_cat):
            start += len(labels[i]) + 2
        prefix_len = len(categories[current_cat]) + 2
        caret_in_inside = start + prefix_len + current_pos
        left_spaces = ' ' * caret_in_inside
        right_spaces = ' ' * max(0, len(inside) - caret_in_inside - 1)
        caret_line = f"| {left_spaces}^{right_spaces} |"
        count_text = f"{decided}/{total} choices made"
        count_line = f"| {count_text}" + ' ' * (len(inside) - len(count_text)) + ' |'
        bottom = '+' + '-' * (len(inside) + 2) + '+'
        return [top, mid1, caret_line, count_line, bottom]

    def next_undecided(start_cat: int, start_pos: int) -> Tuple[int, int] | None:
        for c in range(len(categories)):
            ci = (start_cat + c) % len(categories)
            statuses = status_map[categories[ci]]
            if not statuses:
                continue
            pi_start = start_pos if ci == start_cat else 0
            for p in range(pi_start, len(statuses)):
                if statuses[p] == 'n':
                    return ci, p
        return None

    while decided < total:
        nxt = next_undecided(cat_idx, pos_idx)
        if nxt is None:
            break
        cat_idx, pos_idx = nxt
        cat = categories[cat_idx]
        rel = items_map[cat][pos_idx]
        for line in build_panel(cat_idx, pos_idx):
            print(line, flush=True)
        action = ''
        if cat == 'DELETE':
            action = f'--> delete file "{rel}" ?  [Y/n]'
        elif cat == 'ADD':
            action = f'--> add file "{rel}" ?  [Y/n]'
        elif cat == 'EDIT':
            action = f'--> update file "{rel}" ?  [Y/n]'
        elif cat == 'RENAME':
            oldp, newp = rel  # type: ignore
            action = f'--> rename file "{oldp} -> {newp}" ?  [Y/n]'
        else:
            action = f'--> ack warning "{rel}" ?  [Y/n]'
        print(action, flush=True)
        k = _read_key_stream()
        if k in ('y',):
            status_map[cat][pos_idx] = 'Y'
            decided += 1
            print('', flush=True)
            if cat == 'DELETE':
                remove_warden_file(h_root, d_root, h_root / rel)
                print(f"APPLIED D {rel}", flush=True)
                accepted.append(f"D {rel}")
            elif cat == 'ADD':
                copy_warden_file(h_root, d_root, d_root / rel, h_root / rel)
                print(f"APPLIED A {rel}", flush=True)
                accepted.append(f"A {rel}")
            elif cat == 'EDIT':
                copy_warden_file(h_root, d_root, d_root / rel, h_root / rel)
                print(f"APPLIED M {rel}", flush=True)
                accepted.append(f"M {rel}")
            elif cat == 'RENAME':
                oldp, newp = rel
                remove_warden_file(h_root, d_root, h_root / oldp)
                copy_warden_file(h_root, d_root, d_root / newp, h_root / newp)
                print(f"APPLIED R {oldp} -> {newp}", flush=True)
                accepted.append(f"R {oldp} -> {newp}")
            else:
                if isinstance(rel, str) and rel.startswith('EOL: ') and rel.endswith('expected LF'):
                    try:
                        rel_path = rel[len('EOL: '):].split(' -- ')[0]
                        target = h_root / rel_path
                        changed = normalize_eol_lf_file(target)
                        msg = "FIXED W EOL->LF" if changed else "ACK W (no change)"
                        print(f"{msg} {rel}", flush=True)
                    except Exception:
                        print(f"ACK W {rel}", flush=True)
                else:
                    print(f"ACK W {rel}", flush=True)
                warn_done.append(rel)
            pos_idx += 1
        elif k in ('n',):
            status_map[cat][pos_idx] = 'N'
            decided += 1
            print('', flush=True)
            code = {'DELETE':'D','ADD':'A','EDIT':'M','RENAME':'R','WARNINGS':'W'}[cat]
            print(f"SKIPPED {code} {rel}", flush=True)
            if cat == 'RENAME':
                oldp, newp = rel
                skipped.append(f"R {oldp} -> {newp}")
            else:
                skipped.append(f"{code} {rel}")
            pos_idx += 1
        elif k in ('q',):
            raise KeyboardInterrupt()
        else:
            pos_idx += 1
        print('', flush=True)
    return accepted, skipped, warn_done

def build_summary(branch_label: str, tip_sha: str, accepted: List[str], skipped: List[str], warnings: List[str]) -> str:
    lines: List[str] = []
    lines.append("Branch: " + branch_label)
    lines.append("Tip: " + tip_sha)
    lines.append("Accepted:")
    lines.extend(accepted or ["<none>"])
    lines.append("Skipped:")
    lines.extend(skipped or ["<none>"])
    lines.append("Warnings:")
    lines.extend(warnings or ["<none>"])
    return "\n".join(lines)

def run_command(cmd: str, cwd: Optional[str] = None) -> bool:
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

def run_command_interactive(cmd: str, cwd: Optional[str] = None) -> bool:
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command: {cmd}")
        print(f"Exception: {e}")
        return False

def pull_stage(args: Any) -> bool:
    repo_root = Path(__file__).resolve().parent
    stage_dir = repo_root / 'stage'
    if stage_dir.exists():
        print("🗑️  Removing existing stage before pull...")
        try:
            remove_warden_directory(repo_root, repo_root, stage_dir)
            print("✅ Existing stage removed")
        except Exception as e:
            print(f"❌ Failed to remove existing stage: {e}")
            return False
    print("📥 Fetching remote branches...")
    if not run_command("git fetch origin", cwd=str(repo_root)):
        return False
    result = subprocess.run("git branch -r", shell=True, capture_output=True, text=True, cwd=str(repo_root))
    if result.returncode != 0:
        print("❌ Unable to list remote branches")
        return False
    branches = [b.strip() for b in result.stdout.strip().split('\n') if b.strip()]
    stage_branches = [b for b in branches if 'stage/' in b]
    if not stage_branches:
        print("❌ No stage branches found")
        return False
    target = None
    if hasattr(args, 'search_comment') and args.search_comment:
        print(f"🔍 Searching for stage with comment containing: '{args.search_comment}'")
        for branch in stage_branches:
            stage_content_result = subprocess.run(f"git show {branch}:stage", shell=True, capture_output=True, text=True, cwd=str(repo_root))
            if stage_content_result.returncode == 0:
                stage_comment = stage_content_result.stdout.strip()
                if args.search_comment.lower() in stage_comment.lower():
                    target = branch
                    print(f"✅ Found matching stage branch: {target}")
                    print(f"🎭 Stage signal: '{stage_comment}'")
                    break
        if not target:
            print(f"❌ No stage branch found with comment containing: '{args.search_comment}'")
            print("Available stage branches:")
            for branch in stage_branches:
                stage_content_result = subprocess.run(f"git show {branch}:stage", shell=True, capture_output=True, text=True, cwd=str(repo_root))
                if stage_content_result.returncode == 0:
                    stage_comment = stage_content_result.stdout.strip()
                    print(f"  {branch}: '{stage_comment}'")
            return False
    else:
        stage_branches.sort(reverse=True)
        target = stage_branches[0]
        print(f"✅ Selected stage branch: {target}")
    print("📖 Reading stage signal from branch...")
    stage_content_result = subprocess.run(f"git show {target}:stage", shell=True, capture_output=True, text=True, cwd=str(repo_root))
    if stage_content_result.returncode != 0:
        print("❌ No stage signal found in selected branch")
        return False
    comment = stage_content_result.stdout.strip()
    print(f"🎭 Stage detected: '{comment}'")
    if hasattr(args, 'search_comment') and args.search_comment:
        if args.search_comment.lower() not in comment.lower():
            print(f"❌ Comment mismatch! Expected to contain '{args.search_comment}' but got '{comment}'")
            return False
        print(f"✅ Comment verification passed: '{args.search_comment}' found in stage signal")
    confirm = input("Proceed to pull stage into local stage? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return False
    stage_dir.mkdir(parents=True, exist_ok=True)
    print("📦 Materializing stage into ./stage ...")
    archive_cmd = f"git archive --remote=. {target} | tar -x -C \"{stage_dir}\""
    ok = subprocess.run(archive_cmd, shell=True, cwd=str(repo_root)).returncode == 0
    if not ok:
        tmp_dir = repo_root / '.stage_tmp'
        print("Using worktree fallback...")
        subprocess.run(f"git worktree add \"{tmp_dir}\" {target}", shell=True, cwd=str(repo_root))
        subprocess.run(f"powershell -Command Copy-Item -LiteralPath \"{tmp_dir}\\*\" -Destination \"{stage_dir}\" -Recurse -Force", shell=True)
        subprocess.run(f"git worktree remove \"{tmp_dir}\" --force", shell=True, cwd=str(repo_root))
    try:
        base_sha = subprocess.run(f"git merge-base origin/master {target}", shell=True, capture_output=True, text=True, cwd=str(repo_root))
        base = base_sha.stdout.strip()
        diff = subprocess.run(f"git diff --name-status -M -C {base}..{target}", shell=True, capture_output=True, text=True, cwd=str(repo_root))
        added: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []
        renamed: list[list[str]] = []
        for line in diff.stdout.splitlines():
            t = line.strip()
            if not t:
                continue
            parts = t.split('\t')
            code = parts[0]
            if code == 'A' and len(parts) >= 2:
                added.append(parts[1])
            elif code == 'M' and len(parts) >= 2:
                modified.append(parts[1])
            elif code == 'D' and len(parts) >= 2:
                deleted.append(parts[1])
            elif code.startswith('R') and len(parts) >= 3:
                renamed.append([parts[1], parts[2]])
        manifest = {
            "base": base,
            "target": target,
            "added": added,
            "modified": modified,
            "deleted": deleted,
            "renamed": renamed,
        }
        (stage_dir / '.stage_changes.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    except Exception as e:
        print(f"⚠️  Warning: Could not build change manifest: {e}")
    try:
        stage_local = stage_dir / 'stage'
        if stage_local.exists():
            stage_local.unlink()
    except Exception:
        pass
    print("✅ Stage materialized into ./stage")
    print("📋 Next step: Run 'python stage.py push' to review changes")
    return True

def push_stage(args: Any) -> bool:
    print("🎭 Running stage manager (interactive mode)...")
    repo_root = Path(__file__).resolve().parent
    stage_dir = repo_root / 'stage'
    if not stage_dir.exists():
        print("📥 No local stage found. Pulling latest stage first...")
        pulled = pull_stage(args)
        if not pulled:
            return False
    try:
        h_root = canonical(repo_root)
        s_root = canonical(stage_dir)
        deny_globs = ["**/build/**", "**/.git/**", "**/.vs/**", "**/.vscode/**", "**/__pycache__/**", "**/*.pyc"]
        warn_indent_exts = [".cpp", ".h", ".hpp", ".c", ".ino"]
        manifest_path = Path(s_root) / '.stage_changes.json'
        manifest = None
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            except Exception:
                manifest = None
        s_files = list_rel_files(s_root, deny_globs)
        h_files = list_rel_files(h_root, deny_globs)
        all_rels = set(s_files.keys()) | set(h_files.keys())
        deleted: List[str] = []
        added: List[str] = []
        modified: List[str] = []
        candidate_rels = sorted(all_rels)
        if manifest and all(k in manifest for k in ('added','modified','deleted','renamed')):
            m_set = set(manifest.get('added', []) + manifest.get('modified', []) + manifest.get('deleted', []) + [r[1] for r in manifest.get('renamed', [])])
            candidate_rels = sorted([r for r in candidate_rels if r in m_set])
        for rel in candidate_rels:
            in_s = rel in s_files
            in_h = rel in h_files
            if not in_s and in_h:
                deleted.append(rel)
            elif in_s and not in_h:
                added.append(rel)
            elif in_s and in_h:
                sb = read_bytes(s_files[rel])
                hb = read_bytes(h_files[rel])
                if sb is None or hb is None:
                    continue
                if len(sb) != len(hb) or sb != hb:
                    modified.append(rel)
        warnings = build_warnings(added, modified, s_root, warn_indent_exts)
        try:
            accepted, skipped, warn_done = interactive_review(h_root, s_root, deleted, added, modified, warnings, manifest)
        except KeyboardInterrupt:
            print("\nSession interrupted. Partial decisions preserved in summary.")
            accepted, skipped, warn_done = [], [], []
        summary_text = build_summary("local-stage", "gitless", accepted, skipped, warn_done)
        print("\n---- Review Summary ----")
        print(summary_text)
        print("------------------------")
        print("Session complete.")
        success = True
    except Exception as e:
        print(f"❌ Error during stage review: {e}")
        success = False
    print("🧹 Cleaning up temporary stage directory...")
    try:
        remove_warden_directory(repo_root, repo_root, stage_dir)
        print("✅ Temporary stage directory removed")
    except Exception as e:
        print(f"⚠️  Warning: Could not remove temporary stage directory: {e}")
        print(f"   You may need to manually remove: {stage_dir}")
    return success

def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
🏠 Henhouse - Stage Workflow Management
Windows-compatible script for git-based workflow operations.

Available commands:
  pull      Pull latest changes from stage
  find      Find and pull stage with specific comment
  push      Review and apply changes via stage

Examples:
  python stage.py pull
  python stage.py find "about to redo"
  python stage.py push

""")
        return
    if len(sys.argv) < 2:
        print("Run 'python stage.py --help' for available commands")
        return
    command = sys.argv[1]
    command_args = sys.argv[2:] if len(sys.argv) > 2 else []
    if command == 'pull':
        class PullStageArgs:
            def __init__(self):
                self.search_comment = None
        success = pull_stage(PullStageArgs())
    elif command == 'find':
        class FindStageArgs:
            def __init__(self):
                self.search_comment = command_args[0] if command_args else None
        success = pull_stage(FindStageArgs())
    elif command == 'push':
        class PushStageArgs:
            def __init__(self):
                pass
        success = push_stage(PushStageArgs())
    else:
        print(f"❌ Unknown command: {command}")
        print("Run 'python stage.py --help' for available commands")
        success = False
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

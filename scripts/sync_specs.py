#!/usr/bin/env python3
"""Sync vendored specs/ from strongdm/attractor at a pinned git ref.

This repository vendors a small set of markdown specification files from the
upstream Attractor project. We keep the files in-tree for benchmark stability,
but record the upstream commit so changes are auditable and reproducible.

Usage:
  python3 scripts/sync_specs.py              # sync to pinned ref in specs/UPSTREAM.json
  python3 scripts/sync_specs.py --latest     # sync to latest upstream main
  python3 scripts/sync_specs.py --ref <sha>  # sync to an explicit ref (sha/tag/branch)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = REPO_ROOT / "specs"
MANIFEST_PATH = SPECS_DIR / "UPSTREAM.json"

DEFAULT_UPSTREAM_REPO = "https://github.com/strongdm/attractor.git"
DEFAULT_BRANCH = "main"
DEFAULT_MAPPINGS = [
    # Upstream paths (repo root) -> local vendored paths (specs/)
    {"source_path": "unified-llm-spec.md", "dest_path": "specs/unified-llm-spec.md"},
    {"source_path": "coding-agent-loop-spec.md", "dest_path": "specs/coding-agent-loop-spec.md"},
    {"source_path": "attractor-spec.md", "dest_path": "specs/attractor-spec.md"},
]


def _run(cmd: list[str], *, cwd: Path | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        loc = f" (cwd={cwd})" if cwd else ""
        raise RuntimeError(
            f"Command failed{loc}:\n"
            f"  {' '.join(cmd)}\n\n"
            f"stdout:\n{proc.stdout}\n\n"
            f"stderr:\n{proc.stderr}\n"
        )
    return proc.stdout.strip()


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {
            "upstream_repo": DEFAULT_UPSTREAM_REPO,
            "requested_ref": DEFAULT_BRANCH,
            "ref": "",
            "synced_at": "",
            "mappings": DEFAULT_MAPPINGS,
        }
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _write_manifest(manifest: dict) -> None:
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Sync vendored specs/ from strongdm/attractor.")
    parser.add_argument("--repo", default=None, help=f"Upstream git repo (default: {DEFAULT_UPSTREAM_REPO})")
    parser.add_argument("--ref", default=None, help="Git ref (sha/tag/branch) to sync")
    parser.add_argument(
        "--latest",
        action="store_true",
        help=f"Sync to latest upstream {DEFAULT_BRANCH} (overrides manifest pin)",
    )
    args = parser.parse_args(argv)

    manifest = _load_manifest()
    upstream_repo = args.repo or manifest.get("upstream_repo") or DEFAULT_UPSTREAM_REPO

    if args.ref:
        requested_ref = args.ref
    elif args.latest:
        requested_ref = DEFAULT_BRANCH
    else:
        requested_ref = manifest.get("ref") or manifest.get("requested_ref") or DEFAULT_BRANCH

    mappings = manifest.get("mappings") or DEFAULT_MAPPINGS
    if not isinstance(mappings, list) or not mappings:
        raise RuntimeError(f"Invalid or empty mappings in {MANIFEST_PATH}")

    with tempfile.TemporaryDirectory(prefix="attractorbench-sync-specs-") as td:
        tmp = Path(td)
        _run(["git", "clone", upstream_repo, str(tmp)])
        _run(["git", "checkout", requested_ref], cwd=tmp)
        resolved_ref = _run(["git", "rev-parse", "HEAD"], cwd=tmp)

        changed = False
        for m in mappings:
            src_rel = m.get("source_path")
            dst_rel = m.get("dest_path")
            if not src_rel or not dst_rel:
                raise RuntimeError(f"Invalid mapping in {MANIFEST_PATH}: {m}")

            src = tmp / src_rel
            dst = REPO_ROOT / dst_rel
            if not src.is_file():
                raise RuntimeError(f"Upstream file not found at {src_rel} (ref={resolved_ref})")

            dst.parent.mkdir(parents=True, exist_ok=True)
            src_bytes = src.read_bytes()
            if dst.is_file() and dst.read_bytes() == src_bytes:
                continue
            dst.write_bytes(src_bytes)
            changed = True

    # Only write a new manifest if the commit pin changed or any file changed.
    if str(manifest.get("ref") or "") != resolved_ref:
        changed = True

    if not changed and MANIFEST_PATH.exists():
        print(f"Specs already up to date at {resolved_ref}")
        return 0

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest_out = {
        "upstream_repo": upstream_repo,
        "requested_ref": requested_ref,
        # The resolved commit pin we actually vendored.
        "ref": resolved_ref,
        "synced_at": now,
        "mappings": mappings,
    }
    _write_manifest(manifest_out)

    print(f"Synced specs/ from {upstream_repo} at {resolved_ref}")
    print(f"Wrote manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

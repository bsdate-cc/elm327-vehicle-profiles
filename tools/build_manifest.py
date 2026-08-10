#!/usr/bin/env python3
"""Generate (or verify) manifest.json — the index the app fetches first.

The manifest exists so a client can answer "did anything change?" and "is what I
downloaded intact?" without downloading every profile. Both answers are derived
from file content, never hand-maintained: the drift this repository was created
to end came from a human being expected to keep two copies in step.

Usage:
    build_manifest.py            rewrite manifest.json
    build_manifest.py --check    exit non-zero if manifest.json is stale
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARS = ROOT / "cars"
MANIFEST = ROOT / "manifest.json"

# Bumped when the manifest's own shape changes. A client that does not know this
# version must refuse the manifest rather than guess at missing fields.
MANIFEST_VERSION = 1

FILE_ROLES = {"default.json": "base", "extensions.json": "extensions"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_metadata(car_dir: Path) -> dict:
    """Per-car metadata. Absent fields fall back to the directory name."""
    meta_path = car_dir / "profile.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta.setdefault("id", car_dir.name.lower())
    meta.setdefault("label", car_dir.name.replace("-", " "))
    # The lowest app schema that can parse this profile. Raise it when a profile
    # starts using a feature older apps cannot understand; they must then say so
    # instead of half-parsing it.
    meta.setdefault("minAppSchema", 1)
    return meta


def collect_profile(car_dir: Path) -> dict | None:
    signalsets = sorted(car_dir.glob("signalsets/v*"))
    if not signalsets:
        return None
    version_dir = signalsets[-1]

    files = []
    for name, role in FILE_ROLES.items():
        path = version_dir / name
        if not path.exists():
            continue
        # Parsed here so a syntax error is caught at publish time rather than by
        # a phone in a garage with no connectivity.
        json.loads(path.read_text(encoding="utf-8"))
        files.append(
            {
                "role": role,
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    if not files:
        return None

    meta = load_metadata(car_dir)
    # Changes iff content changes, so the client needs no author discipline to
    # detect an update.
    revision = hashlib.sha256("".join(f["sha256"] for f in files).encode()).hexdigest()[:12]
    return {
        "id": meta["id"],
        "label": meta["label"],
        "signalsetVersion": version_dir.name,
        "minAppSchema": meta["minAppSchema"],
        "revision": revision,
        "files": files,
    }


def build() -> dict:
    profiles = [p for d in sorted(CARS.iterdir()) if d.is_dir() and (p := collect_profile(d))]
    return {"manifestVersion": MANIFEST_VERSION, "profiles": profiles}


def main() -> int:
    fresh = build()
    if "--check" in sys.argv:
        if not MANIFEST.exists():
            print("manifest.json is missing; run tools/build_manifest.py", file=sys.stderr)
            return 1
        current = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if current != fresh:
            print("manifest.json is stale; run tools/build_manifest.py", file=sys.stderr)
            return 1
        print(f"manifest.json is current ({len(fresh['profiles'])} profiles)")
        return 0

    MANIFEST.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    print(f"wrote manifest.json ({len(fresh['profiles'])} profiles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

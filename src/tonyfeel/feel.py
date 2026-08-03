"""Feel pack load / validate."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

def _repo_root() -> Path:
    """Find project root that contains packs/ (repo layout or Space checkout)."""
    here = Path(__file__).resolve()
    for c in (
        here.parent / "packs",  # bundled beside module
        here.parents[2] / "packs",  # src/tonyfeel → repo root
        Path.cwd() / "packs",
    ):
        if c.is_dir():
            return c.parent
    return here.parents[2]


_ROOT = _repo_root()
PACKS_DIR = _ROOT / "packs"
DEMO_DIR = _ROOT / "demo"


def pack_path(name: str | Path) -> Path:
    """Resolve a pack name ('tony_bollas_mad') or filesystem path to a JSON file."""
    p = Path(name)
    if p.suffix == ".json" and p.exists():
        return p.resolve()
    candidate = PACKS_DIR / f"{p.stem}.json"
    if candidate.exists():
        return candidate
    # bare filename in packs/
    candidate2 = PACKS_DIR / p.name
    if candidate2.exists():
        return candidate2
    raise FileNotFoundError(f"feel pack not found: {name} (looked in {PACKS_DIR})")


def list_packs() -> list[str]:
    """Pack names; canon demo pack first."""
    if not PACKS_DIR.is_dir():
        return []
    names = sorted(p.stem for p in PACKS_DIR.glob("*.json"))
    prefer = "tony_bollas_mad_4bar"
    if prefer in names:
        names.remove(prefer)
        names.insert(0, prefer)
    return names


def load_feel(path: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load feel JSON. Returns (retimer, full_profile).

    If path is None, prefers tony_bollas_mad_4bar (demo canon).
    """
    if path is None:
        packs = list_packs()
        if "tony_bollas_mad_4bar" in packs:
            path = pack_path("tony_bollas_mad_4bar")
        elif packs:
            path = pack_path(packs[0])
        else:
            raise FileNotFoundError(f"no feel packs in {PACKS_DIR}")
    else:
        path = pack_path(path)

    data = json.loads(Path(path).read_text())
    if "retimer" not in data:
        raise ValueError(f"{path} missing 'retimer' block")
    return data["retimer"], data

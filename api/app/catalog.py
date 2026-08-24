"""Load versioned YAML catalogs of ISO 42001 controls and EU AI Act obligations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.models import Control, Obligation

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.name}: invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name}: top-level document must be a mapping")
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{path.name}: 'entries' must be a non-empty list")
    return entries


def _require(entry: dict[str, Any], field: str, filename: str) -> Any:
    if field not in entry or entry[field] is None:
        raise ValueError(f"{filename}: entry {entry.get('id', '?')!r} missing field {field!r}")
    return entry[field]


def load_controls(data_dir: Path | str = DEFAULT_DATA_DIR, filename: str = "controls_iso42001.yaml") -> list[Control]:
    """Parse the ISO 42001 control catalog strictly against the Control model."""
    path = Path(data_dir) / filename
    entries = _load_yaml(path)
    controls: list[Control] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{path.name}: each entry must be a mapping")
        try:
            controls.append(
                Control(
                    id=str(_require(entry, "id", path.name)),
                    name=str(_require(entry, "name", path.name)),
                    description=str(_require(entry, "description", path.name)),
                    evidence_types=list(_require(entry, "evidence_types", path.name)),
                )
            )
        except ValueError as exc:  # pydantic validation errors carry context already
            raise ValueError(f"{path.name}: {exc}") from exc
    ids = [c.id for c in controls]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"{path.name}: duplicate control ids: {dupes}")
    return controls


def load_obligations(
    data_dir: Path | str = DEFAULT_DATA_DIR, filename: str = "obligations_eu_ai_act.yaml"
) -> list[Obligation]:
    """Parse the EU AI Act obligation catalog strictly against the Obligation model."""
    path = Path(data_dir) / filename
    entries = _load_yaml(path)
    obligations: list[Obligation] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{path.name}: each entry must be a mapping")
        try:
            article = _require(entry, "article", path.name)
            obligations.append(
                Obligation(
                    id=str(_require(entry, "id", path.name)),
                    article=int(article),
                    title=str(_require(entry, "title", path.name)),
                    description=str(_require(entry, "description", path.name)),
                    control_ids=[str(c) for c in _require(entry, "control_ids", path.name)],
                    source_url=str(_require(entry, "source_url", path.name)),
                )
            )
        except ValueError as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
    return obligations

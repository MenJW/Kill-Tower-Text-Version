from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import orjson
from pydantic import BaseModel, TypeAdapter

from kill_tower.app.config import get_config
from kill_tower.data.schemas import SnapshotManifest

ModelT = TypeVar("ModelT", bound=BaseModel)


def load_json(path: Path) -> Any:
    return orjson.loads(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))


def load_model(path: Path, model_type: type[ModelT]) -> ModelT:
    return model_type.model_validate(load_json(path))


def load_collection(path: Path, model_type: type[ModelT]) -> list[ModelT]:
    adapter = TypeAdapter(list[model_type])
    return adapter.validate_python(load_json(path))


def resolve_snapshot_dir(snapshot_tag: str) -> Path:
    config = get_config()
    return config.paths.snapshots_dir / snapshot_tag


def load_manifest(snapshot_tag: str) -> SnapshotManifest:
    manifest_path = resolve_snapshot_dir(snapshot_tag) / "manifest.json"
    return load_model(manifest_path, SnapshotManifest)
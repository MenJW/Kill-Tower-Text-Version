from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


class PathConfig(BaseModel):
    root: Path
    docs_dir: Path
    data_dir: Path
    raw_data_dir: Path
    normalized_data_dir: Path
    reports_dir: Path
    snapshots_dir: Path
    saves_dir: Path


class RuntimeConfig(BaseModel):
    project_name: str = "Kill Tower Text Version"
    default_language: str = "zhs"
    fallback_language: str = "eng"
    default_snapshot_tag: str | None = None
    spire_codex_api_base: str = "https://spire-codex.com"
    kotone_reference_url: str = "https://kotoneworkshop.com/sts2-builds"


class AppConfig(BaseModel):
    paths: PathConfig
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

    @classmethod
    def from_root(cls, root: Path | None = None) -> "AppConfig":
        project_root = root or _project_root()
        data_dir = project_root / "data"
        return cls(
            paths=PathConfig(
                root=project_root,
                docs_dir=project_root / "docs",
                data_dir=data_dir,
                raw_data_dir=data_dir / "raw",
                normalized_data_dir=data_dir / "normalized",
                reports_dir=data_dir / "reports",
                snapshots_dir=data_dir / "snapshots",
                saves_dir=project_root / "saves",
            )
        )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig.from_root()
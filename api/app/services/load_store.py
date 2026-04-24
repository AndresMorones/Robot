"""In-memory load store backed by a JSON file with mtime-based reload."""

import json
from pathlib import Path

import structlog

from app.models import Load, LoadSearchRequest

log = structlog.get_logger()


class LoadStore:
    def __init__(self) -> None:
        self._loads: list[Load] = []
        self._path: Path | None = None
        self._mtime: float = 0.0

    def load(self, path: str) -> None:
        """Load from JSON file. Idempotent unless file mtime changed."""
        p = Path(path)
        mtime = p.stat().st_mtime
        if p == self._path and mtime == self._mtime:
            return
        with p.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        self._loads = [Load.model_validate(item) for item in raw]
        self._path = p
        self._mtime = mtime
        log.info("load_store.loaded", count=len(self._loads), path=str(p))

    def reload_if_changed(self) -> None:
        if self._path is None:
            return
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            return
        if mtime != self._mtime:
            self.load(str(self._path))

    def all(self) -> list[Load]:
        return list(self._loads)

    def search(self, req: LoadSearchRequest) -> list[Load]:
        self.reload_if_changed()
        results: list[Load] = []
        for load in self._loads:
            if req.origin_state and load.origin_state.upper() != req.origin_state.upper():
                continue
            if (
                req.destination_state
                and load.destination_state.upper() != req.destination_state.upper()
            ):
                continue
            if req.equipment_type and load.equipment_type != req.equipment_type:
                continue
            if req.pickup_after and load.pickup_datetime < req.pickup_after:
                continue
            results.append(load)
            if len(results) >= req.max_results:
                break
        return results


# Module-level singleton; FastAPI lifespan loads it on startup.
load_store = LoadStore()

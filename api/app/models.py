"""Pydantic request/response models.

Single file for now per CLAUDE.md (split per-domain when count grows past ~10).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EquipmentType = Literal["DRY_VAN", "REEFER", "FLATBED", "POWER_ONLY"]


class Load(BaseModel):
    """A freight load matching the take-home spec.

    `loadboard_rate` is the ceiling we charge the shipper — the only rate exposed
    to HR / carrier. Floor + target live in `data/load-policies.json` (added in WS2c).
    """

    load_id: str
    origin: str
    destination: str
    origin_state: str  # 2-letter; used for filtering
    destination_state: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: EquipmentType
    loadboard_rate: int  # USD
    notes: str | None = None
    weight: int  # lbs
    commodity_type: str
    num_of_pieces: int
    miles: int
    dimensions: str  # e.g. "53x8x9 ft"


class LoadSearchRequest(BaseModel):
    origin_state: str | None = None
    destination_state: str | None = None
    equipment_type: EquipmentType | None = None
    pickup_after: datetime | None = None
    max_results: int = Field(default=3, ge=1, le=10)


class LoadSearchResponse(BaseModel):
    matches: list[Load]
    total_in_store: int

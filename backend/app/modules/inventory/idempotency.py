"""Stable request identity; SQL uniqueness remains the concurrency authority."""

import hashlib
import json
from uuid import UUID

from app.modules.inventory.schemas import MovementCreate


def request_fingerprint(payload: MovementCreate, actor_id: UUID) -> str:
    data = payload.model_dump(mode="json")
    data["quantity"] = f"{payload.quantity:.3f}"
    data["actor_id"] = str(actor_id)
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

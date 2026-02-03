from __future__ import annotations

import json
from typing import Any, Dict, Type, Union

from pydantic import ValidationError

from .events import (
    EventType,
    OrderCreatedEvent,
    OrderStatusUpdatedEvent,
    OrderEvent,
)

_EVENT_MODEL_BY_TYPE: Dict[str, Type[Any]] = {
    EventType.ORDER_CREATED.value: OrderCreatedEvent,
    EventType.ORDER_STATUS_UPDATED.value: OrderStatusUpdatedEvent,
}


def serialize_event(event: OrderEvent) -> bytes:
    """
    Converts an OrderEvent (Pydantic model) to bytes (JSON-encoded) for Kafka value.
    """
    return event.model_dump_json().encode("utf-8")


def deserialize_event(raw: Union[bytes, bytearray, memoryview]) -> OrderEvent:
    """
    Converts bytes (Kafka value) into a typed OrderEvent.
    Uses event_type as a discriminator.
    """
    try:
        payload = bytes(raw).decode("utf-8")
        data = json.loads(payload)
    except Exception as e:
        raise ValueError(f"Invalid JSON event payload: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object (dict), got: {type(data).__name__}")

    et = data.get("event_type")
    if et is None:
        raise ValueError("Missing 'event_type' in event payload")

    et_str = et.value if hasattr(et, "value") else str(et)

    model_cls = _EVENT_MODEL_BY_TYPE.get(et_str)
    if model_cls is None:
        raise ValueError(f"Unknown event_type: {et_str}")

    try:
        return model_cls.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Event validation failed for type={et_str}: {e}") from e

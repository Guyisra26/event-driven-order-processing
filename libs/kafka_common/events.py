from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from .models import Order, OrderStatus


class EventType(str, Enum):
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_STATUS_UPDATED = "ORDER_STATUS_UPDATED"


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    order_id: str


class OrderCreatedEvent(BaseEvent):
    event_type: Literal[EventType.ORDER_CREATED] = EventType.ORDER_CREATED
    order: Order


class OrderStatusUpdatedEvent(BaseEvent):
    event_type: Literal[EventType.ORDER_STATUS_UPDATED] = EventType.ORDER_STATUS_UPDATED
    status: OrderStatus


OrderEvent = Union[OrderCreatedEvent, OrderStatusUpdatedEvent]

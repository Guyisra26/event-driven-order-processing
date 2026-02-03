from __future__ import annotations
from typing import Dict

from libs.kafka_common.events import OrderCreatedEvent, OrderStatusUpdatedEvent, OrderEvent
from libs.kafka_common.models import OrderStatus
from .consumer_db import OrderDB
from .models import OrderEntry


class OrderAlreadyExists(Exception):
    pass


class OrderNotFound(Exception):
    pass

class OrderEventHandler:
    def __init__(self, db: OrderDB) -> None:
        self.db = db
        self._pending_status: Dict[str, OrderStatus] = {}

    def handle(self, event: OrderEvent, topic: str) -> None:
        self.db.track_received_id(topic, event.order_id)


        if isinstance(event, OrderCreatedEvent):
            self._handle_created(event)
        elif isinstance(event, OrderStatusUpdatedEvent):
            self._handle_status_updated(event)

    def _handle_created(self, event: OrderCreatedEvent) -> None:
        order = event.order
        if self.db.get(order.order_id) is not None:
            return
        pending = self._pending_status.pop(order.order_id, None)
        if pending is not None:
            order.status = pending

        shipping_cost = self.calculate_shipping_cost(order.total_amount)
        entry = OrderEntry(order=order, shipping_cost=shipping_cost)
        self.db.add_order(entry)

    def _handle_status_updated(self, event: OrderStatusUpdatedEvent) -> None:
        entry = self.db.get(event.order_id)
        if entry is None:
            self._pending_status[event.order_id] = event.status
            return

        if entry.order.status == event.status:
            return

        self.db.update_status(event.order_id, event.status)


    @staticmethod
    def calculate_shipping_cost(amount: float) -> float:
        return round(amount * 0.02, 2) # type: ignore
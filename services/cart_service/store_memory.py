from __future__ import annotations
from typing import Dict, Optional

from libs.kafka_common.models import Order

class OrderStoreMemory:
    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}

    def add(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def get(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def exists(self, order_id: str) -> bool:
        return order_id in self._orders

    def update(self, order: Order) -> None:
        self._orders[order.order_id] = order

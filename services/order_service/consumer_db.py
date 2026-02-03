# services/order_service/consumer_db.py
from __future__ import annotations

from typing import Dict, List, Optional, Set, DefaultDict
from collections import defaultdict

from libs.kafka_common.models import OrderStatus
from .models import OrderEntry


class OrderDB:
    def __init__(self) -> None:
        self._orders: Dict[str, OrderEntry] = {}
        self._received_ids_by_topic: DefaultDict[str, List[str]] = defaultdict(list)


    def add_order(self, order_entry: OrderEntry):
        self._orders[order_entry.order.order_id] = order_entry

    def get(self, order_id: str) -> Optional[OrderEntry]:
        return self._orders.get(order_id)

    def update_status(self, order_id: str , status: OrderStatus) -> bool:
        entry = self._orders.get(order_id)
        if entry is None:
            return False
        entry.order.status = status
        self._orders[order_id] = entry
        return True

    def track_received_id(self, topic: str, order_id: str) -> None:
        self._received_ids_by_topic[topic].append(order_id)

    def get_all_ids_for_topic(self, topic: str) -> List[str]:
        return list(self._received_ids_by_topic.get(topic, []))



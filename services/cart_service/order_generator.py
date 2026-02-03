from __future__ import annotations

from datetime import datetime
from typing import Dict, List
import random

from libs.kafka_common.models import Order, OrderItem, Currency, OrderStatus
from services.cart_service.store_memory import OrderStoreMemory


class OrderAlreadyExists(ValueError):
    pass

class OrderNotFound(ValueError):
    pass



class OrderGenerator:
    def __init__(self, publisher, store: OrderStoreMemory) -> None:
        self.publisher = publisher
        self.store = store

    @staticmethod
    def _normalize_order_id(order_id: str) -> str:
        return f"ORD-{order_id}" if order_id.isdigit() else order_id

    def create_order(self, order_id: str, num_of_items: int) -> str:
        order_id = self._normalize_order_id(order_id)
        if self.store.exists(order_id):
            raise OrderAlreadyExists(f"Order {order_id} already exists.")

        customer_id = f"CUST-{random.randint(1, 99999):05d}"
        order_date = datetime.now()
        items: List[OrderItem] = []
        total_amount = 0.0
        currency = random.choice(list(Currency)).value
        status = OrderStatus.NEW

        for _ in range(num_of_items): # type: ignore[arg-type]
            item_id = f"ITEM-{random.randint(1, 999):03d}"
            quantity = random.randint(1, 10)
            price = round(random.uniform(10.0, 100.0), 2)
            item = OrderItem(item_id=item_id, quantity=quantity, price=price)
            items.append(item)
            total_amount += round(quantity * price, 2)

        order = Order(order_id=order_id, customer_id=customer_id, order_date=order_date, items=items,
                      total_amount=total_amount, currency=currency, status=status)

        self.store.add(order)
        self.publisher.publish_order_created(order)
        return order_id

    def update_order_status(self, order_id: str, new_status: OrderStatus) -> None:
        order_id = self._normalize_order_id(order_id)
        order = self.store.get(order_id)
        if order is None:
            raise OrderNotFound(f"Order {order_id} not found.")
        order.status = new_status
        self.store.update(order)
        self.publisher.publish_order_status_updated(order_id, new_status)


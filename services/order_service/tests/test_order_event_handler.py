from datetime import datetime, timezone

from services.order_service.consumer_db import OrderDB
from services.order_service.order_event_handler import OrderEventHandler
from services.order_service.models import OrderEntry

from libs.kafka_common.models import Order, OrderItem, Currency, OrderStatus
from libs.kafka_common.events import OrderCreatedEvent, OrderStatusUpdatedEvent


def make_order(order_id="ORD-1", total=100.0, status=OrderStatus.NEW):
    return Order(
        order_id=order_id,
        customer_id="CUST-0001",
        order_date=datetime.now(timezone.utc),
        items=[OrderItem(item_id="ITEM-001", quantity=1, price=total)],
        total_amount=total,
        currency=Currency.USD,
        status=status,
    )


def test_created_stores_order_and_shipping():
    db = OrderDB()
    h = OrderEventHandler(db)

    order = make_order(order_id="ORD-10", total=100.0)
    ev = OrderCreatedEvent(order_id=order.order_id, order=order)

    h.handle(ev, topic="orders.events")

    entry = db.get("ORD-10")
    assert entry is not None
    assert entry.shipping_cost == 2.0  # 2% of 100
    assert entry.order.order_id == "ORD-10"
    assert db.get_all_ids_for_topic("orders.events") == ["ORD-10"]


def test_status_update_after_created_updates_status():
    db = OrderDB()
    h = OrderEventHandler(db)

    order = make_order(order_id="ORD-20", total=50.0, status=OrderStatus.NEW)
    h.handle(OrderCreatedEvent(order_id=order.order_id, order=order), topic="orders.events")

    h.handle(OrderStatusUpdatedEvent(order_id="ORD-20", status=OrderStatus.SHIPPED), topic="orders.events")

    entry = db.get("ORD-20")
    assert entry is not None
    assert entry.order.status == OrderStatus.SHIPPED
    # tracking list contains both arrivals (created + update)
    assert db.get_all_ids_for_topic("orders.events") == ["ORD-20", "ORD-20"]


def test_status_update_before_created_is_applied_on_create():
    db = OrderDB()
    h = OrderEventHandler(db)

    h.handle(OrderStatusUpdatedEvent(order_id="ORD-30", status=OrderStatus.CONFIRMED), topic="orders.events")

    order = make_order(order_id="ORD-30", total=10.0, status=OrderStatus.NEW)
    h.handle(OrderCreatedEvent(order_id=order.order_id, order=order), topic="orders.events")

    entry = db.get("ORD-30")
    assert entry is not None
    assert entry.order.status == OrderStatus.CONFIRMED
    assert db.get_all_ids_for_topic("orders.events") == ["ORD-30", "ORD-30"]


def test_duplicate_created_is_ignored_but_tracking_keeps_arrivals():
    db = OrderDB()
    h = OrderEventHandler(db)

    order = make_order(order_id="ORD-40", total=100.0)
    ev = OrderCreatedEvent(order_id=order.order_id, order=order)

    h.handle(ev, topic="orders.events")
    h.handle(ev, topic="orders.events")  # duplicate

    entry = db.get("ORD-40")
    assert entry is not None
    assert entry.shipping_cost == 2.0

    # business state doesn't duplicate; tracking list does (because we track arrivals)
    assert db.get_all_ids_for_topic("orders.events") == ["ORD-40", "ORD-40"]

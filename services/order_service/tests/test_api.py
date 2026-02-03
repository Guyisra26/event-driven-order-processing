from fastapi.testclient import TestClient

from services.order_service.app.main import app
from services.order_service.consumer_db import OrderDB
from services.order_service.app.api.routes import get_db

from libs.kafka_common.models import Order, OrderItem, Currency, OrderStatus
from services.order_service.models import OrderEntry
from datetime import datetime, timezone


def make_entry(order_id="ORD-1"):
    order = Order(
        order_id=order_id,
        customer_id="CUST-1",
        order_date=datetime.now(timezone.utc),
        items=[OrderItem(item_id="ITEM-1", quantity=1, price=100.0)],
        total_amount=100.0,
        currency=Currency.USD,
        status=OrderStatus.NEW,
    )
    return OrderEntry(order=order, shipping_cost=2.0)


def test_order_details_404_when_missing():
    db = OrderDB()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    r = client.get("/order-details", params={"orderId": "ORD-999"})
    assert r.status_code == 404


def test_order_details_success():
    db = OrderDB()
    db.add_order(make_entry("ORD-7"))
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    r = client.get("/order-details", params={"orderId": "ORD-7"})
    assert r.status_code == 200
    body = r.json()
    assert body["order"]["orderId"] == "ORD-7"
    assert body["shippingCost"] == 2.0


def test_get_all_order_ids_from_topic():
    db = OrderDB()
    db.track_received_id("orders.events", "ORD-1")
    db.track_received_id("orders.events", "ORD-1")
    db.track_received_id("orders.events", "ORD-2")

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    r = client.get("/getAllOrderIdsFromTopic", params={"topicName": "orders.events"})
    assert r.status_code == 200
    assert r.json()["orderIds"] == ["ORD-1", "ORD-1", "ORD-2"]


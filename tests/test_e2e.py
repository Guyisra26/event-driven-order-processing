"""
End-to-End tests - requires running services:
1. Kafka (docker-compose.dev.yml)
2. Cart service on port 8000
3. Order service on port 8001

Run with: PYTHONPATH=. pytest tests/test_e2e.py -v -s
"""
import time
import requests
import pytest

CART_SERVICE_URL = "http://localhost:8000"
ORDER_SERVICE_URL = "http://localhost:8001"


def wait_for_consumer(timeout: float = 3.0, poll_interval: float = 0.3):
    """Wait for consumer to process messages."""
    time.sleep(timeout)


@pytest.fixture
def unique_order_id():
    """Generate unique order ID for each test."""
    return str(int(time.time() * 1000))


class TestE2EOrderFlow:
    """End-to-end tests for the full order flow."""

    def test_create_order_and_get_details(self, unique_order_id):
        """Test: Create order → Kafka → Consumer → Get details."""
        # 1. Create order via cart service
        response = requests.post(
            f"{CART_SERVICE_URL}/create-order",
            json={"orderId": unique_order_id, "numberOfItems": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["orderId"] == f"ORD-{unique_order_id}"
        print(f"\n✅ Order created: {data['orderId']}")

        # 2. Wait for consumer to process
        wait_for_consumer()

        # 3. Get order details from order service
        response = requests.get(
            f"{ORDER_SERVICE_URL}/order-details",
            params={"orderId": unique_order_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["order"]["orderId"] == f"ORD-{unique_order_id}"
        assert data["shippingCost"] > 0
        print(f"✅ Order received by consumer: {data['order']['orderId']}")
        print(f"   Shipping cost: {data['shippingCost']}")

    def test_create_and_update_order_status(self, unique_order_id):
        """Test: Create order → Update status → Verify status changed."""
        # 1. Create order
        response = requests.post(
            f"{CART_SERVICE_URL}/create-order",
            json={"orderId": unique_order_id, "numberOfItems": 1}
        )
        assert response.status_code == 200
        print(f"\n✅ Order created: ORD-{unique_order_id}")

        # 2. Update status to 'confirmed'
        response = requests.put(
            f"{CART_SERVICE_URL}/update-order",
            json={"orderId": unique_order_id, "status": "confirmed"}
        )
        assert response.status_code == 200
        print(f"✅ Order status updated to: confirmed")

        # 3. Wait for consumer to process both events
        wait_for_consumer()

        # 4. Verify status changed
        response = requests.get(
            f"{ORDER_SERVICE_URL}/order-details",
            params={"orderId": unique_order_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["order"]["status"] == "confirmed"
        print(f"✅ Order status verified: {data['order']['status']}")

    def test_get_all_order_ids_from_topic(self, unique_order_id):
        """Test: Create order → Check it appears in topic tracking."""
        # 1. Create order
        response = requests.post(
            f"{CART_SERVICE_URL}/create-order",
            json={"orderId": unique_order_id, "numberOfItems": 1}
        )
        assert response.status_code == 200
        print(f"\n✅ Order created: ORD-{unique_order_id}")

        # 2. Wait for consumer
        wait_for_consumer()

        # 3. Get all order IDs from topic
        response = requests.get(
            f"{ORDER_SERVICE_URL}/getAllOrderIdsFromTopic",
            params={"topicName": "orders.events"}
        )
        assert response.status_code == 200
        data = response.json()
        assert f"ORD-{unique_order_id}" in data["orderIds"]
        print(f"✅ Order found in topic: {data['orderIds'][-3:]}")  # Show last 3

    def test_update_nonexistent_order_returns_404(self):
        """Test: Update non-existent order returns 404."""
        response = requests.put(
            f"{CART_SERVICE_URL}/update-order",
            json={"orderId": "99999999", "status": "confirmed"}
        )
        assert response.status_code == 404
        print(f"\n✅ Correctly returned 404 for non-existent order")

    def test_get_nonexistent_order_returns_404(self):
        """Test: Get non-existent order returns 404."""
        response = requests.get(
            f"{ORDER_SERVICE_URL}/order-details",
            params={"orderId": "99999999"}
        )
        assert response.status_code == 404
        print(f"\n✅ Correctly returned 404 for non-existent order")


class TestE2EMultipleStatusUpdates:
    """Test multiple status updates flow."""

    def test_full_order_lifecycle(self, unique_order_id):
        """Test: new → confirmed → processing → shipped."""
        statuses = ["confirmed", "processing", "shipped"]

        # 1. Create order
        response = requests.post(
            f"{CART_SERVICE_URL}/create-order",
            json={"orderId": unique_order_id, "numberOfItems": 3}
        )
        assert response.status_code == 200
        print(f"\n✅ Order created: ORD-{unique_order_id} (status: new)")

        # 2. Update through each status
        for status in statuses:
            response = requests.put(
                f"{CART_SERVICE_URL}/update-order",
                json={"orderId": unique_order_id, "status": status}
            )
            assert response.status_code == 200
            print(f"✅ Status updated to: {status}")

        # 3. Wait and verify final status
        wait_for_consumer()

        response = requests.get(
            f"{ORDER_SERVICE_URL}/order-details",
            params={"orderId": unique_order_id}
        )
        assert response.status_code == 200
        assert response.json()["order"]["status"] == "shipped"
        print(f"✅ Final status verified: shipped")
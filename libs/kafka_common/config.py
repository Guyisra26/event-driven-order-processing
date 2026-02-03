import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
ORDERS_TOPIC = os.getenv("ORDERS_TOPIC", "orders.events")

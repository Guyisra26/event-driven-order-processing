from confluent_kafka import Producer, Consumer
from .config import KAFKA_BOOTSTRAP_SERVERS

def create_producer() -> Producer:
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "acks": "all",
        "retries": 3,
        "retry.backoff.ms": 200,
        "linger.ms": 5,
        "enable.idempotence": True,
    }
    return Producer(conf)

def create_consumer(group_id: str, auto_offset_reset: str = "earliest") -> Consumer:
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": group_id,
        "auto.offset.reset": auto_offset_reset,
        "enable.auto.commit": True,
    }
    return Consumer(conf)

from __future__ import annotations

import time
from typing import Optional

from confluent_kafka import Producer, KafkaException

from libs.kafka_common.config import ORDERS_TOPIC
from libs.kafka_common.kafka_factory import create_producer
from libs.kafka_common.serdes_json import serialize_event
from libs.kafka_common.events import OrderCreatedEvent, OrderStatusUpdatedEvent
from libs.kafka_common.models import Order, OrderStatus


class KafkaPublishError(RuntimeError):
    """Base error when failing to publish to Kafka."""


class KafkaBrokersUnavailable(KafkaPublishError):
    """Raised when brokers are not available / connection issue."""


class KafkaTimeout(KafkaPublishError):
    """Raised when message could not be delivered within timeout."""


class ProducerQueueFull(KafkaPublishError):
    """Raised when local producer queue is full (BufferError)."""


class OrderEventPublisher:
    def __init__(self, producer: Optional[Producer] = None,topic: str = ORDERS_TOPIC,max_retries: int = 3,retry_backoff_ms: int = 200,flush_timeout_sec: float = 10.0):
        self.producer = producer or create_producer()
        self.topic = topic
        self.max_retries = max_retries
        self.retry_backoff_ms = retry_backoff_ms
        self.flush_timeout_sec = flush_timeout_sec


    def _produce(self,*, key: str,value: bytes) -> None:
        last_err: Optional[Exception] = None
        for attempt in range(1, (self.max_retries + 1)):
            try:
                self.producer.poll(0)
                self.producer.produce(topic=self.topic,key=key.encode("utf-8"),value=value)
                remaining = self.producer.flush(self.flush_timeout_sec)
                if remaining != 0:
                    raise KafkaTimeout(f"Flush timeout: {remaining} message(s) pending")
                return
            except BufferError as e:
                last_err = e
                time.sleep(self.retry_backoff_ms * attempt / 1000.0)
            except KafkaException as e:
                last_err = e
                time.sleep(self.retry_backoff_ms * attempt / 1000.0)
            except KafkaPublishError:
                raise
            except Exception as e:
                last_err = e
                time.sleep(self.retry_backoff_ms * attempt / 1000.0)

        if isinstance(last_err, BufferError):
            raise ProducerQueueFull(str(last_err)) from last_err
        if isinstance(last_err, KafkaException):
            raise KafkaBrokersUnavailable(str(last_err)) from last_err
        raise KafkaPublishError(f"Failed to publish after retries: {last_err}") from last_err

    def publish_order_created(self, order: Order) -> OrderCreatedEvent:
        event = OrderCreatedEvent(order_id = order.order_id, order=order)
        self._produce(key=event.order_id,value=serialize_event(event))
        return event

    def publish_order_status_updated(self, order_id: str, status: OrderStatus) -> OrderStatusUpdatedEvent:
        event = OrderStatusUpdatedEvent(order_id=order_id, status=status)
        self._produce(key=event.order_id,value=serialize_event(event))
        return event






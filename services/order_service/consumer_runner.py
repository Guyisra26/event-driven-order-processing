from __future__ import annotations

import threading
from confluent_kafka import KafkaException, KafkaError

from libs.kafka_common.config import ORDERS_TOPIC
from libs.kafka_common.kafka_factory import create_consumer
from libs.kafka_common.serdes_json import deserialize_event

from .consumer_db import OrderDB
from .order_event_handler import OrderEventHandler


class ConsumerRunner:
    def __init__(
        self,
        db: OrderDB,
        group_id: str = "order-service",
        max_retries: int = 5,
        retry_backoff_sec: float = 2.0,
    ) -> None:
        self.db = db
        self.group_id = group_id
        self.max_retries = max_retries
        self.retry_backoff_sec = retry_backoff_sec
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_with_reconnect, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run_with_reconnect(self) -> None:
        """Wrapper that handles reconnection on failures."""
        retry_count = 0

        while not self._stop_event.is_set() and retry_count < self.max_retries:
            try:
                self._run()
                if self._stop_event.is_set():
                    break
                retry_count = 0
            except Exception as e:
                retry_count += 1
                print(f"Consumer error (attempt {retry_count}/{self.max_retries}): {e}")
                if retry_count < self.max_retries:
                    print(f"Reconnecting in {self.retry_backoff_sec} seconds...")
                    self._stop_event.wait(self.retry_backoff_sec)

        if retry_count >= self.max_retries:
            print("Max retries reached. Consumer stopped.")

    def _run(self) -> None:
        """Main consumer loop."""
        consumer = create_consumer(
            group_id=self.group_id,
            auto_offset_reset="earliest"
        )
        handler = OrderEventHandler(self.db)
        consumer.subscribe([ORDERS_TOPIC])

        try:
            while not self._stop_event.is_set():
                msg = consumer.poll(1.0)
                if msg is None:
                    continue

                if msg.error():
                    # Topic not available yet - just wait, don't fail
                    if msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        continue
                    raise KafkaException(msg.error())

                try:
                    event = deserialize_event(msg.value())
                    handler.handle(event, topic=msg.topic())
                except Exception as e:
                    print(f"Failed to process message: {e}")
                    continue

        finally:
            consumer.close()

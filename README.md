# Event-Driven Order Processing System

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-7.6-231F20?logo=apachekafka&logoColor=white)](https://kafka.apache.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

A production-style **event-driven microservices system** built with **FastAPI** and **Apache Kafka**, implementing order lifecycle management with strict event ordering, idempotent processing, and resilient error handling.

---

## Architecture

```
┌──────────────┐       ┌─────────────────┐       ┌──────────────────┐
│    Client     │──────▶│  Cart Service    │──────▶│   Apache Kafka   │
│  (HTTP API)   │       │  (Producer:8000) │       │  orders.events   │
└──────────────┘       └─────────────────┘       └────────┬─────────┘
                                                          │
                                                          ▼
                                                 ┌──────────────────┐
                                                 │  Order Service    │
                                                 │  (Consumer:8001) │
                                                 └──────────────────┘
```

**Flow:**
1. Client sends HTTP requests to the **Cart Service**
2. Cart Service validates the request and publishes order events to Kafka
3. **Order Service** consumes events sequentially per order (guaranteed by partition key)
4. Order state and shipping costs are calculated and exposed via REST API

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI + Uvicorn |
| Message Broker | Apache Kafka (Confluent) |
| Serialization | JSON with Pydantic models |
| Containerization | Docker + Docker Compose |
| Language | Python 3.11 |

---

## Key Design Decisions

### Event-Driven Communication
Services are fully decoupled — the producer has no knowledge of downstream consumers. This enables independent scaling, deployment, and failure isolation.

### Kafka Partition Key Strategy
All events use `order_id` as the message key. This ensures:
- **Strict ordering** — all events for the same order land in the same partition
- **Horizontal scalability** — different orders are distributed across partitions
- **Consistency** — status updates are always processed after the corresponding order creation

### Event Types
| Event | Trigger | Payload |
|-------|---------|---------|
| `ORDER_CREATED` | `POST /create-order` | Full order object |
| `ORDER_STATUS_UPDATED` | `PUT /update-order` | Order ID + new status |

---

## Error Handling

### Producer (Cart Service)
- **Idempotent producer** (`enable.idempotence = true`) prevents duplicate messages on retry
- **`acks=all`** ensures messages are replicated before acknowledgment
- **Exponential backoff** for transient Kafka failures (broker unavailable, buffer full, flush timeout)
- Proper HTTP status codes: `409` for duplicates, `404` for missing orders, `503` for Kafka issues

### Consumer (Order Service)
- **Auto-reconnection** with configurable backoff on Kafka connection loss
- **Poison message handling** — malformed messages are logged and skipped
- **Out-of-order event buffering** — status updates arriving before `ORDER_CREATED` are queued and applied when the order arrives
- **Idempotent processing** — duplicate `ORDER_CREATED` events are safely ignored
- **Graceful topic handling** — consumer starts cleanly even if the topic doesn't exist yet

---

## API Reference

### Cart Service (Producer) — Port 8000

#### `POST /create-order`
Creates a new order and publishes an `ORDER_CREATED` event.

```bash
curl -X POST http://localhost:8000/create-order \
  -H "Content-Type: application/json" \
  -d '{"order_id": "123", "number_of_items": 3}'
```

```json
{
  "message": "order created and published successfully",
  "orderId": "ORD-123"
}
```

#### `PUT /update-order`
Updates order status and publishes an `ORDER_STATUS_UPDATED` event.

```bash
curl -X PUT http://localhost:8000/update-order \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORD-123", "status": "confirmed"}'
```

```json
{
  "message": "order status updated and published successfully",
  "orderId": "ORD-123"
}
```

---

### Order Service (Consumer) — Port 8001

#### `GET /order-details?orderId=<id>`
Returns order details with calculated shipping cost.

```bash
curl http://localhost:8001/order-details?orderId=ORD-123
```

```json
{
  "order": {
    "orderId": "ORD-123",
    "customerId": "CUST-...",
    "orderDate": "2024-01-18T12:00:00Z",
    "items": ["..."],
    "totalAmount": 150.00,
    "currency": "USD",
    "status": "confirmed"
  },
  "shippingCost": 3.00
}
```

#### `GET /getAllOrderIdsFromTopic?topicName=<topic>`
Returns all order IDs received from a Kafka topic.

```bash
curl http://localhost:8001/getAllOrderIdsFromTopic?topicName=orders.events
```

```json
{
  "topicName": "orders.events",
  "orderIds": ["ORD-123", "ORD-124", "ORD-125"]
}
```

---

## Getting Started

### Prerequisites
- [Docker](https://www.docker.com/products/docker-desktop/) installed and running

### Run the Producer (Cart Service)
```bash
cd services/cart_service
docker-compose -f docker-compose-producer.yml up --build
```
API available at `http://localhost:8000`

### Run the Consumer (Order Service)
```bash
cd services/order_service
docker-compose -f docker-compose-consumer.yml up --build
```
API available at `http://localhost:8001`

### Stop & Clean Up
```bash
docker-compose -f docker-compose-producer.yml down -v
docker-compose -f docker-compose-consumer.yml down -v
```

---

## Project Structure

```
.
├── Dockerfile
├── requirements.txt
├── docker-compose.yml                          # Full system compose
├── libs/
│   └── kafka_common/                           # Shared Kafka library
│       ├── config.py                           # Broker configuration
│       ├── kafka_factory.py                    # Producer/Consumer factory
│       ├── events.py                           # Event models
│       ├── models.py                           # Order domain models
│       └── serdes_json.py                      # JSON serialization
├── services/
│   ├── cart_service/                           # Producer microservice
│   │   ├── docker-compose-producer.yml
│   │   ├── main.py
│   │   ├── app/api/routes.py                   # REST endpoints
│   │   ├── publisher.py                        # Kafka publisher
│   │   ├── order_generator.py                  # Order creation logic
│   │   └── store_memory.py                     # In-memory order store
│   └── order_service/                          # Consumer microservice
│       ├── docker-compose-consumer.yml
│       ├── app/
│       │   ├── main.py
│       │   └── api/routes.py                   # REST endpoints
│       ├── consumer_runner.py                  # Kafka consumer loop
│       ├── order_event_handler.py              # Event processing logic
│       ├── consumer_db.py                      # In-memory order storage
│       └── tests/                              # Unit tests
└── tests/
    └── test_e2e.py                             # End-to-end tests
```

---

## Testing

```bash
# Run unit tests
pip install pytest pytest-asyncio httpx
PYTHONPATH=. pytest services/order_service/tests/ -v
```

---

## License

MIT
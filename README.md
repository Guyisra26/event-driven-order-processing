# Event-Driven Architecture - Exercise 2

## 1. Student Information
- **Full Name:** Guy Israeli
- **ID Number:** 323870238

---

## 2. Topic Names and Purpose

| Topic Name | Used By | Purpose |
|------------|---------|---------|
| `orders.events` | Producer (Cart Service) | Publishes order events when orders are created or updated |
| `orders.events` | Consumer (Order Service) | Receives and processes order events to store order details and calculate shipping costs |

**Event Types Published to `orders.events`:**
- `ORDER_CREATED` - Published when a new order is created via `/create-order`. Contains the full order object.
- `ORDER_STATUS_UPDATED` - Published when order status changes via `/update-order`. Contains the order ID and new status.

---

## 3. Message Key

**Key Used:** `order_id` (e.g., `ORD-123`)

**Why this key was chosen:**
1. **Ordering Guarantee:** Kafka guarantees message ordering only within a single partition. By using `order_id` as the key, all events for the same order are hashed to the same partition, ensuring they are processed in the exact sequence they were published.
2. **Consistency:** When an order is created and then updated multiple times, the consumer processes these events in the correct chronological order, preventing race conditions.
3. **Scalability:** Different orders can be processed in parallel across different partitions, while events for the same order remain strictly sequential.

---

## 4. Error Handling Approaches

### 4.1 Producer (Cart Service) Error Handling

| Error Type | Handling Approach | HTTP Response |
|------------|-------------------|---------------|
| Order already exists | Catch `OrderAlreadyExists` exception | 409 Conflict |
| Order not found (on update) | Catch `OrderNotFound` exception | 404 Not Found |
| Kafka broker unavailable | Retry with exponential backoff (3 retries), raise `KafkaBrokersUnavailable` | 503 Service Unavailable |
| Kafka flush timeout | Retry with backoff, raise `KafkaTimeout` | 503 Service Unavailable |
| Producer queue full (BufferError) | Retry with backoff, raise `ProducerQueueFull` | 503 Service Unavailable |
| General/unexpected errors | Catch all exceptions | 500 Internal Server Error |

**Why these approaches:**
- **Retry with backoff** for Kafka errors because they are often transient (broker restart, network blip).
- **Idempotent producer** (`enable.idempotence: True`) prevents duplicate messages even when retrying.
- **`acks: all`** ensures durability - message is only acknowledged after all in-sync replicas confirm.
- **Specific HTTP status codes** allow clients to differentiate between client errors (4xx) and server/infrastructure errors (5xx).

### 4.2 Consumer (Order Service) Error Handling

| Error Type | Handling Approach | Why |
|------------|-------------------|-----|
| Topic not available (`UNKNOWN_TOPIC_OR_PART`) | Continue polling silently | Topic auto-creates when producer sends first message |
| Kafka connection error | Reconnect with backoff (5 retries, 2 sec interval) | Transient failures recover automatically |
| Message deserialization error | Log error, skip message, continue | Prevents poison messages from blocking the queue |
| Out-of-order events (status update before create) | Store pending status in memory, apply when order arrives | Handles eventual consistency without losing data |
| Duplicate `ORDER_CREATED` events | Ignore if order already exists in DB | Ensures idempotent processing |

**Why these approaches:**
- **Reconnection logic** ensures the consumer auto-recovers from temporary Kafka issues.
- **Graceful handling of missing topics** allows services to start in any order.
- **Pending status buffer** handles race conditions where status updates arrive before the order creation event.

### 4.3 API Error Responses Summary

| Endpoint | Method | Success | Error Cases |
|----------|--------|---------|-------------|
| `/create-order` | POST | 200 | 409 (duplicate), 503 (Kafka), 500 (general) |
| `/update-order` | PUT | 200 | 404 (not found), 503 (Kafka), 500 (general) |
| `/order-details` | GET | 200 | 400 (invalid orderId format), 404 (not found) |
| `/getAllOrderIdsFromTopic` | GET | 200 | Returns empty list if no orders |

---

## 5. How to Run (Windows Instructions)

### Prerequisites
- Docker Desktop for Windows installed and running
- Open PowerShell or Command Prompt

### Option A: Run Producer (Cart Service)
```powershell
cd services\cart_service
docker-compose -f docker-compose-producer.yml up --build
```
API available at: `http://localhost:8000`

**Test the API:**
```powershell
# Create an order
curl -X POST http://localhost:8000/create-order -H "Content-Type: application/json" -d "{\"order_id\": \"123\", \"number_of_items\": 3}"

# Update order status
curl -X PUT http://localhost:8000/update-order -H "Content-Type: application/json" -d "{\"order_id\": \"ORD-123\", \"status\": \"confirmed\"}"
```

### Option B: Run Consumer (Order Service)
```powershell
cd services\order_service
docker-compose -f docker-compose-consumer.yml up --build
```
API available at: `http://localhost:8001`

**Test the API:**
```powershell
# Get order details
curl http://localhost:8001/order-details?orderId=ORD-123

# Get all order IDs from topic
curl http://localhost:8001/getAllOrderIdsFromTopic?topicName=orders.events
```

### Running Both Services Together (Full Integration)
To test the full flow where producer sends orders and consumer receives them, use the main docker-compose from the project root:

```powershell
# From project root directory
docker-compose up --build
```

This runs both services with a **shared Kafka cluster**, allowing end-to-end communication:
- Cart Service API: `http://localhost:8000`
- Order Service API: `http://localhost:8001`

**Note:** The individual docker-compose files in each service folder are designed for **isolated testing** of each service. For full integration where orders flow from producer to consumer, use the root docker-compose.yml.

### Stopping Services
```powershell
# Stop Producer
cd services\cart_service
docker-compose -f docker-compose-producer.yml down

# Stop Consumer
cd services\order_service
docker-compose -f docker-compose-consumer.yml down
```

---

## 6. API Endpoints

### Cart Service (Producer) - Port 8000

#### POST /create-order
Creates a new order and publishes `ORDER_CREATED` event to Kafka.

**Request:**
```json
{
  "order_id": "123",
  "number_of_items": 3
}
```

**Response (200):**
```json
{
  "message": "order created and published successfully",
  "orderId": "ORD-123"
}
```

#### PUT /update-order
Updates order status and publishes `ORDER_STATUS_UPDATED` event to Kafka.

**Request:**
```json
{
  "order_id": "ORD-123",
  "status": "confirmed"
}
```

**Response (200):**
```json
{
  "message": "order status updated and published successfully",
  "orderId": "ORD-123"
}
```

### Order Service (Consumer) - Port 8001

#### GET /order-details?orderId=\<id\>
Returns order details with calculated shipping cost.

**Response (200):**
```json
{
  "order": {
    "orderId": "ORD-123",
    "customerId": "CUST-...",
    "orderDate": "2024-01-18T12:00:00Z",
    "items": [...],
    "totalAmount": 150.00,
    "currency": "USD",
    "status": "confirmed"
  },
  "shippingCost": 3.00
}
```

#### GET /getAllOrderIdsFromTopic?topicName=\<topic\>
Returns all order IDs received from the specified Kafka topic.

**Response (200):**
```json
{
  "topicName": "orders.events",
  "orderIds": ["ORD-123", "ORD-124", "ORD-125"]
}
```

---

## 7. Project Structure

```
ex2_event_driven/
├── docker-compose.yml              # Main compose (all services)
├── docker-compose.dev.yml          # Development with Kafka UI
├── Dockerfile
├── requirements.txt
├── libs/
│   └── kafka_common/               # Shared Kafka utilities
│       ├── config.py               # Kafka configuration
│       ├── kafka_factory.py        # Producer/Consumer factory
│       ├── events.py               # Event models
│       ├── models.py               # Order models
│       └── serdes_json.py          # JSON serialization
├── services/
│   ├── cart_service/               # Producer service
│   │   ├── docker-compose-producer.yml  # Standalone compose file
│   │   ├── app/api/routes.py       # API endpoints
│   │   ├── publisher.py            # Kafka publisher with error handling
│   │   └── order_generator.py      # Order creation logic
│   └── order_service/              # Consumer service
│       ├── docker-compose-consumer.yml  # Standalone compose file
│       ├── app/api/routes.py       # API endpoints
│       ├── consumer_runner.py      # Kafka consumer with reconnection
│       ├── order_event_handler.py  # Event processing logic
│       └── consumer_db.py          # In-memory order storage
└── tests/
```

---

## 8. Submission Files

### Docker Compose Files (2 required)
1. **services/cart_service/docker-compose-producer.yml** - Producer (Cart Service) Docker Compose
2. **services/order_service/docker-compose-consumer.yml** - Consumer (Order Service) Docker Compose

### Documentation
3. **README.md** - This file (answers all required questions)

### How to Test (for checker on Windows)

**Step 1:** Extract the submitted zip file

**Step 2:** Run Producer (Cart Service)
```powershell
cd services\cart_service
docker-compose -f docker-compose-producer.yml up --build
```
Wait for "Application startup complete" message. API at `http://localhost:8000`

**Step 3:** Run Consumer (Order Service) - in a new terminal
```powershell
cd services\order_service
docker-compose -f docker-compose-consumer.yml up --build
```
Wait for "Application startup complete" message. API at `http://localhost:8001`

**Step 4:** Test the flow
```powershell
# Create an order (Producer)
curl -X POST http://localhost:8000/create-order -H "Content-Type: application/json" -d "{\"order_id\": \"123\", \"number_of_items\": 3}"

# Get order details (Consumer)
curl "http://localhost:8001/order-details?orderId=ORD-123"

# Update order status (Producer)
curl -X PUT http://localhost:8000/update-order -H "Content-Type: application/json" -d "{\"order_id\": \"ORD-123\", \"status\": \"confirmed\"}"

# Get all order IDs from topic (Consumer)
curl "http://localhost:8001/getAllOrderIdsFromTopic?topicName=orders.events"
```
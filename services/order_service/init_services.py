from services.order_service.consumer_db import OrderDB
from services.order_service.consumer_runner import ConsumerRunner

db = OrderDB()
consumer_runner = ConsumerRunner(db=db)

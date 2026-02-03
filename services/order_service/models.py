from libs.kafka_common.models import Order
from pydantic import BaseModel


class OrderEntry(BaseModel):
    order: Order
    shipping_cost: float

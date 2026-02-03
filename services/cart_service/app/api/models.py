from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

from libs.kafka_common.models import OrderStatus

ORDER_ID_RE = re.compile(r"^(ORD-)?\d+$")

class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: str = Field(..., alias="orderId")
    number_of_items: int = Field(..., alias="numberOfItems", gt=0)

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str):
        if not ORDER_ID_RE.match(v):
            raise ValueError("orderId must be digits or 'ORD-<digits>'")
        return v


class UpdateOrderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: str = Field(..., alias="orderId")
    status: OrderStatus

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str):
        if not ORDER_ID_RE.match(v):
            raise ValueError("orderId must be digits or 'ORD-<digits>'")
        return v

from pydantic import BaseModel, Field, ConfigDict,field_validator
from datetime import datetime
from typing import List
from enum import Enum


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    KRW = "KRW"
    CNY = "CNY"
    INR = "INR"
    BRL = "BRL"
    MXN = "MXN"
    ARS = "ARS"
    COP = "COP"

class OrderStatus(str, Enum):
    NEW = "new"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    item_id: str = Field(..., alias = "itemId")
    quantity: int
    price: float

    model_config = ConfigDict(populate_by_name=True)


class Order(BaseModel):
    order_id: str = Field(..., alias = "orderId")
    customer_id: str = Field(..., alias = "customerId")
    order_date: datetime = Field(..., alias = "orderDate")
    items: List[OrderItem]
    total_amount: float
    currency: Currency
    status: OrderStatus

    model_config = ConfigDict(populate_by_name=True)
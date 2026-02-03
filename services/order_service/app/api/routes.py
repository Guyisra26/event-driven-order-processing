from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from services.order_service.consumer_db import OrderDB

router = APIRouter()


def get_db() -> OrderDB:
    """
    This should be overridden in app/main.py so API and consumer share the same DB instance.
    """
    raise RuntimeError("OrderDB dependency is not configured")


def _normalize_order_id(order_id: str) -> str:
    # Support "123" or "ORD-123"
    return f"ORD-{order_id}" if order_id.isdigit() else order_id


@router.get("/order-details")
def order_details(order_id: str = Query(...,alias="orderId"),db: OrderDB = Depends(get_db)):
    order_id = _normalize_order_id(order_id)

    if not (order_id.isdigit() or order_id.startswith("ORD-")):
        raise HTTPException(
            status_code=400,
            detail="orderId must be a numeric string or start with 'ORD-'",
        )

    entry = db.get(order_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="order not found")

    return {
        "order": entry.order.model_dump(by_alias=True),
        "shippingCost": entry.shipping_cost,
    }


@router.get("/getAllOrderIdsFromTopic")
def get_all_order_ids_from_topic(topic_name: str = Query(..., alias="topicName"),db: OrderDB = Depends(get_db),):
    order_ids = db.get_all_ids_for_topic(topic_name)
    return {"topicName": topic_name, "orderIds": order_ids}

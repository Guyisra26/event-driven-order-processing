from fastapi import APIRouter, Depends, HTTPException

from services.cart_service.app.api.models import CreateOrderRequest, UpdateOrderRequest
from services.cart_service.order_generator import OrderGenerator, OrderAlreadyExists, OrderNotFound
from services.cart_service.publisher import KafkaPublishError, KafkaBrokersUnavailable, KafkaTimeout, ProducerQueueFull

router = APIRouter()

def get_order_generator() -> OrderGenerator:
    """
    This should be overridden in main.py via app.dependency_overrides
    so we use the singleton generator (with the same store + publisher).
    """
    raise RuntimeError("OrderGenerator dependency is not configured")


@router.post("/create-order")
def create_order(request: CreateOrderRequest, order_generator: OrderGenerator = Depends(get_order_generator)):
    try:
        order_id = order_generator.create_order(request.order_id, request.number_of_items)
        return {"message": "order created and published successfully", "orderId": order_id}
    except OrderAlreadyExists as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (KafkaPublishError, KafkaBrokersUnavailable, KafkaTimeout, ProducerQueueFull) as e:
        raise HTTPException(status_code=503, detail=f"Failed to publish order event: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update-order")
def update_order(request: UpdateOrderRequest, order_generator: OrderGenerator = Depends(get_order_generator)):
    try:
        order_generator.update_order_status(request.order_id, request.status)
        return {"message": "order status updated and published successfully", "orderId": request.order_id}
    except OrderNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (KafkaPublishError, KafkaBrokersUnavailable, KafkaTimeout, ProducerQueueFull) as e:
        raise HTTPException(status_code=503, detail=f"Failed to publish order status update event: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
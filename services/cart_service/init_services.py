
from services.cart_service.store_memory  import OrderStoreMemory
from services.cart_service.order_generator import OrderGenerator
from services.cart_service.publisher import OrderEventPublisher

order_store = OrderStoreMemory()
publisher = OrderEventPublisher()
order_generator = OrderGenerator(
    store=order_store,
    publisher=publisher,
)
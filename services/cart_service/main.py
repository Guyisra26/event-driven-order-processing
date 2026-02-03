# services/cart_service/app/main.py

from fastapi import FastAPI
from services.cart_service.app.api.routes import router, get_order_generator
from services.cart_service.init_services import order_generator

app = FastAPI()
app.include_router(router)

app.dependency_overrides[get_order_generator] = lambda: order_generator

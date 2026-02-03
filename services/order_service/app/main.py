from contextlib import asynccontextmanager
from fastapi import FastAPI

from services.order_service.app.api.routes import router, get_db
from services.order_service.init_services import db, consumer_runner


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    consumer_runner.start()
    yield
    # Shutdown
    consumer_runner.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(router)

app.dependency_overrides[get_db] = lambda: db

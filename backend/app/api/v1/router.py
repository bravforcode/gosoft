from fastapi import APIRouter

from app.api.v1.endpoints import alerts, analytics, auth, cameras, demo, inventory, purchase_orders, settings


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(inventory.router)
api_router.include_router(cameras.router)
api_router.include_router(alerts.router)
api_router.include_router(purchase_orders.router)
api_router.include_router(analytics.router)
api_router.include_router(settings.router)
api_router.include_router(demo.router)

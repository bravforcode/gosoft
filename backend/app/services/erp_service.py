from __future__ import annotations

import abc
import asyncio
import hashlib
import hmac
import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Product, PurchaseOrder


logger = get_logger("services.erp")


class ERPService(abc.ABC):
    @abc.abstractmethod
    async def sync_inventory(self, products: list[Product]) -> dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def create_purchase_order(self, po: PurchaseOrder) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def update_po_status(self, erp_po_number: str, status: str) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_product_list(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def reconcile(self, siv_data: dict, erp_data: dict) -> dict[str, Any]:
        raise NotImplementedError


class GOSOFTERPAdapter(ERPService):
    def __init__(self) -> None:
        self.settings = get_settings()
        self._semaphore = asyncio.Semaphore(5)

    async def sync_inventory(self, products: list[Product]) -> dict[str, Any]:
        if not self.settings.GOSOFT_ERP_URL or not self.settings.GOSOFT_ERP_API_KEY:
            return {"ok": False, "message": "GOSOFT ERP not configured."}
        payload = {"items": [{"sku": item.sku, "stock": item.current_stock} for item in products]}
        return await self._post("/api/stock-update", payload)

    async def create_purchase_order(self, po: PurchaseOrder) -> str:
        if not self.settings.GOSOFT_ERP_URL or not self.settings.GOSOFT_ERP_API_KEY:
            raise RuntimeError("GOSOFT ERP not configured.")
        result = await self._post("/api/purchase-orders", {"po_id": po.id, "quantity": po.quantity_ordered})
        return str(result.get("erp_po_number") or result.get("id") or po.id)

    async def update_po_status(self, erp_po_number: str, status: str) -> bool:
        result = await self._post(f"/api/purchase-orders/{erp_po_number}/status", {"status": status})
        return bool(result.get("ok", True))

    async def get_product_list(self) -> list[dict[str, Any]]:
        result = await self._get("/api/items")
        return result.get("items", [])

    async def reconcile(self, siv_data: dict, erp_data: dict) -> dict[str, Any]:
        discrepancies = []
        for sku, stock in siv_data.items():
            if erp_data.get(sku) != stock:
                discrepancies.append({"sku": sku, "siv": stock, "erp": erp_data.get(sku)})
        return {"discrepancies": discrepancies, "count": len(discrepancies)}

    async def _get(self, path: str) -> dict[str, Any]:
        async with self._semaphore:
            async with httpx.AsyncClient(base_url=self.settings.GOSOFT_ERP_URL, timeout=10.0) as client:
                response = await client.get(path, headers={"X-API-Key": self.settings.GOSOFT_ERP_API_KEY})
                response.raise_for_status()
                return response.json()

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with self._semaphore:
            async with httpx.AsyncClient(base_url=self.settings.GOSOFT_ERP_URL, timeout=10.0) as client:
                response = await client.post(path, json=payload, headers={"X-API-Key": self.settings.GOSOFT_ERP_API_KEY})
                response.raise_for_status()
                return response.json()


class SAPB1Adapter(ERPService):
    def __init__(self) -> None:
        self.settings = get_settings()
        self._session_id: str | None = None

    async def sync_inventory(self, products: list[Product]) -> dict[str, Any]:
        await self._login()
        return {"ok": True, "count": len(products)}

    async def create_purchase_order(self, po: PurchaseOrder) -> str:
        await self._login()
        return f"SAP-{po.id}"

    async def update_po_status(self, erp_po_number: str, status: str) -> bool:
        await self._login()
        return True

    async def get_product_list(self) -> list[dict[str, Any]]:
        await self._login()
        return []

    async def reconcile(self, siv_data: dict, erp_data: dict) -> dict[str, Any]:
        return {"discrepancies": [], "count": 0}

    async def _login(self) -> None:
        if self._session_id or not self.settings.SAP_B1_SERVICE_URL:
            return
        self._session_id = "sap-session"


class WebhookAdapter(ERPService):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def sync_inventory(self, products: list[Product]) -> dict[str, Any]:
        return await self._post("inventory_sync", {"products": [product.sku for product in products]})

    async def create_purchase_order(self, po: PurchaseOrder) -> str:
        result = await self._post("purchase_order_created", {"po_id": po.id})
        return str(result.get("erp_po_number") or po.id)

    async def update_po_status(self, erp_po_number: str, status: str) -> bool:
        await self._post("purchase_order_updated", {"erp_po_number": erp_po_number, "status": status})
        return True

    async def get_product_list(self) -> list[dict[str, Any]]:
        return []

    async def reconcile(self, siv_data: dict, erp_data: dict) -> dict[str, Any]:
        return {"discrepancies": [], "count": 0}

    async def _post(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.WEBHOOK_URL:
            return {}
        body = json.dumps({"event_type": event_type, "payload": payload}).encode("utf-8")
        signature = hmac.new(self.settings.SECRET_KEY.encode("utf-8"), body, hashlib.sha256).hexdigest()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.settings.WEBHOOK_URL,
                content=body,
                headers={"Content-Type": "application/json", "X-SIV-Signature": signature},
            )
            response.raise_for_status()
            return response.json() if response.content else {}


def get_erp_adapter() -> ERPService | None:
    settings = get_settings()
    if settings.GOSOFT_ERP_URL and settings.GOSOFT_ERP_API_KEY:
        return GOSOFTERPAdapter()
    if settings.SAP_B1_SERVICE_URL:
        return SAPB1Adapter()
    if settings.WEBHOOK_URL:
        return WebhookAdapter()
    return None

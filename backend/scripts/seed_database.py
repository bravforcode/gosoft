from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.database import init_db
from app.db.models import AlertStatus, CameraStatus, EventType, PurchaseOrderStatus, Severity, UserRole


USERS = [
    {"username": "admin", "email": "admin@siv.example.com", "password": "admin123", "role": "admin"},
    {"username": "manager", "email": "manager@siv.example.com", "password": "manager123", "role": "manager"},
    {"username": "operator", "email": "operator@siv.example.com", "password": "operator123", "role": "operator"},
]

VENDORS = [
    {"name": "Thai Beverage PLC", "lead_time_days": 1, "contact_email": "ops@thaibev.example"},
    {"name": "PepsiCo Thailand", "lead_time_days": 2, "contact_email": "b2b@pepsico.example"},
    {"name": "Nestlé Thailand", "lead_time_days": 2, "contact_email": "retail@nestle.example"},
    {"name": "TC Pharmaceutical", "lead_time_days": 1, "contact_email": "sales@tcp.example"},
    {"name": "Unilever Thailand", "lead_time_days": 3, "contact_email": "trade@unilever.example"},
]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_sqlite_path(database_url: str, backend_root: Path) -> Path:
    prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
    for prefix in prefixes:
        if database_url.startswith(prefix):
            raw_path = database_url[len(prefix) :]
            candidate = Path(raw_path)
            return candidate if candidate.is_absolute() else (backend_root / candidate).resolve()
    raise ValueError(f"Unsupported DATABASE_URL for local sqlite seeding: {database_url}")


def bootstrap_database(target_db: Path, template_db: Path) -> None:
    target_db.parent.mkdir(parents=True, exist_ok=True)
    if template_db.exists():
        shutil.copy2(template_db, target_db)
        return
    if target_db.exists():
        target_db.unlink()
    asyncio.run(init_db())


def reset_database(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")
    for table in (
        "purchase_orders",
        "alerts",
        "detection_events",
        "products",
        "cameras",
        "system_settings",
        "users",
        "vendors",
    ):
        cursor.execute(f"DELETE FROM {table}")
    cursor.execute("PRAGMA foreign_keys = ON")
    connection.commit()


def seed_users(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    created_at = utcnow_iso()
    for user in USERS:
        cursor.execute(
            """
            INSERT INTO users (id, username, email, hashed_password, role, is_active, last_login, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                user["username"],
                user["email"],
                get_password_hash(user["password"]),
                UserRole(user["role"]).name,
                1,
                None,
                created_at,
            ),
        )
    connection.commit()


def seed_vendors(connection: sqlite3.Connection) -> dict[str, str]:
    cursor = connection.cursor()
    vendor_ids: dict[str, str] = {}
    for vendor in VENDORS:
        vendor_id = str(uuid4())
        vendor_ids[vendor["name"]] = vendor_id
        cursor.execute(
            """
            INSERT INTO vendors (id, name, contact_email, contact_phone, lead_time_days, api_url, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vendor_id,
                vendor["name"],
                vendor["contact_email"],
                None,
                vendor["lead_time_days"],
                None,
                1,
            ),
        )
    connection.commit()
    return vendor_ids


def seed_cameras(connection: sqlite3.Connection) -> None:
    settings = get_settings()
    cursor = connection.cursor()
    defaults = [
        {"id": "CAM-01", "url": "0", "name": "Main Entrance Camera", "zone": "Zone A"},
        {"id": "CAM-02", "url": "", "name": "Zone B Camera", "zone": "Zone B"},
        {"id": "CAM-03", "url": "", "name": "Zone C Camera", "zone": "Zone C"},
        {"id": "CAM-04", "url": "", "name": "Zone D Camera", "zone": "Zone D"},
    ]
    overrides = {camera["id"]: camera for camera in settings.configured_cameras}
    cameras = [{**camera, **overrides.get(camera["id"], {})} for camera in defaults]
    for camera in cameras:
        cursor.execute(
            """
            INSERT INTO cameras (
                id, name, zone, stream_url, status, resolution_width, resolution_height,
                fps_processing, is_active, last_frame_at, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                camera["id"],
                camera["name"],
                camera["zone"],
                camera["url"],
                CameraStatus.OFFLINE.name,
                1280,
                720,
                settings.CAMERA_PROCESSING_FPS,
                1,
                None,
                json.dumps({"source": camera["url"]}),
            ),
        )
    connection.commit()


def seed_products(connection: sqlite3.Connection, vendor_ids: dict[str, str], products_path: Path) -> list[dict[str, str | int | float | dict]]:
    cursor = connection.cursor()
    products = json.loads(products_path.read_text(encoding="utf-8"))
    now = utcnow_iso()
    for item in products:
        cursor.execute(
            """
            INSERT INTO products (
                id, sku, name_th, name_en, brand, category, barcode, zone_id, camera_id,
                max_capacity, current_stock, reorder_threshold, reorder_quantity, unit_cost,
                unit_price, vendor_id, shelf_position, product_color_hex, image_url, is_active,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                item["sku"],
                item["name_th"],
                item["name_en"],
                item["brand"],
                item["category"],
                item.get("barcode"),
                item["zone_id"],
                item["camera_id"],
                item["max_capacity"],
                int(item["max_capacity"] * 0.72),
                item["reorder_threshold"],
                item["reorder_quantity"],
                item["unit_cost"],
                item["unit_price"],
                vendor_ids[item["vendor"]],
                json.dumps(item["shelf_position"], ensure_ascii=False),
                item["product_color_hex"],
                item.get("image_url"),
                1,
                now,
                now,
            ),
        )
    connection.commit()
    return products


def seed_settings(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    updated_at = utcnow_iso()
    items = [
        ("stock_low_threshold", 0.50, "Low stock threshold"),
        ("stock_critical_threshold", 0.25, "Critical stock threshold"),
        ("auto_po_approval_limit", 5000, "Auto approve limit"),
        ("demo_mode", True, "Enable demo endpoints"),
        ("notification_channels", ["websocket"], "Enabled notification channels"),
    ]
    for key, value, description in items:
        cursor.execute(
            """
            INSERT INTO system_settings (key, value, description, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key, json.dumps(value, ensure_ascii=False), description, updated_at, "seed"),
        )
    connection.commit()


def load_product_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, sku, name_en, zone_id, camera_id, max_capacity, reorder_quantity,
               unit_cost, vendor_id
        FROM products
        ORDER BY sku
        """
    )
    return cursor.fetchall()


def seed_history(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    products = load_product_rows(connection)[:20]
    current_year = datetime.now(timezone.utc).year

    for index, product in enumerate(products):
        product_id = product["id"]
        for day_offset in range(7):
            created_at = (datetime.now(timezone.utc) - timedelta(days=day_offset)).replace(microsecond=0).isoformat()
            fullness = max(0.12, 0.82 - day_offset * 0.07)
            cursor.execute(
                """
                INSERT INTO detection_events (
                    id, camera_id, product_id, zone, event_type, severity,
                    fullness_before, fullness_after, confidence, frame_path,
                    ai_analysis, bbox_data, acknowledged_at, acknowledged_by, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    product["camera_id"],
                    product_id,
                    product["zone_id"],
                    EventType.STOCK_UPDATE.name,
                    Severity.WARNING.name if fullness < 0.5 else Severity.INFO.name,
                    round(min(1.0, fullness + 0.08), 4),
                    round(fullness, 4),
                    0.92,
                    None,
                    None,
                    None,
                    None,
                    None,
                    json.dumps({"seed": True}),
                    created_at,
                ),
            )

        if index < 8:
            quantity = int(product["reorder_quantity"])
            unit_cost = float(product["unit_cost"])
            cursor.execute(
                """
                INSERT INTO purchase_orders (
                    id, product_id, vendor_id, trigger_alert_id, quantity_ordered, unit_cost,
                    total_amount, status, approved_by, approved_at, expected_delivery,
                    notes, erp_po_number, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"PO-{current_year}-{index + 1:04d}",
                    product_id,
                    product["vendor_id"],
                    None,
                    quantity,
                    unit_cost,
                    round(unit_cost * quantity, 2),
                    PurchaseOrderStatus.DELIVERED.name,
                    "system",
                    utcnow_iso(),
                    utcnow_iso(),
                    "Seeded historical PO",
                    None,
                    utcnow_iso(),
                ),
            )

        event_id = str(uuid4())
        created_at = (datetime.now(timezone.utc) - timedelta(days=index % 5)).replace(microsecond=0).isoformat()
        cursor.execute(
            """
            INSERT INTO detection_events (
                id, camera_id, product_id, zone, event_type, severity,
                fullness_before, fullness_after, confidence, frame_path,
                ai_analysis, bbox_data, acknowledged_at, acknowledged_by, metadata, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                product["camera_id"],
                product_id,
                product["zone_id"],
                EventType.EMPTY_SHELF.name,
                Severity.CRITICAL.name,
                0.20,
                0.05,
                0.96,
                None,
                None,
                None,
                None,
                None,
                json.dumps({"seed": True}),
                created_at,
            ),
        )
        cursor.execute(
            """
            INSERT INTO alerts (
                id, event_id, product_id, camera_id, title, description, severity, status,
                auto_resolved_at, resolved_by, evidence_frame_path, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                event_id,
                product_id,
                product["camera_id"],
                f"Resolved alert for {product['name_en']}",
                "Historical resolved alert",
                Severity.CRITICAL.name,
                AlertStatus.RESOLVED.name,
                None,
                "system",
                None,
                created_at,
            ),
        )

    connection.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-history", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    template_db = BACKEND_ROOT / "test_siv.db"
    target_db = resolve_sqlite_path(settings.DATABASE_URL, BACKEND_ROOT)

    bootstrap_database(target_db, template_db)
    connection = sqlite3.connect(target_db)
    connection.row_factory = sqlite3.Row
    try:
        reset_database(connection)
        seed_users(connection)
        vendor_ids = seed_vendors(connection)
        seed_cameras(connection)
        products_path = BACKEND_ROOT / "data" / "products.json"
        seed_products(connection, vendor_ids, products_path)
        seed_settings(connection)
        if args.with_history:
            seed_history(connection)
    finally:
        connection.close()

    print(f"Database seeded successfully: {target_db}")


if __name__ == "__main__":
    main()

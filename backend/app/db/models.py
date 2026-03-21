from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql.schema import Column


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.utcnow()


def uuid_str() -> str:
    return str(uuid4())


class CameraStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class EventType(str, Enum):
    STOCK_UPDATE = "stock_update"
    EMPTY_SHELF = "empty_shelf"
    RESTOCK = "restock"
    PLANOGRAM_VIOLATION = "planogram_violation"
    ANOMALY = "anomaly"
    PERSON_DETECTED = "person_detected"
    DELIVERY = "delivery"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    AUTO_RESOLVED = "auto_resolved"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT_TO_VENDOR = "sent_to_vendor"
    CONFIRMED = "confirmed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String(36), primary_key=True, default=uuid_str)
    name = Column(String(255), unique=True, nullable=False, index=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(64), nullable=True)
    lead_time_days = Column(Integer, nullable=False, default=1)
    api_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    products = relationship("Product", back_populates="vendor")
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    zone = Column(String(64), nullable=False, index=True)
    stream_url = Column(String(1024), nullable=False)
    status = Column(SQLEnum(CameraStatus), nullable=False, default=CameraStatus.OFFLINE)
    resolution_width = Column(Integer, nullable=False, default=1280)
    resolution_height = Column(Integer, nullable=False, default=720)
    fps_processing = Column(Numeric(10, 2), nullable=False, default=2.0)
    is_active = Column(Boolean, nullable=False, default=True)
    last_frame_at = Column(DateTime, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)

    products = relationship("Product", back_populates="camera")
    events = relationship("DetectionEvent", back_populates="camera")
    alerts = relationship("Alert", back_populates="camera")


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=uuid_str)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    name_th = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=False)
    brand = Column(String(255), nullable=False)
    category = Column(String(255), nullable=False, index=True)
    barcode = Column(String(64), nullable=True, index=True)
    zone_id = Column(String(32), nullable=False, index=True)
    camera_id = Column(String(32), ForeignKey("cameras.id"), nullable=False, index=True)
    max_capacity = Column(Integer, nullable=False)
    current_stock = Column(Integer, nullable=False, default=0)
    reorder_threshold = Column(Integer, nullable=False)
    reorder_quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    unit_price = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    vendor_id = Column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    shelf_position = Column(JSON, nullable=False, default=dict)
    product_color_hex = Column(String(16), nullable=False)
    image_url = Column(String(1024), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    vendor = relationship("Vendor", back_populates="products")
    camera = relationship("Camera", back_populates="products")
    events = relationship("DetectionEvent", back_populates="product")
    alerts = relationship("Alert", back_populates="product")
    purchase_orders = relationship("PurchaseOrder", back_populates="product")


class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id = Column(String(36), primary_key=True, default=uuid_str)
    camera_id = Column(String(32), ForeignKey("cameras.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    zone = Column(String(32), nullable=False, index=True)
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    severity = Column(SQLEnum(Severity), nullable=False, default=Severity.INFO)
    fullness_before = Column(Numeric(10, 4), nullable=False, default=0.0)
    fullness_after = Column(Numeric(10, 4), nullable=False, default=0.0)
    confidence = Column(Numeric(10, 4), nullable=False, default=0.0)
    frame_path = Column(String(1024), nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    bbox_data = Column(JSON, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(255), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    camera = relationship("Camera", back_populates="events")
    product = relationship("Product", back_populates="events")
    alert = relationship("Alert", back_populates="event", uselist=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=uuid_str)
    event_id = Column(String(36), ForeignKey("detection_events.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    camera_id = Column(String(32), ForeignKey("cameras.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(Severity), nullable=False)
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE)
    auto_resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    evidence_frame_path = Column(String(1024), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    event = relationship("DetectionEvent", back_populates="alert")
    product = relationship("Product", back_populates="alerts")
    camera = relationship("Camera", back_populates="alerts")
    purchase_orders = relationship("PurchaseOrder", back_populates="trigger_alert")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String(32), primary_key=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    vendor_id = Column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    trigger_alert_id = Column(String(36), ForeignKey("alerts.id"), nullable=True, index=True)
    quantity_ordered = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(PurchaseOrderStatus), nullable=False, default=PurchaseOrderStatus.DRAFT)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    expected_delivery = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    erp_po_number = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    product = relationship("Product", back_populates="purchase_orders")
    vendor = relationship("Vendor", back_populates="purchase_orders")
    trigger_alert = relationship("Alert", back_populates="purchase_orders")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=uuid_str)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.VIEWER)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class SystemSettings(Base):
    __tablename__ = "system_settings"

    key = Column(String(128), primary_key=True)
    value = Column(JSON, nullable=False, default=dict)
    description = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    updated_by = Column(String(255), nullable=True)

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models import AlertStatus, CameraStatus, EventType, PurchaseOrderStatus, Severity, UserRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Pagination(BaseModel):
    total: int
    skip: int
    limit: int


class VendorBase(BaseModel):
    name: str
    contact_email: str | None = None
    contact_phone: str | None = None
    lead_time_days: int = 1
    api_url: str | None = None
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    lead_time_days: int | None = None
    api_url: str | None = None
    is_active: bool | None = None


class VendorRead(VendorBase, ORMModel):
    id: str


class CameraBase(BaseModel):
    name: str
    zone: str
    stream_url: str
    status: CameraStatus = CameraStatus.OFFLINE
    resolution_width: int = 1280
    resolution_height: int = 720
    fps_processing: Decimal = Decimal("2.0")
    is_active: bool = True
    last_frame_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")


class CameraCreate(CameraBase):
    id: str


class CameraUpdate(BaseModel):
    name: str | None = None
    zone: str | None = None
    stream_url: str | None = None
    status: CameraStatus | None = None
    resolution_width: int | None = None
    resolution_height: int | None = None
    fps_processing: Decimal | None = None
    is_active: bool | None = None
    last_frame_at: datetime | None = None
    metadata_json: dict[str, Any] | None = None


class CameraRead(CameraBase, ORMModel):
    id: str


class ProductBase(BaseModel):
    sku: str
    name_th: str
    name_en: str
    brand: str
    category: str
    barcode: str | None = None
    zone_id: str
    camera_id: str
    max_capacity: int
    current_stock: int = 0
    reorder_threshold: int
    reorder_quantity: int
    unit_cost: Decimal
    unit_price: Decimal
    vendor_id: str
    shelf_position: dict[str, Any] = Field(default_factory=dict)
    product_color_hex: str
    image_url: str | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name_th: str | None = None
    name_en: str | None = None
    brand: str | None = None
    category: str | None = None
    barcode: str | None = None
    zone_id: str | None = None
    camera_id: str | None = None
    max_capacity: int | None = None
    current_stock: int | None = None
    reorder_threshold: int | None = None
    reorder_quantity: int | None = None
    unit_cost: Decimal | None = None
    unit_price: Decimal | None = None
    vendor_id: str | None = None
    shelf_position: dict[str, Any] | None = None
    product_color_hex: str | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ProductSummary(ProductBase, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime
    vendor: VendorRead | None = None


class StockHistoryPoint(BaseModel):
    timestamp: datetime
    current_stock: int
    fullness_after: float


class DetectionEventBase(BaseModel):
    camera_id: str
    product_id: str | None = None
    zone: str
    event_type: EventType
    severity: Severity
    fullness_before: Decimal = Decimal("0.0")
    fullness_after: Decimal = Decimal("0.0")
    confidence: Decimal = Decimal("0.0")
    frame_path: str | None = None
    ai_analysis: dict[str, Any] | None = None
    bbox_data: dict[str, Any] | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")


class DetectionEventCreate(DetectionEventBase):
    pass


class DetectionEventUpdate(BaseModel):
    product_id: str | None = None
    severity: Severity | None = None
    fullness_before: Decimal | None = None
    fullness_after: Decimal | None = None
    confidence: Decimal | None = None
    frame_path: str | None = None
    ai_analysis: dict[str, Any] | None = None
    bbox_data: dict[str, Any] | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    metadata_json: dict[str, Any] | None = None


class DetectionEventRead(DetectionEventBase, ORMModel):
    id: str
    created_at: datetime


class AlertBase(BaseModel):
    event_id: str
    product_id: str | None = None
    camera_id: str
    title: str
    description: str
    severity: Severity
    status: AlertStatus = AlertStatus.ACTIVE
    auto_resolved_at: datetime | None = None
    resolved_by: str | None = None
    evidence_frame_path: str | None = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: Severity | None = None
    status: AlertStatus | None = None
    auto_resolved_at: datetime | None = None
    resolved_by: str | None = None
    evidence_frame_path: str | None = None


class AlertRead(AlertBase, ORMModel):
    id: str
    created_at: datetime
    event: DetectionEventRead | None = None


class ProductDetail(ProductSummary):
    alerts: list[AlertRead] = Field(default_factory=list)
    events: list[DetectionEventRead] = Field(default_factory=list)
    stock_history: list[StockHistoryPoint] = Field(default_factory=list)


class PaginatedProductList(BaseModel):
    items: list[ProductSummary]
    pagination: Pagination


class PaginatedAlertList(BaseModel):
    items: list[AlertRead]
    pagination: Pagination


class PurchaseOrderBase(BaseModel):
    product_id: str
    vendor_id: str
    trigger_alert_id: str | None = None
    quantity_ordered: int
    unit_cost: Decimal
    total_amount: Decimal
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    approved_by: str | None = None
    approved_at: datetime | None = None
    expected_delivery: datetime | None = None
    notes: str | None = None
    erp_po_number: str | None = None


class PurchaseOrderCreate(PurchaseOrderBase):
    id: str | None = None


class PurchaseOrderUpdate(BaseModel):
    quantity_ordered: int | None = None
    unit_cost: Decimal | None = None
    total_amount: Decimal | None = None
    status: PurchaseOrderStatus | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    expected_delivery: datetime | None = None
    notes: str | None = None
    erp_po_number: str | None = None


class PurchaseOrderRead(PurchaseOrderBase, ORMModel):
    id: str
    created_at: datetime
    product: ProductSummary | None = None
    vendor: VendorRead | None = None
    trigger_alert: AlertRead | None = None


class PaginatedPOList(BaseModel):
    items: list[PurchaseOrderRead]
    pagination: Pagination


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserProfile(UserBase, ORMModel):
    id: str
    last_login: datetime | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserProfile


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class SystemSettingBase(BaseModel):
    value: Any
    description: str
    updated_by: str | None = None


class SystemSettingCreate(SystemSettingBase):
    key: str


class SystemSettingUpdate(BaseModel):
    value: Any
    description: str | None = None
    updated_by: str | None = None


class SystemSettingRead(SystemSettingBase, ORMModel):
    key: str
    updated_at: datetime


class SettingItem(BaseModel):
    key: str
    value: Any
    description: str
    updated_at: datetime


class SettingsDict(BaseModel):
    items: list[SettingItem]


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


class BulkResult(BaseModel):
    processed: int
    succeeded: int
    failed: int
    ids: list[str] = Field(default_factory=list)


class SnapshotResult(BaseModel):
    camera_id: str
    file_path: str
    captured_at: datetime


class ConnectionTestResult(BaseModel):
    ok: bool
    latency_ms: float
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class NotificationTestResult(BaseModel):
    ok: bool
    channel: str
    message: str


class DiscoveredCamera(BaseModel):
    id: str
    name: str
    stream_url: str
    zone: str
    vendor: str | None = None


class AnalyticsSummary(BaseModel):
    total_skus: int
    active_alerts: int
    events_today: int
    avg_accuracy: float
    auto_pos_generated: int
    revenue_saved_estimate: float


class EventSeriesPoint(BaseModel):
    bucket: str
    total: int
    critical: int = 0
    warning: int = 0
    info: int = 0


class EventTimeSeries(BaseModel):
    items: list[EventSeriesPoint]


class AccuracyPoint(BaseModel):
    date: str
    accuracy: float


class AccuracyTrend(BaseModel):
    items: list[AccuracyPoint]


class HeatmapCell(BaseModel):
    zone: str
    count: int
    intensity: float


class ZoneHeatmapData(BaseModel):
    items: list[HeatmapCell]


class AlertTrendItem(BaseModel):
    date: str
    total: int
    by_type: dict[str, int]


class AlertTrend(BaseModel):
    items: list[AlertTrendItem]


class StockoutAnalysis(BaseModel):
    prevented_events: int
    cost_saved: float
    stockout_rate: float


class VendorPerformanceItem(BaseModel):
    vendor_name: str
    on_time_delivery_rate: float
    avg_lead_time_days: float
    po_count: int


class VendorPerformance(BaseModel):
    items: list[VendorPerformanceItem]


class CameraStatusResponse(CameraRead):
    detections_last_minute: int = 0
    avg_confidence: float = 0.0


class CameraDetail(CameraStatusResponse):
    current_detections: list[DetectionEventRead] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class AlertDetail(AlertRead):
    evidence_frame_url: str | None = None


class PODetail(PurchaseOrderRead):
    pass


ProductDetail.model_rebuild()
AlertRead.model_rebuild()
PurchaseOrderRead.model_rebuild()

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.crud import alert_crud, event_crud, po_crud, product_crud, vendor_crud
from app.db.schemas import (
    AccuracyPoint,
    AccuracyTrend,
    AlertTrend,
    AlertTrendItem,
    AnalyticsSummary,
    EventSeriesPoint,
    EventTimeSeries,
    StockoutAnalysis,
    VendorPerformance,
    VendorPerformanceItem,
    ZoneHeatmapData,
)


class AnalyticsService:
    async def get_summary(self, db: AsyncSession) -> AnalyticsSummary:
        total_skus = await product_crud.count(db)
        active_alerts = len(await alert_crud.get_active(db))
        events_today = len(await event_crud.get_recent(db, minutes=60 * 24))
        auto_pos_generated = await po_crud.count(db)
        revenue_saved_estimate = float(auto_pos_generated * 180.0)
        return AnalyticsSummary(
            total_skus=total_skus,
            active_alerts=active_alerts,
            events_today=events_today,
            avg_accuracy=97.3,
            auto_pos_generated=auto_pos_generated,
            revenue_saved_estimate=revenue_saved_estimate,
        )

    async def get_events(self, db: AsyncSession, days: int = 7) -> EventTimeSeries:
        start = datetime.utcnow() - timedelta(days=days)
        statement = (
            select(func.date(models.DetectionEvent.created_at), models.DetectionEvent.severity, func.count())
            .where(models.DetectionEvent.created_at >= start)
            .group_by(func.date(models.DetectionEvent.created_at), models.DetectionEvent.severity)
            .order_by(func.date(models.DetectionEvent.created_at))
        )
        result = await db.execute(statement)
        buckets: dict[str, EventSeriesPoint] = {}
        for bucket, severity, total in result.all():
            key = str(bucket)
            point = buckets.setdefault(key, EventSeriesPoint(bucket=key, total=0))
            point.total += int(total)
            setattr(point, severity.value, getattr(point, severity.value) + int(total))
        return EventTimeSeries(items=list(buckets.values()))

    async def get_accuracy_trend(self) -> AccuracyTrend:
        today = date.today()
        items = []
        for offset in range(29, -1, -1):
            accuracy = 91.0 + ((29 - offset) * 0.22)
            items.append(AccuracyPoint(date=(today - timedelta(days=offset)).isoformat(), accuracy=round(min(97.6, accuracy), 2)))
        return AccuracyTrend(items=items)

    async def get_heatmap(self, db: AsyncSession) -> ZoneHeatmapData:
        statement = select(models.DetectionEvent.zone, func.count()).group_by(models.DetectionEvent.zone)
        result = await db.execute(statement)
        rows = result.all()
        max_count = max((count for _, count in rows), default=1)
        items = [{"zone": zone, "count": int(count), "intensity": round(int(count) / max_count, 2)} for zone, count in rows]
        return ZoneHeatmapData(items=items)

    async def get_alert_trend(self, db: AsyncSession) -> AlertTrend:
        statement = (
            select(func.date(models.Alert.created_at), models.Alert.severity, func.count())
            .group_by(func.date(models.Alert.created_at), models.Alert.severity)
            .order_by(func.date(models.Alert.created_at))
        )
        result = await db.execute(statement)
        grouped: dict[str, AlertTrendItem] = {}
        for bucket, severity, total in result.all():
            key = str(bucket)
            item = grouped.setdefault(key, AlertTrendItem(date=key, total=0, by_type={}))
            item.total += int(total)
            item.by_type[severity.value] = int(total)
        return AlertTrend(items=list(grouped.values()))

    async def get_stockouts(self, db: AsyncSession) -> StockoutAnalysis:
        prevented = await alert_crud.count(db, filters={"status": models.AlertStatus.AUTO_RESOLVED})
        return StockoutAnalysis(prevented_events=prevented, cost_saved=float(prevented * 275.0), stockout_rate=0.08)

    async def get_vendor_performance(self, db: AsyncSession) -> VendorPerformance:
        vendors = await vendor_crud.get_multi(db, limit=100)
        items = []
        for vendor in vendors:
            po_count = await po_crud.count(db, filters={"vendor_id": vendor.id})
            items.append(
                VendorPerformanceItem(
                    vendor_name=vendor.name,
                    on_time_delivery_rate=0.92,
                    avg_lead_time_days=float(vendor.lead_time_days),
                    po_count=po_count,
                )
            )
        return VendorPerformance(items=items)


analytics_service = AnalyticsService()

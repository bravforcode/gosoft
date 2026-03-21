from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import AccuracyTrend, AlertTrend, AnalyticsSummary, EventTimeSeries, StockoutAnalysis, VendorPerformance, ZoneHeatmapData
from app.services.analytics_service import analytics_service


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> AnalyticsSummary:
    return await analytics_service.get_summary(db)


@router.get("/events", response_model=EventTimeSeries)
async def get_events(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> EventTimeSeries:
    return await analytics_service.get_events(db)


@router.get("/accuracy", response_model=AccuracyTrend)
async def get_accuracy(_: User = Depends(get_current_user)) -> AccuracyTrend:
    return await analytics_service.get_accuracy_trend()


@router.get("/heatmap", response_model=ZoneHeatmapData)
async def get_heatmap(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> ZoneHeatmapData:
    return await analytics_service.get_heatmap(db)


@router.get("/alerts", response_model=AlertTrend)
async def get_alert_trend(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> AlertTrend:
    return await analytics_service.get_alert_trend(db)


@router.get("/stockouts", response_model=StockoutAnalysis)
async def get_stockouts(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> StockoutAnalysis:
    return await analytics_service.get_stockouts(db)


@router.get("/vendors", response_model=VendorPerformance)
async def get_vendor_performance(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> VendorPerformance:
    return await analytics_service.get_vendor_performance(db)

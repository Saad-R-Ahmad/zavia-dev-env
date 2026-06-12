"""Metrics API routes."""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from api.deps import DBDep
from src.uns.crud import get_all_metrics, get_metric_by_id
from src.postgresql.models import Metric

router = APIRouter()


class MetricResponse(BaseModel):
    """Metric response model."""
    id: str
    name: str
    value: Optional[str | int | float | bool] = None
    device_id: Optional[str] = None
    node_id: Optional[str] = None
    dataType: Optional[int] = None
    dataType_name: Optional[str] = None
    alias: Optional[str] = None
    unit: Optional[str] = None
    quality: Optional[str] = None
    timestamp: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[MetricResponse])
async def list_metrics(
    db: DBDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all metrics with pagination."""
    try:
        metrics = get_all_metrics(db)
        # Convert ORM objects to dicts
        metric_dicts = [m.to_dict() for m in metrics]
        return metric_dicts[skip : skip + limit]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching metrics: {str(e)}"
        )


@router.get("/{metric_id}", response_model=MetricResponse)
async def get_metric(metric_id: str, db: DBDep):
    """Get a specific metric by ID."""
    try:
        metric = get_metric_by_id(db, metric_id)
        if not metric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metric with ID {metric_id} not found"
            )
        return metric.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching metric: {str(e)}"
        )
    
@router.delete("/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_metric(metric_id: str, db: DBDep):
    """Delete a specific metric by ID."""
    try:
        metric = get_metric_by_id(db, metric_id)
        if not metric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metric with ID {metric_id} not found"
            )
        db.delete(metric)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting metric: {str(e)}"
        )

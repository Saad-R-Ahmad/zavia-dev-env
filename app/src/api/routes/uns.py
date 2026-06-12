"""UNS hierarchy API routes."""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional, Any
from pydantic import BaseModel
from api.deps import DBDep
from src.uns.crud import get_all_groups

router = APIRouter()


class MetricDetail(BaseModel):
    """Detailed metric information."""
    id: str
    name: str
    alias: str
    value: Optional[Any] = None
    dataType_name: str
    unit: str
    quality: str
    timestamp: Optional[str] = None


class DeviceDetail(BaseModel):
    """Detailed device information."""
    id: str
    name: str
    metrics: List[MetricDetail]


class NodeDetail(BaseModel):
    """Detailed node information."""
    id: str
    name: str
    devices: List[DeviceDetail]
    metrics: List[MetricDetail]


class GroupDetail(BaseModel):
    """Detailed group information."""
    id: str
    name: str
    nodes: List[NodeDetail]


class UNSHierarchy(BaseModel):
    """Complete UNS hierarchy."""
    groups: List[GroupDetail]


@router.get("/", response_model=UNSHierarchy)
async def get_uns_hierarchy(db: DBDep):
    """Return the complete UNS hierarchy using nested models."""
    try:
        groups = get_all_groups(db)
        return {"groups": groups}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching UNS hierarchy: {str(e)}"
        )

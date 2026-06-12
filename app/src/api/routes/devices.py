"""Devices API routes."""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional,Any
from pydantic import BaseModel
from api.deps import DBDep
from src.uns.crud import (
    get_all_devices,
    get_device_by_id,
    get_devices_for_node,
)
from src.postgresql.models import Device

router = APIRouter()


class MetricInfo(BaseModel):
    """Metric info for device response."""
    id: str
    name: str
    alias: str
    value: Any
    data_type: Optional[str] = None


class DeviceResponse(BaseModel):
    """Device response model (nested)."""
    id: str
    name: str
    metrics: List[MetricInfo]


@router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    db: DBDep,
    skip: int = 0,
    limit: int = 100,
    node_id: Optional[str] = None,
    group_name: Optional[str] = None,
    node_name: Optional[str] = None
):
    """Get all devices with optional filtering by node."""
    try:
        if node_id or (group_name and node_name):
            devices = get_devices_for_node(db, node_id=node_id, group_name=group_name, node_name=node_name)
        else:
            devices = get_all_devices(db)

        result = []
        for device in devices[skip : skip + limit]:
            metrics = [MetricInfo(id=m["id"], name=m["name"], alias=m.get("alias", ""), value=m.get("value"), data_type=m.get("dataType_name")) for m in device.get("metrics", [])]
            result.append(DeviceResponse(
                id=device["id"],
                name=device["name"],
                metrics=metrics
            ))
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching devices: {str(e)}"
        )


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, db: DBDep):
    """Get a specific device by ID."""
    try:
        device_obj = get_device_by_id(db, device_id)
        if not device_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with ID {device_id} not found"
            )
        device = device_obj.to_dict()
        metrics = [MetricInfo(id=m["id"], name=m["name"], alias=m.get("alias", ""), value=m.get("value"), data_type=m.get("dataType_name")) for m in device.get("metrics", [])]
        return DeviceResponse(
            id=device["id"],
            name=device["name"],
            metrics=metrics
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching device: {str(e)}"
        )


@router.get("/{device_id}/metrics", response_model=List[MetricInfo])
async def get_device_metrics(device_id: str, db: DBDep):
    """Get all metrics for a specific device."""
    try:
        device = get_device_by_id(db, device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with ID {device_id} not found"
            )
        return [MetricInfo(id=m.id, name=m.name, alias=m.alias, value=m.value, data_type=m.dataType_name) for m in device.metrics]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching device metrics: {str(e)}"
        )
    
# routes for delete and update devices:
@router.delete("/{device_id}")
async def delete_device(device_id: str, db: DBDep):
    """Delete a specific device by ID."""
    try:
        device = get_device_by_id(db, device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device with ID {device_id} not found"
            )
        db.delete(device)
        db.commit()
        return {"detail": f"Device with ID {device_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting device: {str(e)}"
        )

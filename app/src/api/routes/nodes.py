"""Nodes API routes."""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from api.deps import DBDep
from src.uns.crud import get_all_nodes, get_node_by_id, get_nodes_for_group
from src.postgresql.models import Node

router = APIRouter()


class DeviceInfo(BaseModel):
    """Device info for node response."""
    id: str
    name: str


class MetricInfo(BaseModel):
    """Metric info for node response."""
    id: str
    name: str
    alias: str


class NodeResponse(BaseModel):
    """Node response model (nested)."""
    id: str
    name: str
    devices: List[DeviceInfo]
    metrics: List[MetricInfo]


@router.get("/", response_model=List[NodeResponse])
async def list_nodes(
    db: DBDep,
    skip: int = 0,
    limit: int = 100,
    group_id: Optional[str] = None,
    group_name: Optional[str] = None
):
    """Get all nodes with optional filtering by group."""
    try:
        if group_id or group_name:
            nodes = get_nodes_for_group(db, group_id=group_id, group_name=group_name)
        else:
            nodes = get_all_nodes(db)

        # Transform dicts to response models
        result = []
        for node in nodes[skip : skip + limit]:
            devices = [DeviceInfo(id=d["id"], name=d["name"]) for d in node.get("devices", [])]
            metrics = [MetricInfo(id=m["id"], name=m["name"], alias=m.get("alias", "")) for m in node.get("metrics", [])]
            result.append(NodeResponse(
                id=node["id"],
                name=node["name"],
                devices=devices,
                metrics=metrics
            ))
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching nodes: {str(e)}"
        )


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(node_id: str, db: DBDep):
    """Get a specific node by ID."""
    try:
        node_obj = get_node_by_id(db, node_id)
        if not node_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID {node_id} not found"
            )
        node = node_obj.to_dict()
        devices = [DeviceInfo(id=d["id"], name=d["name"]) for d in node.get("devices", [])]
        metrics = [MetricInfo(id=m["id"], name=m["name"], alias=m.get("alias", "")) for m in node.get("metrics", [])]
        return NodeResponse(
            id=node["id"],
            name=node["name"],
            devices=devices,
            metrics=metrics
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching node: {str(e)}"
        )


@router.get("/{node_id}/devices")
async def get_node_devices(node_id: str, db: DBDep):
    """Get all devices for a specific node."""
    try:
        node = get_node_by_id(db, node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID {node_id} not found"
            )
        return [d.to_dict() for d in node.devices]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching node devices: {str(e)}"
        )


@router.get("/{node_id}/metrics")
async def get_node_metrics(node_id: str, db: DBDep):
    """Get all metrics for a specific node."""
    try:
        node = get_node_by_id(db, node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID {node_id} not found"
            )
        return [m.to_dict() for m in node.metrics]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching node metrics: {str(e)}"
        )
    
@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(node_id: str, db: DBDep):
    """Delete a specific node by ID."""
    try:
        node = get_node_by_id(db, node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID {node_id} not found"
            )
        db.delete(node)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting node: {str(e)}"
        )

"""MQTT connections API routes."""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid
import json
from sqlalchemy.orm import Session
from api.deps import DBDep
from src.uns.crud import (
    get_all_mqtt_connections,
    get_mqtt_connection_record_by_id,
    get_uns_mqtt_connection,
    delete_mqtt_connection_record,
    update_mqtt_connection_in_redis_db,
    create_mqtt_connection
)
from uns.mqtt_manager import mqtt_client_connect, subscribe_to_all_topics, stop_mqtt_client
from postgresql.models import MQTTConnection, SubscriptionTopic

router = APIRouter()


class SubscriptionTopicRequest(BaseModel):
    """Subscription topic request model."""
    topic: str
    qos: str = "0:0"
    enabled: bool = True
    data_specification: str


class SubscriptionTopicResponse(BaseModel):
    """Subscription topic response model."""
    topic: str
    qos: str
    enabled: bool
    data_specification: str

    class Config:
        from_attributes = True


class MQTTConnectionResponse(BaseModel):
    """MQTT connection response model."""
    id: str
    mqtt_broker: str
    mqtt_port: int
    mqtt_client_id: str
    mqtt_keepalive: int
    mqtt_tls_enabled: bool
    mqtt_clean_session: bool
    is_uns_broker: bool
    is_connected: bool
    is_enabled: bool
    subscription_topics: List[SubscriptionTopicResponse]

    class Config:
        from_attributes = True


class MQTTConnectionDetail(MQTTConnectionResponse):
    """Detailed MQTT connection response with sensitive fields."""
    mqtt_username: str
    mqtt_tls_ca_certs: Optional[str] = None
    mqtt_tls_certfile: Optional[str] = None
    mqtt_tls_keyfile: Optional[str] = None
    mqtt_protocol_version: int
    mqtt_reconnect_delay: int
    mqtt_reconnect_delay_max: int
    mqtt_will_topic: str
    mqtt_will_payload: str
    mqtt_will_qos: int
    mqtt_will_retain: bool


class MQTTConnectionCreate(BaseModel):
    """MQTT connection creation model."""
    mqtt_broker: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_client_id: str
    mqtt_keepalive: int = 60
    mqtt_tls_enabled: bool = False
    mqtt_tls_ca_certs: Optional[str] = None
    mqtt_tls_certfile: Optional[str] = None
    mqtt_tls_keyfile: Optional[str] = None
    mqtt_tls_version: Optional[int] = None
    mqtt_tls_ciphers: Optional[str] = None
    mqtt_clean_session: bool = True
    mqtt_protocol_version: int = 4
    mqtt_reconnect_delay: int = 5
    mqtt_reconnect_delay_max: int = 120
    mqtt_reconnect_delay_jitter: float = 0.1
    mqtt_max_inflight_messages: int = 20
    mqtt_max_queued_messages: int = 1000
    mqtt_message_timeout: int = 60
    mqtt_will_topic: str
    mqtt_will_payload: str
    mqtt_will_qos: int = 1
    mqtt_will_retain: bool = True
    subscription_topics: List[SubscriptionTopicRequest] = []
    is_uns_broker: bool = False


class MQTTConnectionUpdate(BaseModel):
    """MQTT connection update model (all fields optional)."""
    mqtt_broker: Optional[str] = None
    mqtt_port: Optional[int] = None
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_client_id: Optional[str] = None
    mqtt_keepalive: Optional[int] = None
    mqtt_tls_enabled: Optional[bool] = None
    mqtt_tls_ca_certs: Optional[str] = None
    mqtt_tls_certfile: Optional[str] = None
    mqtt_tls_keyfile: Optional[str] = None
    mqtt_tls_version: Optional[int] = None
    mqtt_tls_ciphers: Optional[str] = None
    mqtt_clean_session: Optional[bool] = None
    mqtt_protocol_version: Optional[int] = None
    mqtt_reconnect_delay: Optional[int] = None
    mqtt_reconnect_delay_max: Optional[int] = None
    mqtt_reconnect_delay_jitter: Optional[float] = None
    mqtt_max_inflight_messages: Optional[int] = None
    mqtt_max_queued_messages: Optional[int] = None
    mqtt_message_timeout: Optional[int] = None
    mqtt_will_topic: Optional[str] = None
    mqtt_will_payload: Optional[str] = None
    mqtt_will_qos: Optional[int] = None
    mqtt_will_retain: Optional[bool] = None
    subscription_topics: Optional[List[SubscriptionTopicRequest]] = None
    is_uns_broker: Optional[bool] = None


@router.get("/", response_model=List[MQTTConnectionResponse])
async def list_mqtt_connections(db: DBDep):
    """Get all MQTT connections (without passwords)."""
    try:
        connections = get_all_mqtt_connections(db)
        return connections
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching MQTT connections: {str(e)}"
        )


@router.get("/uns", response_model=MQTTConnectionResponse)
async def get_uns_connection(db: DBDep):
    """Get the UNS broker connection."""
    try:
        connection = get_uns_mqtt_connection(db)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="UNS broker connection not found"
            )
        return connection
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching UNS connection: {str(e)}"
        )


@router.get("/{connection_id}", response_model=MQTTConnectionDetail)
async def get_mqtt_connection(connection_id: str, db: DBDep):
    """Get a specific MQTT connection by ID."""
    try:
        connection = get_mqtt_connection_record_by_id(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        return connection
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching MQTT connection: {str(e)}"
        )


@router.post("/{connection_id}/stop")
async def stop_mqtt_connection_endpoint(connection_id: str, db: DBDep):
    """Stop/disconnect an MQTT client without deleting the connection."""
    try:
        connection = get_mqtt_connection_record_by_id(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        
        connection.is_enabled = False  # Also mark as disabled to prevent auto-reconnect
        result = stop_mqtt_client(mqtt_connection_record=connection)
        
        if result:
            # Update is_connected status in DB
            connection.is_connected = False
            db.commit()
            return {"message": f"MQTT client {connection_id} stopped successfully"}
        else:
            return {"message": f"MQTT client {connection_id} did not disconnect (it may not have been connected)"}
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping MQTT client: {str(e)}"
        )


@router.post("/{connection_id}/start")
async def start_mqtt_connection_endpoint(connection_id: str, db: DBDep):
    """Start/connect an MQTT client."""
    try:
        connection = get_mqtt_connection_record_by_id(db, connection_id)
        connection.is_enabled = True  # Mark as enabled to allow connection
        db.commit()
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        
        mqtt_client = mqtt_client_connect(mqtt_connection_record=connection)
        if mqtt_client.is_connected():  # type: ignore[attr-defined]
            # subscribe_to_all_topics(mqtt_connection_record=connection) This is handled by the on_connect callback now, so we don't need to call it here
            return {"message": f"MQTT client {connection_id} started and connected successfully"}
        else:
            return {"message": f"MQTT client {connection_id} started, connecting..."}
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting MQTT client: {str(e)}"
        )


@router.delete("/{connection_id}")
async def delete_mqtt_connection(connection_id: str, db: DBDep):
    """Delete an MQTT connection by ID."""
    try:
        # Get the connection before deleting to stop the client
        connection = get_mqtt_connection_record_by_id(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        
        # Stop the MQTT client first
        stop_mqtt_client(mqtt_connection_record=connection)
        
        # Delete from database
        success = delete_mqtt_connection_record(db, connection_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        return {"message": f"MQTT connection {connection_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting MQTT connection: {str(e)}"
        )


@router.get("/{connection_id}/subscriptions", response_model=List[SubscriptionTopicResponse])
async def get_connection_subscriptions(connection_id: str, db: DBDep):
    """Get all subscription topics for a specific MQTT connection."""
    try:
        connection = get_mqtt_connection_record_by_id(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        return connection.subscription_topics
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching subscriptions: {str(e)}"
        )


@router.post("/", response_model=MQTTConnectionDetail, status_code=status.HTTP_201_CREATED)
async def create_mqtt_connection_endpoint(connection_data: MQTTConnectionCreate, db: DBDep):
    """Create a new MQTT connection."""
    try:
        # Prepare subscription topics data
        subscription_topics_data = [
            {
                "topic": sub.topic,
                "qos": sub.qos,
                "enabled": sub.enabled,
                "data_specification": sub.data_specification
            }
            for sub in (connection_data.subscription_topics or [])
        ]
        
        # Create new connection using CRUD
        new_connection = create_mqtt_connection(
            session=db,
            mqtt_broker=connection_data.mqtt_broker,
            mqtt_port=connection_data.mqtt_port,
            mqtt_username=connection_data.mqtt_username,
            mqtt_password=connection_data.mqtt_password,
            mqtt_client_id=connection_data.mqtt_client_id,
            mqtt_keepalive=connection_data.mqtt_keepalive,
            mqtt_tls_enabled=connection_data.mqtt_tls_enabled,
            mqtt_tls_ca_certs=connection_data.mqtt_tls_ca_certs,
            mqtt_tls_certfile=connection_data.mqtt_tls_certfile,
            mqtt_tls_keyfile=connection_data.mqtt_tls_keyfile,
            mqtt_protocol_version=connection_data.mqtt_protocol_version,
            mqtt_reconnect_delay=connection_data.mqtt_reconnect_delay,
            mqtt_reconnect_delay_max=connection_data.mqtt_reconnect_delay_max,
            mqtt_will_topic=connection_data.mqtt_will_topic,
            mqtt_will_payload=connection_data.mqtt_will_payload,
            mqtt_will_qos=connection_data.mqtt_will_qos,
            mqtt_will_retain=connection_data.mqtt_will_retain,
            is_uns_broker=connection_data.is_uns_broker,
            mqtt_clean_session=connection_data.mqtt_clean_session,
            subscription_topics=subscription_topics_data
        )
        
        # Start the MQTT client for the new connection
        mqtt_client = mqtt_client_connect(mqtt_connection_record=new_connection)
        if mqtt_client.is_connected():  # type: ignore[attr-defined]
            subscribe_to_all_topics(mqtt_connection_record=new_connection)
        
        return new_connection
    
    except Exception as e:
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating MQTT connection: {str(e)}"
        )


@router.put("/{connection_id}", response_model=MQTTConnectionDetail)
async def update_mqtt_connection(
    connection_id: str,
    connection_data: MQTTConnectionUpdate,
    db: DBDep
):
    """Update an existing MQTT connection."""
    try:
        # Get existing connection
        connection = get_mqtt_connection_record_by_id(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        
        # Build update data (only include provided fields)
        update_data = {}
        for field, value in connection_data.model_dump(exclude_unset=True).items():
            if field != "subscription_topics":
                update_data[field] = value
        
        # Update the connection
        updated_connection = update_mqtt_connection_in_redis_db(db, connection, update_data)
        
        # Handle subscription topics separately if provided
        if connection_data.subscription_topics is not None:
            # Clear existing subscription topics
            for sub in connection.subscription_topics:
                db.delete(sub)
            
            # Add new subscription topics
            for sub_data in connection_data.subscription_topics:
                new_sub = SubscriptionTopic(
                    id=str(uuid.uuid4()),
                    mqtt_connection_id=connection.id,
                    topic=sub_data.topic,
                    qos=sub_data.qos,
                    enabled=sub_data.enabled,
                    data_specification=sub_data.data_specification
                )
                db.add(new_sub)
            db.commit()
            db.refresh(updated_connection)
        
        # Reconnect the client if connection params changed (will use config hash to detect changes)
        mqtt_client = mqtt_client_connect(mqtt_connection_record=updated_connection)
        if mqtt_client.is_connected():  # type: ignore[attr-defined]
            subscribe_to_all_topics(mqtt_connection_record=updated_connection)
        
        return updated_connection
    
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating MQTT connection: {str(e)}"
        )

@router.post("/{connection_id}/restart")
async def restart_mqtt_connection(connection_id: str, db: DBDep):
    """Restart an MQTT client by stopping and starting it again."""
    try:
        connection = get_mqtt_connection_record_by_id(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        
        # Stop the MQTT client first
        stop_mqtt_client(mqtt_connection_record=connection)
        
        # Start the MQTT client again
        mqtt_client = mqtt_client_connect(mqtt_connection_record=connection)
        if mqtt_client.is_connected():  # type: ignore[attr-defined]
            subscribe_to_all_topics(mqtt_connection_record=connection)
            return {"message": f"MQTT client {connection_id} restarted and connected successfully"}
        else:
            return {"message": f"MQTT client {connection_id} restarted, connecting..."}
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restarting MQTT client: {str(e)}"
        )
    
@router.delete("/{connection_id}")
async def delete_mqtt_connection(connection_id: str, db: DBDep):
    """Delete an MQTT connection by ID."""
    try:
        # Get the connection before deleting to stop the client
        connection = get_mqtt_connection_record_by_id(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        
        # Stop the MQTT client first
        stop_mqtt_client(mqtt_connection_record=connection)
        
        # Delete from database
        success = delete_mqtt_connection_record(db, connection_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        return {"message": f"MQTT connection {connection_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting MQTT connection: {str(e)}"
        )
    
@router.delete("/{connection_id}/subscriptions/{topic_id}")
async def delete_subscription_topic(connection_id: str, topic_id: str, db: DBDep):
    """Delete a specific subscription topic from an MQTT connection."""
    try:
        connection = get_mqtt_connection_record_by_id(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MQTT connection with ID {connection_id} not found"
            )
        
        subscription_topic = db.query(SubscriptionTopic).filter_by(id=topic_id, mqtt_connection_id=connection_id).first()
        if not subscription_topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription topic with ID {topic_id} not found for connection {connection_id}"
            )
        
        db.delete(subscription_topic)
        db.commit()
        
        # Reconnect the client to update subscriptions
        mqtt_client = mqtt_client_connect(mqtt_connection_record=connection)
        if mqtt_client.is_connected():  # type: ignore[attr-defined]
            subscribe_to_all_topics(mqtt_connection_record=connection)
        
        return {"message": f"Subscription topic {topic_id} deleted successfully from connection {connection_id}"}
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting subscription topic: {str(e)}"
        )
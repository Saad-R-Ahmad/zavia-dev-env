"""SQLAlchemy models for PostgreSQL."""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from datetime import datetime
import uuid
from typing import List

Base = declarative_base()


class Group(Base):
    __tablename__ = "groups"
    
    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # type: ignore[assignment]
    name: Mapped[str] = Column(String, nullable=False)  # type: ignore[assignment]
    
    nodes: Mapped[List["Node"]] = relationship("Node", back_populates="group", cascade="all, delete-orphan")  # type: ignore[assignment]
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes]
        }


class Node(Base):
    __tablename__ = "nodes"
    
    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # type: ignore[assignment]
    name: Mapped[str] = Column(String, nullable=False)  # type: ignore[assignment]
    group_name: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    group_id: Mapped[str | None] = Column(String, ForeignKey("groups.id"))  # type: ignore[assignment]
    
    group: Mapped["Group"] = relationship("Group", back_populates="nodes")  # type: ignore[assignment]
    devices: Mapped[List["Device"]] = relationship("Device", back_populates="node", cascade="all, delete-orphan")  # type: ignore[assignment]
    metrics: Mapped[List["Metric"]] = relationship("Metric", back_populates="node", cascade="all, delete-orphan")  # type: ignore[assignment]

    command_topic : Mapped[str | None] = Column(String)  # type: ignore[assignment]
    
    def to_dict(self):
        return {
            "id": self.id,
            "group_name": self.group_name,
            "name": self.name,
            "devices": [device.to_dict() for device in self.devices],
            "metrics": [metric.to_dict() for metric in self.metrics],
            "command_topic": self.command_topic
        }


class Device(Base):
    __tablename__ = "devices"
    
    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # type: ignore[assignment]
    name: Mapped[str] = Column(String, nullable=False)  # type: ignore[assignment]
    node_name: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    node_id: Mapped[str | None] = Column(String, ForeignKey("nodes.id"))  # type: ignore[assignment]
    group_id: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    
    node: Mapped["Node"] = relationship("Node", back_populates="devices")  # type: ignore[assignment]
    metrics: Mapped[List["Metric"]] = relationship("Metric", back_populates="device", cascade="all, delete-orphan")  # type: ignore[assignment]

    command_topic : Mapped[str | None] = Column(String)  # type: ignore[assignment]
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "command_topic": self.command_topic
        }


class Metric(Base):
    __tablename__ = "metrics"
    
    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # type: ignore[assignment]
    device_id: Mapped[str | None] = Column(String, ForeignKey("devices.id"))  # type: ignore[assignment]
    node_id: Mapped[str | None] = Column(String, ForeignKey("nodes.id"))  # type: ignore[assignment]
    name: Mapped[str] = Column(String, nullable=False)  # type: ignore[assignment]
    value: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    timestamp: Mapped[datetime | None] = Column(DateTime, nullable=True)  # type: ignore[assignment]
    dataType: Mapped[int | None] = Column(Integer)  # type: ignore[assignment]
    dataType_name: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    alias: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    unit: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    quality: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    
    device: Mapped["Device"] = relationship("Device", back_populates="metrics")  # type: ignore[assignment]
    node: Mapped["Node"] = relationship("Node", back_populates="metrics")  # type: ignore[assignment]
    
    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "node_id": self.node_id,
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "dataType": self.dataType,
            "dataType_name": self.dataType_name,
            "alias": self.alias,
            "unit": self.unit,
            "quality": self.quality
        }


class SubscriptionTopic(Base):
    __tablename__ = "subscription_topics"
    
    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # type: ignore[assignment]
    mqtt_connection_id: Mapped[str | None] = Column(String, ForeignKey("mqtt_connections.id"))  # type: ignore[assignment]
    topic: Mapped[str] = Column(String, nullable=False)  # type: ignore[assignment]
    qos: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    enabled: Mapped[bool] = Column(Boolean, default=True)  # type: ignore[assignment]
    data_specification: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    
    mqtt_connection: Mapped["MQTTConnection"] = relationship("MQTTConnection", back_populates="subscription_topics")  # type: ignore[assignment]
    
    def to_dict(self):
        return {
            "id": self.id,
            "topic": self.topic,
            "qos": self.qos,
            "enabled": self.enabled,
            "data_specification": self.data_specification
        }


class MQTTConnection(Base):
    __tablename__ = "mqtt_connections"
    
    id: Mapped[str] = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))  # type: ignore[assignment]
    mqtt_broker: Mapped[str] = Column(String, nullable=False)  # type: ignore[assignment]
    mqtt_port: Mapped[int] = Column(Integer, nullable=False)  # type: ignore[assignment]
    mqtt_username: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    mqtt_password: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    mqtt_client_id: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    mqtt_keepalive: Mapped[int] = Column(Integer, default=60)  # type: ignore[assignment]
    mqtt_tls_enabled: Mapped[bool] = Column(Boolean, default=False)  # type: ignore[assignment]
    mqtt_tls_ca_certs: Mapped[str | None] = Column(String, nullable=True)  # type: ignore[assignment]
    mqtt_tls_certfile: Mapped[str | None] = Column(String, nullable=True)  # type: ignore[assignment]
    mqtt_tls_keyfile: Mapped[str | None] = Column(String, nullable=True)  # type: ignore[assignment]
    mqtt_tls_version: Mapped[int | None] = Column(Integer, nullable=True)  # type: ignore[assignment]
    mqtt_tls_ciphers: Mapped[str | None] = Column(String, nullable=True)  # type: ignore[assignment]
    mqtt_clean_session: Mapped[bool] = Column(Boolean, default=True)  # type: ignore[assignment]
    mqtt_protocol_version: Mapped[int] = Column(Integer, default=4)  # type: ignore[assignment]
    mqtt_reconnect_delay: Mapped[int] = Column(Integer, default=5)  # type: ignore[assignment]
    mqtt_reconnect_delay_max: Mapped[int] = Column(Integer, default=120)  # type: ignore[assignment]
    mqtt_reconnect_delay_jitter: Mapped[float] = Column(Float, default=0.1)  # type: ignore[assignment]
    mqtt_max_inflight_messages: Mapped[int] = Column(Integer, default=20)  # type: ignore[assignment]
    mqtt_max_queued_messages: Mapped[int] = Column(Integer, default=1000)  # type: ignore[assignment]
    mqtt_message_timeout: Mapped[int] = Column(Integer, default=60)  # type: ignore[assignment]
    mqtt_will_topic: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    mqtt_will_payload: Mapped[str | None] = Column(String)  # type: ignore[assignment]
    mqtt_will_qos: Mapped[int] = Column(Integer, default=1)  # type: ignore[assignment]
    mqtt_will_retain: Mapped[bool] = Column(Boolean, default=True)  # type: ignore[assignment]
    is_uns_broker: Mapped[bool] = Column(Boolean, default=False)  # type: ignore[assignment]
    # Connection state tracking
    is_connected: Mapped[bool] = Column(Boolean, default=False)  # type: ignore[assignment]
    is_enabled: Mapped[bool] = Column(Boolean, default=True)  # type: ignore[assignment]
    
    subscription_topics: Mapped[List["SubscriptionTopic"]] = relationship("SubscriptionTopic", back_populates="mqtt_connection")  # type: ignore[assignment]
    
    def to_dict(self):
        return {
            "id": self.id,
            "mqtt_broker": self.mqtt_broker,
            "mqtt_port": self.mqtt_port,
            "mqtt_username": self.mqtt_username,
            "mqtt_password": self.mqtt_password,
            "mqtt_client_id": self.mqtt_client_id,
            "mqtt_keepalive": self.mqtt_keepalive,
            "mqtt_tls_enabled": self.mqtt_tls_enabled,
            "mqtt_tls_ca_certs": self.mqtt_tls_ca_certs,
            "mqtt_tls_certfile": self.mqtt_tls_certfile,
            "mqtt_tls_keyfile": self.mqtt_tls_keyfile,
            "mqtt_tls_version": self.mqtt_tls_version,
            "mqtt_tls_ciphers": self.mqtt_tls_ciphers,
            "mqtt_clean_session": self.mqtt_clean_session,
            "mqtt_protocol_version": self.mqtt_protocol_version,
            "mqtt_reconnect_delay": self.mqtt_reconnect_delay,
            "mqtt_reconnect_delay_max": self.mqtt_reconnect_delay_max,
            "mqtt_reconnect_delay_jitter": self.mqtt_reconnect_delay_jitter,
            "mqtt_max_inflight_messages": self.mqtt_max_inflight_messages,
            "mqtt_max_queued_messages": self.mqtt_max_queued_messages,
            "mqtt_message_timeout": self.mqtt_message_timeout,
            "mqtt_will_topic": self.mqtt_will_topic,
            "mqtt_will_payload": self.mqtt_will_payload,
            "mqtt_will_qos": self.mqtt_will_qos,
            "mqtt_will_retain": self.mqtt_will_retain,
            "is_uns_broker": self.is_uns_broker,
            "is_connected": self.is_connected,
            "is_enabled": self.is_enabled,
            "subscription_topics": [topic.to_dict() for topic in self.subscription_topics]
        }

"""
CRUD operations for UNS entities (Groups, Nodes, Devices, Metrics).
This module is a low-level data access layer with no dependencies on higher-level modules.
"""
import uuid
import logging
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from src.postgresql.models import Group, Node, Device, Metric, MQTTConnection, SubscriptionTopic
from src.uns.models import DeviceType
from src.uns.datatypes import MetricDataType

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


###########################################
## GROUP CRUD OPERATIONS ###################
############################################
def get_or_add_group(session: Session, group_name: str, group_id: str = "") -> Group:
	'''
	Get or add a group to the database
	'''
	# Prefer lookup by name; simplify and ignore id-based flow
	if group_name is not None:
		found_group = get_group_by_name(session, group_name)
		if found_group is not None:
			return found_group
	# Create a new group
	new_group = Group(
		id=str(uuid.uuid4()),
		name=group_name
	)
	session.add(new_group)
	session.commit()
	logger.debug(f"Created new group: {new_group}")
	return new_group


def get_group_by_id(session: Session, group_id: str) -> Group | None:
	return session.query(Group).filter(Group.id == group_id).first()


def get_group_by_name(session: Session, group_name: str) -> Group | None:
	return session.query(Group).filter(Group.name == group_name).first()


def get_all_groups(session: Session) -> list[dict]:
	"""Get all groups as nested dicts (groups -> nodes -> devices -> metrics)."""
	groups = session.query(Group).all()
	return [g.to_dict() for g in groups]

def get_uns_tree(session: Session) -> list[dict]:
	"""Return full UNS tree as nested dicts."""
	groups = session.query(Group).all()
	return [g.to_dict() for g in groups]


def update_group_in_db(session: Session, group: Group, data: dict) -> Group:
	'''Update group with new data and save to database'''
	for key, value in data.items():
		if hasattr(group, key):
			setattr(group, key, value)
	session.commit()
	session.refresh(group)
	return group

def delete_group(session: Session, group_id: str) -> bool:
	'''Delete a group by its ID'''
	group = get_group_by_id(session, group_id)
	if group is not None:
		session.delete(group)
		session.commit()
		logger.debug(f"Deleted group with ID: {group_id}")
		return True
	else:
		logger.debug(f"No group found with ID: {group_id}")
		return False


###########################################
## NODE CRUD OPERATIONS ###################
############################################
def get_or_add_node(session: Session, group_name: str, node_name: str, device_type:DeviceType, group_id: str = "", node_id: str = "") -> Node:
	'''
	Get or add a node to the database
	'''
	# Get or create the group first (name-based)
	group = get_or_add_group(session, group_name)
	
	# Prefer lookup by name within the group
	if node_name is not None:
		found_node = session.query(Node).filter(Node.name == node_name, Node.group_id == group.id).first()
		if found_node is not None:
			return found_node
	
	# Create a new node
	if device_type == DeviceType.Siemens_Databus:
		command_topic = command_topic = f"ie/d/j/simatic/v1/{group_name}/dp/w/{node_name}"
	elif device_type == DeviceType.SparkplugB:
		command_topic = f"spBv1.0/{group_name}/NCMD/{node_name}"
	else:
		command_topic = f""
	
	new_node = Node(
		id=str(uuid.uuid4()),
		name=node_name,
		group_id=group.id,
		group_name=group.name,
		command_topic=command_topic
	)
	session.add(new_node)
	session.commit()
	logger.debug(f"Created new node: {new_node}")
	return new_node


def get_node_by_id(session: Session, node_id: str) -> Node | None:
	return session.query(Node).filter(Node.id == node_id).first()


def get_node_by_name(session: Session, node_name: str) -> Node | None:
	return session.query(Node).filter(Node.name == node_name).first()


def get_all_nodes(session: Session) -> list[dict]:
	nodes = session.query(Node).all()
	return [n.to_dict() for n in nodes]

def get_nodes_for_group(session: Session, group_id: Optional[str] = None, group_name: Optional[str] = None) -> list[dict]:
	q = session.query(Node)
	if group_id:
		q = q.filter(Node.group_id == group_id)
	elif group_name:
		grp = get_group_by_name(session, group_name)
		if not grp:
			return []
		q = q.filter(Node.group_id == grp.id)
	nodes = q.all()
	return [n.to_dict() for n in nodes]


def update_node_in_db(session: Session, node: Node, data: dict) -> Node:
	'''Update node with new data and save to database'''
	for key, value in data.items():
		if hasattr(node, key):
			setattr(node, key, value)
	session.commit()
	session.refresh(node)
	return node

def delete_node(session: Session, node_id: str) -> bool:
	'''Delete a node by its ID'''
	node = get_node_by_id(session, node_id)
	if node is not None:
		session.delete(node)
		session.commit()
		logger.debug(f"Deleted node with ID: {node_id}")
		return True
	else:
		logger.debug(f"No node found with ID: {node_id}")
		return False


###########################################
## DEVICE CRUD OPERATIONS ###################
############################################
def get_or_add_device(session: Session, group_name: str, device_name: str, node_name: str,device_type: DeviceType, device_id: str | None = None, node_id: str | None = None) -> Device:
	'''
	Get or add a device to the database
	'''
	# Get or create the node first (which will also get or create the group)
	node = get_or_add_node(session, group_name, node_name,device_type)
	
	# Prefer lookup by name within the node
	if device_name is not None:
		found_device = session.query(Device).filter(Device.name == device_name, Device.node_id == node.id).first()
		if found_device is not None:
			return found_device
	
	# Create a new device
	if device_type == DeviceType.Siemens_Databus:
		command_topic = f"ie/d/j/simatic/v1/{group_name}/dp/w/{node_name}/{device_name}"
	elif device_type == DeviceType.SparkplugB:
		command_topic = f"spBv1.0/{group_name}/DCMD/{node_name}/{device_name}"
	else:
		command_topic = f""
	new_device = Device(
		id=str(uuid.uuid4()),
		name=device_name,
		node_id=node.id,
		command_topic=command_topic
	)
	session.add(new_device)
	session.commit()
	logger.debug(f"Created new device: {new_device}")
	return new_device


def get_device_by_name(session: Session, device_name: str) -> Device | None:
	return session.query(Device).filter(Device.name == device_name).first()


def get_device_by_id(session: Session, device_id: str) -> Device | None:
	return session.query(Device).filter(Device.id == device_id).first()


def get_all_devices(session: Session) -> list[dict]:
	"""Get all devices as nested dicts."""
	devices = session.query(Device).all()
	return [d.to_dict() for d in devices]

def get_devices_for_node(session: Session, node_id: Optional[str] = None, group_name: Optional[str] = None, node_name: Optional[str] = None) -> list[dict]:
	q = session.query(Device)
	if node_id:
		q = q.filter(Device.node_id == node_id)
	elif group_name and node_name:
		node = session.query(Node).join(Group).filter(Group.name == group_name, Node.name == node_name).first()
		if not node:
			return []
		q = q.filter(Device.node_id == node.id)
	
	devices = q.all()
	return [d.to_dict() for d in devices]


def update_device_in_db(session: Session, device: Device, data: dict) -> Device:
	'''Update device with new data and save to database'''
	for key, value in data.items():
		if hasattr(device, key):
			setattr(device, key, value)
	session.commit()
	session.refresh(device)
	return device

def delete_device(session: Session, device_id: str) -> bool:
	'''Delete a device by its ID'''
	device = get_device_by_id(session, device_id)
	if device is not None:
		session.delete(device)
		session.commit()
		logger.debug(f"Deleted device with ID: {device_id}")
		return True
	else:
		logger.debug(f"No device found with ID: {device_id}")
		return False


###########################################
## METRIC CRUD OPERATIONS ###################
############################################
def get_or_add_metric(session: Session, device: Device | Node, metric_name: str, metric_alias: str, data_type: MetricDataType, value: Any | None, timestamp: datetime | None, unit: str = "", quality: str = "") -> Metric:
	'''
	Get or add a metric to the database
	'''
	# Normalize timestamp to datetime
	if timestamp is None:
		ts = datetime.utcnow()
	elif isinstance(timestamp, (int, float)):
		ts = datetime.fromtimestamp(timestamp / 1000)
	else:
		ts = timestamp

	# Check if metric with alias already exists for this device
	existing_metric = get_device_metric_by_alias(session, device, metric_alias)
	if existing_metric is not None:
		# Update the value and timestamp if provided
		if value is not None:
			existing_metric.value = value
		if ts is not None:
			existing_metric.timestamp = ts
		session.commit()
		# logger.debug(f"Updated existing metric: {existing_metric}")
		return existing_metric
	
	# Create a new metric
	new_metric = Metric(
		id=str(uuid.uuid4()),
		name=metric_name,
		alias=metric_alias,
		value=value,
		timestamp=ts,
		dataType=data_type.value,
		dataType_name=data_type.name,
		unit=unit,
		quality=quality,
		device_id=device.id if isinstance(device, Device) else None,
		node_id=device.id if isinstance(device, Node) else None
	)
	session.add(new_metric)
	session.commit()
	return new_metric

def sync_device_metrics(session: Session, device: Device | Node, new_metrics: list[Metric]) -> list[Metric]:
	"""
	Synchronize device/node metrics with new metric list.
	Adds new metrics, keeps existing ones, and removes metrics no longer in the list.
	
	Args:
		session: SQLAlchemy session
		device: Device or Node to sync metrics for
		new_metrics: List of Metric objects to sync
	"""
	# Get current metrics from database
	if isinstance(device, Device):
		current_metrics = session.query(Metric).filter(Metric.device_id == device.id).all()
	else:
		current_metrics = session.query(Metric).filter(Metric.node_id == device.id).all()
	
	current_aliases = {m.alias for m in current_metrics}
	new_aliases = {m.alias for m in new_metrics}
	
	# Find metrics to remove (in current but not in new)
	aliases_to_remove = current_aliases - new_aliases
	metrics_to_delete = [m for m in current_metrics if m.alias in aliases_to_remove]

	#### Delete all existing metrics and re-add from new list (simpler logic, but less efficient)
	metrics_to_delete = current_metrics
	
	# Delete removed metrics
	for metric in metrics_to_delete:
		session.delete(metric)
		logger.debug(f"Deleted metric {metric.name} (alias: {metric.alias}) from {device.name}")
		session.commit()
	
	# Get or create metrics from new list
	synced_metrics = []
	for new_metric in new_metrics:
		metric = get_or_add_metric(
			session=session,
			device=device,
			metric_name=new_metric.name,
			metric_alias=new_metric.alias or new_metric.name,
			data_type=MetricDataType(new_metric.dataType) if new_metric.dataType else MetricDataType.Unknown,
			value=new_metric.value,
			timestamp=new_metric.timestamp,
			unit=new_metric.unit or '',
			quality=new_metric.quality or ''
		)
		synced_metrics.append(metric)
	
	session.commit()
	return synced_metrics


def get_device_metric_by_alias(session: Session, device: Device | Node, metric_alias: str) -> Metric | None:
	if isinstance(device, Device):
		return session.query(Metric).filter(
			and_(Metric.device_id == device.id, Metric.alias == metric_alias)
		).first()
	else:
		return session.query(Metric).filter(
			and_(Metric.node_id == device.id, Metric.alias == metric_alias)
		).first()


def get_metric_by_id(session: Session, metric_id: str) -> Metric | None:
	return session.query(Metric).filter(Metric.id == metric_id).first()

def get_group(session: Session, group_name: str) -> dict | None:
	grp = get_group_by_name(session, group_name)
	return grp.to_dict() if grp else None

def get_node(session: Session, group_name: str, node_name: str) -> dict | None:
	node = session.query(Node).join(Group).filter(Group.name == group_name, Node.name == node_name).first()
	return node.to_dict() if node else None

def get_device(session: Session, group_name: str, node_name: str, device_name: str) -> dict | None:
	dev = session.query(Device).join(Node).join(Group).filter(Group.name == group_name, Node.name == node_name, Device.name == device_name).first()
	return dev.to_dict() if dev else None

def get_metrics_for_node(session: Session, group_name: str, node_name: str) -> list[dict]:
	node = session.query(Node).join(Group).filter(Group.name == group_name, Node.name == node_name).first()
	if not node:
		return []
	metrics = session.query(Metric).filter(Metric.node_id == node.id).all()
	return [m.to_dict() for m in metrics]

def get_metrics_for_device(session: Session, group_name: str, node_name: str, device_name: str) -> list[dict]:
	dev = session.query(Device).join(Node).join(Group).filter(Group.name == group_name, Node.name == node_name, Device.name == device_name).first()
	if not dev:
		return []
	metrics = session.query(Metric).filter(Metric.device_id == dev.id).all()
	return [m.to_dict() for m in metrics]

def get_group_with_children(session: Session, group_id: str) -> dict | None:
	g = get_group_by_id(session, group_id)
	return g.to_dict_nested() if g else None

def get_node_with_children(session: Session, node_id: str) -> dict | None:
	n = get_node_by_id(session, node_id)
	return n.to_dict_nested() if n else None

def get_device_with_children(session: Session, device_id: str) -> dict | None:
	d = get_device_by_id(session, device_id)
	return d.to_dict_nested() if d else None

def get_all_metrics(session: Session) -> list[Metric]:
	"""Get all metrics from the database."""
	return session.query(Metric).all()


def update_metric_in_db(session: Session, metric: Metric, data: dict) -> Metric:
	'''Update metric with new data and save to database'''
	for key, value in data.items():
		if hasattr(metric, key):
			# Normalize timestamp ints/floats (ms) to datetime
			if key == 'timestamp' and isinstance(value, (int, float)):
				value = datetime.fromtimestamp(value / 1000)
			setattr(metric, key, value)
	session.commit()
	session.refresh(metric)
	return metric

def delete_metric(session: Session, metric_id: str) -> bool:
	'''Delete a metric by its ID'''
	metric = get_metric_by_id(session, metric_id)
	if metric is not None:
		session.delete(metric)
		session.commit()
		logger.debug(f"Deleted metric with ID: {metric_id}")
		return True
	else:
		logger.debug(f"No metric found with ID: {metric_id}")
		return False


###########################################
## MQTT CONNECTION CRUD OPERATIONS ###################
############################################
def get_mqtt_connection_record_by_id(session: Session, connection_id: str) -> MQTTConnection | None:
	"""Retrieve an MQTTConnection record by its ID."""
	connection = session.query(MQTTConnection).filter(MQTTConnection.id == connection_id).first()
	if connection is None:
		raise RuntimeError(f"No MQTTConnection record found with ID: {connection_id}")
	return connection


def update_mqtt_connection_in_redis_db(session: Session, connection: MQTTConnection, data: dict) -> MQTTConnection:
	'''Update MQTT connection with new data and save to database'''
	for key, value in data.items():
		if hasattr(connection, key):
			setattr(connection, key, value)
	session.commit()
	session.refresh(connection)
	return connection

def delete_mqtt_connection(session: Session, connection_id: str) -> bool:
	'''Delete an MQTT connection by its ID'''
	connection = get_mqtt_connection_record_by_id(session, connection_id)
	if connection is not None:
		session.delete(connection)
		session.commit()
		logger.debug(f"Deleted MQTT connection with ID: {connection_id}")
		return True
	else:
		logger.debug(f"No MQTT connection found with ID: {connection_id}")
		return False


def get_uns_mqtt_connection(session: Session) -> MQTTConnection | None:
	''' Retrieve the default UNS MQTT connection record '''
	return session.query(MQTTConnection).filter(MQTTConnection.is_uns_broker == True).first()


def get_all_mqtt_connections(session: Session) -> list[MQTTConnection]:
	"""Get all MQTT connections from the database."""
	return session.query(MQTTConnection).all()


def delete_mqtt_connection_record(session: Session, connection_id: str) -> bool:
	''' Delete an MQTT connection record by its ID '''
	mqtt_connection_record = get_mqtt_connection_record_by_id(session, connection_id)
	if mqtt_connection_record is not None:
		session.delete(mqtt_connection_record)
		session.commit()
		logger.debug(f"Deleted MQTT connection record with ID: {connection_id}")
		return True
	else:
		logger.debug(f"No MQTT connection record found with ID: {connection_id}")
		return False


def create_mqtt_connection(
	session: Session,
	mqtt_broker: str,
	mqtt_port: int,
	mqtt_username: str,
	mqtt_password: str,
	mqtt_client_id: str,
	mqtt_keepalive: int = 60,
	mqtt_tls_enabled: bool = False,
	mqtt_tls_ca_certs: str | None = None,
	mqtt_tls_certfile: str | None = None,
	mqtt_tls_keyfile: str | None = None,
	mqtt_protocol_version: int = 4,
	mqtt_reconnect_delay: int = 5,
	mqtt_reconnect_delay_max: int = 120,
	mqtt_will_topic: str | None = None,
	mqtt_will_payload: str | None = None,
	mqtt_will_qos: int = 0,
	mqtt_will_retain: bool = False,
	is_uns_broker: bool = False,
	mqtt_clean_session: bool = True,
	subscription_topics: list[dict] | None = None
) -> MQTTConnection:
	"""Create a new MQTT connection record."""
	connection = MQTTConnection(
		id=str(uuid.uuid4()),
		mqtt_broker=mqtt_broker,
		mqtt_port=mqtt_port,
		mqtt_username=mqtt_username,
		mqtt_password=mqtt_password,
		mqtt_client_id=mqtt_client_id,
		mqtt_keepalive=mqtt_keepalive,
		mqtt_tls_enabled=mqtt_tls_enabled,
		mqtt_tls_ca_certs=mqtt_tls_ca_certs,
		mqtt_tls_certfile=mqtt_tls_certfile,
		mqtt_tls_keyfile=mqtt_tls_keyfile,
		mqtt_protocol_version=mqtt_protocol_version,
		mqtt_reconnect_delay=mqtt_reconnect_delay,
		mqtt_reconnect_delay_max=mqtt_reconnect_delay_max,
		mqtt_will_topic=mqtt_will_topic,
		mqtt_will_payload=mqtt_will_payload,
		mqtt_will_qos=mqtt_will_qos,
		mqtt_will_retain=mqtt_will_retain,
		is_uns_broker=is_uns_broker,
		mqtt_clean_session=mqtt_clean_session
	)
	
	# Add subscription topics if provided
	if subscription_topics:
		for topic_data in subscription_topics:
			subscription_topic = SubscriptionTopic(
				id=str(uuid.uuid4()),
				mqtt_connection_id=connection.id,
				topic=topic_data.get('topic'),
				qos=topic_data.get('qos', '0:0'),
				enabled=topic_data.get('enabled', True),
				data_specification=topic_data.get('data_specification', '')
			)
			connection.subscription_topics.append(subscription_topic)

	# Persist the new connection and its subscription topics
	session.add(connection)
	session.commit()
	session.refresh(connection)
	return connection




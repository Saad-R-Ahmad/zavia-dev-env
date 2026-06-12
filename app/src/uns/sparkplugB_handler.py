import uuid
from .tahu.core.sparkplug_b import sparkplug_b_pb2,getNodeBirthPayload,addMetric,MetricDataType,getDdataPayload
from datetime import datetime
import logging
from src.postgresql import get_session
from src.postgresql.models import Metric, Node, Device
from src.uns.models import DeviceType, UNSMQTTMessage
from src.uns.datatypes import MetricDataType,get_default_value_for_datatype
from .crud import (
	update_device_in_db,
    get_or_add_device,
    get_or_add_node
)

logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def get_metric_value(metric, datatype:MetricDataType):
	"""
	Get the metric value based on the data type
	"""
	if datatype == MetricDataType.Int8:
		return metric.int_value
	elif datatype == MetricDataType.Int16:
		return metric.int_value
	elif datatype == MetricDataType.Int32:
		return metric.int_value
	elif datatype == MetricDataType.Int64:
		return metric.long_value
	elif datatype == MetricDataType.UInt8:
		return metric.int_value
	elif datatype == MetricDataType.UInt16:
		return metric.int_value
	elif datatype == MetricDataType.UInt32:
		return metric.int_value
	elif datatype == MetricDataType.UInt64:
		return metric.int_value
	elif datatype == MetricDataType.Float:
		return metric.float_value
	elif datatype == MetricDataType.Double:
		return metric.double_value
	elif datatype == MetricDataType.Boolean:
		return metric.boolean_value
	elif datatype == MetricDataType.String:
		return metric.string_value
	elif datatype == MetricDataType.DateTime:
		#TODO: get tz from application
		return datetime.fromtimestamp(metric.long_value/1000).isoformat()
	elif datatype == MetricDataType.Text:
		return metric.text_value
	elif datatype == MetricDataType.UUID:
		return metric.uuid_value
	elif datatype == MetricDataType.DataSet:
		return metric.dataset_value
	elif datatype == MetricDataType.Bytes:
		return metric.bytes_value
	elif datatype == MetricDataType.File:
		return metric.file_value
	else:
		logger.debug(f"Unknown data type: {datatype}")

def spb_topic_parser(message_topic: str) -> tuple[str, str, str, str]:
	"""
	Parse the Sparkplug B message and return the group id, node id, device id and message type
	"""
	group_name = ''
	node_name = ''
	message_type = ''
	device_name = ''
	tokens = message_topic.split('/')
	if len(tokens) > 1: group_name = tokens[1]
	if len(tokens) > 2: message_type = tokens[2]
	if len(tokens) > 3: node_name = tokens[3]
	if len(tokens) > 4: device_name = tokens[4]
	return group_name, message_type, node_name, device_name

def spb_metrics_parser_for_birth(device:Device|Node, inbound_payload)->list[Metric]:
	"""Parse Sparkplug B metrics for BIRTH messages and sync with device (removes old metrics)."""
	# SparkplugB timestamps are in ms; store raw ms, CRUD will normalize
	timestamp = datetime.fromtimestamp(inbound_payload.timestamp / 1000)
	
	# Create Metric objects for sync
	new_metrics = []
	for metric in inbound_payload.metrics:
		# Skip Template metrics (UDT definitions) - they are metadata, not data values
		# Templates contain nested structures that cause recursion during serialization
		metric_datatype = MetricDataType(metric.datatype)
		if metric_datatype == MetricDataType.Template:
			logger.debug(f"Skipping Template metric: {getattr(metric, 'name', 'unnamed')}")
			continue
		
		# Skip DataSet metrics as they can also cause serialization issues
		if metric_datatype == MetricDataType.DataSet:
			logger.debug(f"Skipping DataSet metric: {getattr(metric, 'name', 'unnamed')}")
			continue
			
		new_metric = Metric(
			id=str(uuid.uuid4()),
			device_id=device.id if isinstance(device, Device) else None,
			node_id=device.id if isinstance(device, Node) else None,
			name=getattr(metric, 'name', None),
			alias=str(getattr(metric, 'alias', metric.name)),
			dataType=metric_datatype.value,
			dataType_name=metric_datatype.name,
			value=get_metric_value(metric, metric_datatype),
			timestamp=timestamp,
			unit=getattr(metric, 'unit', ''),
			quality=getattr(metric, 'quality', 'GOOD')
		)
		new_metrics.append(new_metric)
	
	return new_metrics

def spb_metrics_parser_for_data(device:Device|Node, inbound_payload)->list[Metric]:
	"""Parse Sparkplug B metrics for DATA messages (only updates existing metrics, never creates new ones)."""
	metric_list : list[Metric] = []
	device_metrics = device.metrics if hasattr(device, 'metrics') else []
	
	# Normalize SparkplugB ms timestamp to datetime for updates
	timestamp = datetime.fromtimestamp(inbound_payload.timestamp / 1000)

	for metric in inbound_payload.metrics:
		inbound_metric_alias = str(getattr(metric, 'alias', None))
		metric_datatype = MetricDataType(metric.datatype)
		metric_name = getattr(metric, 'name', None)
		for device_metric in device_metrics:
			if device_metric.alias == inbound_metric_alias or device_metric.name == metric_name:
				device_metric.value = get_metric_value(metric, metric_datatype)
				device_metric.timestamp = timestamp
				metric_list.append(device_metric)
				break
	return metric_list

def spb_proto_handler(mqtt_topic:str, payload:bytes) -> UNSMQTTMessage | list[UNSMQTTMessage] | None:
	"""
	Handle the Sparkplug B protobuf message.
	"""
	group_name, message_type, node_name, device_name = spb_topic_parser(mqtt_topic)
	inbound_payload = sparkplug_b_pb2.Payload()  # type: ignore[attr-defined]
	inbound_payload.ParseFromString(payload)  # type: ignore[attr-defined]
	# inbound_payload_timestamp = datetime.fromtimestamp(inbound_payload.timestamp / 1000)

	session = get_session()
	metric_list: list[Metric] = []
	topic_suffix = node_name

	try:
		if message_type == 'DBIRTH':
			device = get_or_add_device(session, group_name=group_name, node_name=node_name, device_name=device_name, device_type=DeviceType.SparkplugB)
			metric_list = spb_metrics_parser_for_birth(device=device, inbound_payload=inbound_payload)
			logger.debug(f"Parsed metrics for device birth: {[m.to_dict() for m in metric_list]}")
			update_device_in_db(session, device=device, data={"metrics": metric_list})
			topic_suffix = f"{node_name}/{device.name}"
		
		elif message_type == 'NBIRTH':
			node = get_or_add_node(session, group_name=group_name, node_name=node_name, device_type=DeviceType.SparkplugB)
			metric_list = spb_metrics_parser_for_birth(device=node, inbound_payload=inbound_payload)
			update_device_in_db(session, device=node, data={"metrics": metric_list})
			topic_suffix = node.name
		
		elif message_type == 'DDATA':
			device = get_or_add_device(session, group_name=group_name, node_name=node_name, device_name=device_name, device_type=DeviceType.SparkplugB)
			metric_list = spb_metrics_parser_for_data(device=device, inbound_payload=inbound_payload)
			update_device_in_db(session, device=device, data={"metrics": metric_list})
			# device.metrics = update_metrics(session=session, device=device, metric_list=metric_list)
			topic_suffix = f"{node_name}/{device.name}"
		
		elif message_type == 'NDATA':
			node = get_or_add_node(session, group_name=group_name, node_name=node_name, device_type=DeviceType.SparkplugB)
			metric_list = spb_metrics_parser_for_data(device=node, inbound_payload=inbound_payload)
			# node.metrics = update_metrics(session=session, device=node, metric_list=metric_list)
			update_device_in_db(session, device=node, data={"metrics": metric_list})
			topic_suffix = node.name
			uns_message = UNSMQTTMessage(
				topic=f"uns/data/{group_name}/{topic_suffix}",
				metrics=[{'name': m.name, 'value': m.value, 'datatype': MetricDataType(m.dataType).name} for m in node.metrics],
				timestamp=inbound_payload.timestamp  # type: ignore[attr-defined]
			)
			return uns_message

		elif message_type == 'DDEATH':
			# For device death, we can either delete the device or mark its metrics as stale. Here we choose to mark metrics as stale (e.g., set quality to 'DEAD' and value to None).
			device = get_or_add_device(session, group_name=group_name, node_name=node_name, device_name=device_name, device_type=DeviceType.SparkplugB)
			for metric in device.metrics:
				metric.value = None
				metric.quality = 'DEAD'
			update_device_in_db(session, device=device, data={"metrics": device.metrics})
			return UNSMQTTMessage(
				topic=f"uns/data/{group_name}/{node_name}/{device.name}",
				metrics=[{'name': m.name, 'value': m.value, 'datatype': MetricDataType(m.dataType).name} for m in device.metrics],
				timestamp=inbound_payload.timestamp  # type: ignore[attr-defined]
			)

		elif message_type == 'NDEATH':
			uns_message_list = []
			node = get_or_add_node(session, group_name=group_name, node_name=node_name, device_type=DeviceType.SparkplugB)
			devices = session.query(Device).filter(Device.node_id == node.id).all()
			for device in devices:
				updated_device_metrics = []
				for metric in device.metrics:
					metric.value = get_default_value_for_datatype(MetricDataType(metric.dataType))
					updated_device_metrics.append(metric)
				update_device_in_db(session, device=device, data={"metrics": updated_device_metrics})
				uns_message_list.append(UNSMQTTMessage(
					topic=f"uns/data/{group_name}/{node_name}/{device.name}",
					metrics=[{'name': m.name, 'value': m.value, 'datatype': MetricDataType(m.dataType).name} for m in device.metrics],
					timestamp=inbound_payload.timestamp  # type: ignore[attr-defined]
				))
			
			updated_node_metrics = []
			for metric in node.metrics:
				metric.value = get_default_value_for_datatype(MetricDataType(metric.dataType))
				updated_node_metrics.append(metric)

			update_device_in_db(session, device=node, data={"metrics": updated_node_metrics})
			uns_message_list.append(UNSMQTTMessage(
				topic=f"uns/data/{group_name}/{node_name}",
				metrics=[{'name': m.name, 'value': m.value, 'datatype': MetricDataType(m.dataType).name} for m in node.metrics],
				timestamp=inbound_payload.timestamp  # type: ignore[attr-defined]
			))
			return uns_message_list
		
		else:
			return None

		if not metric_list:
			logger.debug(f"No metrics to publish for Sparkplug message type {message_type} on {mqtt_topic}.")
			return None

		metric_items = []
		for metric in metric_list:
			try:
				datatype_name = MetricDataType(metric.dataType).name
			except Exception:
				datatype_name = getattr(metric, 'dataType_name', 'Unknown')
			metric_items.append({'name': metric.name, 'value': metric.value, 'datatype': datatype_name})

		return UNSMQTTMessage(
			topic=f"uns/data/{group_name}/{topic_suffix}",
			metrics=metric_items,
			timestamp=inbound_payload.timestamp  # type: ignore[attr-defined]
		)
	finally:
		session.close()

def on_spb_json(mqtt_topic:str, client_name:str, payload:dict):
	logger.debug(f"SpB json type Message received for {client_name} on {mqtt_topic}: {payload}")
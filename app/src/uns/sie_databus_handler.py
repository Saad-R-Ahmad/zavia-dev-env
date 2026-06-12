import json
import uuid
from typing import Any
from datetime import datetime
from core.logger import get_logger
from enum import Enum, auto
from re import split

from src.postgresql import get_session
from src.postgresql.models import Metric, Node, Device
from src.uns.models import DeviceType, UNSMQTTMessage
from src.uns.datatypes import MetricDataType, convert_value_based_on_datatype, get_default_value_for_datatype

from .crud import (
    get_or_add_device,
    get_or_add_node,
    update_device_in_db,
    update_node_in_db,
    get_device_metric_by_alias,
    update_metric_in_db,
    get_or_add_metric,
    sync_device_metrics
)

logger = get_logger().getChild(__name__)

class DatabusMessageType(Enum):
    META_DATA = "metadata"
    DATA = "data"
    STATUS = "status"
    UNKNOWN = "unknown" 

def get_message_type(topic:str)->DatabusMessageType:
    # Meta Data topic
    if 'ie/m' in topic:
        return DatabusMessageType.META_DATA
    # Data topic
    elif 'ie/d' in topic:
        return DatabusMessageType.DATA
    # Status topic
    elif 'ie/s' in topic:
        return DatabusMessageType.STATUS
    else:
        return DatabusMessageType.UNKNOWN

databus_datatype_to_metric_datatype_map = {
    'Int': MetricDataType.Int16,
    'DInt': MetricDataType.Int32,
    'LReal': MetricDataType.Float,
    'Bool': MetricDataType.Boolean,
    'String': MetricDataType.String,
    'Double' : MetricDataType.Double,
}

databus_quality_map = {
    0: "Bad",
    1: "Uncertain",
    2: "Good"
}

def update_device_metric_from_datamsg(session, device:Device, payload:dict)->list[Metric]:
    ''' function take the data bus data message to update the metrics values:
    payload format: {'seq': 615, 'ts': '2025-10-29T18:19:10.000Z', 'vals': [{'val': 433, 'qc': 2, 'id': 'id-SG2_In1'}, {'val': False, 'qc': 2, 'id': 'id-SG2Bool1'}]}'''
    
    incoming_metrics = payload["vals"]
    if "ts" in payload:
        str_timestamp = payload["ts"]
        dt = datetime.fromisoformat(str_timestamp.replace('Z', '+00:00'))
        unix_ms = int(dt.timestamp() * 1000)
    else:
        unix_ms = int(datetime.now().timestamp() * 1000)

    timestamp_dt = datetime.fromtimestamp(unix_ms / 1000)

    updated_metrics : list[Metric] = []
    
    for metric in incoming_metrics:
        metric_from_db = get_device_metric_by_alias(session, device=device,metric_alias=metric["id"])
        if metric_from_db is None:
            logger.warning(f"Metric with alias {metric['id']} not found for device {device.name}. Skipping update.")
            continue
        updated_value = convert_value_based_on_datatype(metric["val"],metric_from_db.dataType) # type: ignore
        quality = databus_quality_map[metric["qc"]]
        updated_metric = update_metric_in_db(session, metric=metric_from_db, data={"value": updated_value, "timestamp": timestamp_dt,"quality":quality})
        updated_metrics.append(updated_metric)
        
    return updated_metrics
    
def sie_databus_metrics_parser(session, device:Device, datapoint_definitions:list[dict]) -> list[Metric]:
    """Parse datapoint definitions and sync metrics with device, removing old ones."""
    # Create Metric objects for sync
    new_metrics = []
    unix_timestamp_ms = int(datetime.now().timestamp() * 1000)
    for metric_def in datapoint_definitions:
        metric_data_type = databus_datatype_to_metric_datatype_map[metric_def["dataType"]]
        metric_value_Init_value = get_default_value_for_datatype(metric_data_type)
        metric = Metric(
            id=str(uuid.uuid4()),
            device_id=device.id,
            name=metric_def["name"],
            alias=metric_def["id"],
            dataType=metric_data_type,
            dataType_name=metric_data_type.name,
            value=metric_value_Init_value,
            timestamp=unix_timestamp_ms,
            unit=metric_def.get("unit", ""),
            quality="Good"
        )
        new_metrics.append(metric)
    
    # Sync metrics (add new, keep existing, remove deleted)
    synced_metrics = sync_device_metrics(session=session, device=device, new_metrics=new_metrics)
    return synced_metrics
    
# function to create devices in the UNS based on the datapoints received in the metadata payload
def update_connections_datapoints(session, node:Node, datapoints:list[dict]) -> None:
    global logger
    devices : list[Device] = []
    for datapoint in datapoints:
        datapoint_name = datapoint["name"] if "name" in datapoint else None
        if datapoint_name is None:
            raise ValueError(f"Datapoint name is missing in metadata payload for datapoint : {datapoint}")
        device = get_or_add_device(session, group_name=node.group_name, # type: ignore
                                node_name=node.name,
                                device_name=datapoint_name,
                                device_type=DeviceType.Siemens_Databus)

        if device is not None:
            datapoint_definations = datapoint["dataPointDefinitions"] if "dataPointDefinitions" in datapoint else None
            if datapoint_definations is not None:
                metrics_list = sie_databus_metrics_parser(session, device=device, datapoint_definitions=datapoint_definations)
                # Metrics are already added to device via sie_databus_metrics_parser -> sync_device_metrics
                logger.debug(f"Updated device {device.name}: {[m.name for m in metrics_list]}")
                devices.append(device)
    return devices # type: ignore
    
# function creates nodes in the UNS based on the connections received in the metadata payload
def updated_connector_connections(session, connector_name:str, connections:list[dict]) -> None:
    global logger
    for connection in connections:
            connection_name = connection["name"] if "name" in connection else None
            if connection_name is None:
                raise ValueError(f"Connection name is missing in metadata payload for connection: {connection}")
            node = get_or_add_node(session, group_name=connector_name, node_name=connection_name, device_type=DeviceType.Siemens_Databus)
            if node is not None:
                logger.debug(f"Processing connection: {connection_name} under connector: {connector_name}")
                datapoints = connection["dataPoints"] if "dataPoints" in connection else None
                if datapoints is None:
                    logger.debug(f"No datapoints found for connection: {connection_name}, skipping device creation.")
                    return None
                else:
                    devices = update_connections_datapoints(session, node=node, datapoints=datapoints)
                    # Devices are already added to node via update_connections_datapoints -> get_or_add_device
    return None

# Function creates a new group in the UNS based on the connector name received in the metadata payload    
def process_metadata(session, topic:str , payload:dict)->None:
    global logger
    connector_name = topic.split('/')[-2]  # ie/m/j/simatic/v1/<connector-name>/dp
    logger.debug(f"Processing metadata for connector: {connector_name}")

    if "connections" in payload:
        connections = payload["connections"]
    else:
        return None
    
    if connections is None:
        return None
    else:
        updated_connector_connections(session, connector_name=connector_name, connections=connections)
        return None

def process_data(session, topic:str,payload:dict)->UNSMQTTMessage:
    ''' function take the data bus data message to update the metrics values and return UNSMQTTMessage:'''
    # topic format: ie/d/j/simatic/v1/<GroupID/Connector>/dp/r/<Node/Connection>/<Device>
    parts = topic.split('/')
    device_name = parts[-1]
    node_name = parts[-2]
    group_name = parts[-5]
    if "ts" in payload:
        str_timestamp = payload["ts"]
        dt = datetime.fromisoformat(str_timestamp.replace('Z', '+00:00'))
        unix_ms = int(dt.timestamp() * 1000)
    else:
        unix_ms = int(datetime.now().timestamp() * 1000)

    device = get_or_add_device(session, group_name=group_name,node_name=node_name,device_name=device_name,device_type=DeviceType.Siemens_Databus)
    updated_metrics = update_device_metric_from_datamsg(session, device=device,payload=payload)
    
    metric_items = []
    for metric in updated_metrics:
        try:
            datatype_name = MetricDataType(metric.dataType).name
        except Exception:
            datatype_name = getattr(metric, 'dataType_name', 'Unknown')
        metric_items.append({'name': metric.name, 'value': metric.value, 'datatype': datatype_name})

    uns_message = UNSMQTTMessage(
        topic = f"uns/data/{group_name}/{node_name}/{device.name}",
        metrics = metric_items,
        timestamp = unix_ms
    )

    return uns_message
    
def sie_databus_msg_handler(mqtt_topic:str, payload:bytes) -> None|dict:
    """
    Handle the Siemens Databus MQTT message.
    """
    payload_str = payload.decode('utf-8')
    payload = json.loads(payload_str)
    message_type = get_message_type(mqtt_topic)
    global logger
    
    session = get_session()

    if message_type == DatabusMessageType.META_DATA:
        ''' Handle Meta Data message '''
        logger.info(f" Meta Data Message Received on Topic: {mqtt_topic}")
        # logger.debug(f" \n Payload: {payload}")
        # Process metadata payload here
        process_metadata(session, mqtt_topic, payload)
        session.close()
        return None

    elif message_type == DatabusMessageType.DATA:
        ''' Handle Data message '''
        logger.info(f" Data Message Received on Topic: {mqtt_topic}")
        # logger.debug(f" \n Payload: {payload}")
        uns_message = process_data(session, topic=mqtt_topic,payload=payload)
        session.close()
        return uns_message # type: ignore

    elif message_type == DatabusMessageType.STATUS:
        ''' Handle Status message '''
        logger.debug(f" \n Status Message Received: \n Topic: {mqtt_topic} \n Payload: {payload}")
        # Process status payload here
        session.close()
        return None

    else:
        logger.warning(f" \n Unknown Message Type Received: \n Topic: {mqtt_topic} \n Payload: {payload}")
        session.close()
        return None
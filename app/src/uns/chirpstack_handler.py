import json
import uuid
from datetime import datetime
from typing import Any
from src.postgresql import get_session
from src.postgresql.models import Metric
from src.uns.models import UNSMQTTMessage
from src.uns.datatypes import MetricDataType, convert_value_based_on_datatype, get_default_value_for_datatype
from src.uns.crud import get_or_add_group, get_or_add_node, get_or_add_device, sync_device_metrics


chirpstack_datatype_to_metric_datatype_map = {
    'int': MetricDataType.Int16,
    'dint': MetricDataType.Int32,
    'lreal': MetricDataType.Float,
    'float': MetricDataType.Float,
    'bool': MetricDataType.Boolean,
    'string': MetricDataType.String,
    'double' : MetricDataType.Double,
}

def metrics_processor_chirpstack(device_id: str, metrics_payload:dict, unix_ts_ms:int)->list[Metric]:
    """
    Process the Chirpstack payload to extract metrics and return Metric objects.
    This is a placeholder function and should be implemented based on the actual payload structure.
    """
    print(f"Processing Chirpstack metrics payload: {metrics_payload}")  # Debug log
    metrics = []
    # Example processing logic (to be replaced with actual logic)
    for metric in metrics_payload:
        if type(metric) is dict:
            metric_name = metric["name"] if "name" in metric else list(metric.keys())[0]
            metric_value = metric["value"] if "value" in metric else metric[metric_name]
            metric_datatype = chirpstack_datatype_to_metric_datatype_map[str(metric["dataType"]).lower()] if "dataType" in metric else MetricDataType.String
            metric_unit = metric["unit"] if "unit" in metric else 'unspecified'
            metric_quality = metric["quality"] if "quality" in metric else "Uncertain"
            metric_alias = metric["alias"] if "alias" in metric else f"{metric_name}_{metric_datatype.name}"
        else:
            metric_name = metric
            metric_value = metrics_payload[metric]
            metric_datatype = MetricDataType.String
            metric_unit = 'unspecified'
            metric_quality = "Uncertain"
            metric_alias = f"{metric_name}_{metric_datatype.name}"
        
        #convert value based on datatype
        metric_value = convert_value_based_on_datatype(metric_value, metric_datatype)
        
        metric_obj = Metric(
            id=str(uuid.uuid4()),
            device_id=device_id,
            name=metric_name,
            alias=metric_alias,
            dataType=metric_datatype,
            dataType_name=metric_datatype.name,
            value=metric_value,
            timestamp=unix_ts_ms,
            unit=metric_unit,
            quality=metric_quality
        )
        # Add other datatype handling as needed
        metrics.append(metric_obj)
    return metrics

def chirpstack_msg_handler(mqtt_topic:str, payload:dict) -> UNSMQTTMessage | None:
    """
    Handler for Chirpstack messages.
    1. Parse the topic to extract relevant information.
    
        GroupID: is the tenanID that we assign to the LoRa messages for agrisol
        NodeID: is the application ID
        DeviceID: would be the DeviceEUI
        N.B: Data type and tag name should be added to the codec so the device metrics can be built up when the message is received
    2. Process the payload to extract metrics and other data.
    3. Construct and return an UNSMQTTMessage object with the extracted data.
    4. If the message type is not recognized, return None.
    Typical data message topic format: chirpstack/application/<ApplicationID>/device/<DeviceEUI>/event/up
    """
    print(f"\n Chirpstack type Message received on {mqtt_topic}:\n")
    
    topic = topic
    payload_str = payload.decode('utf-8')
    payload = json.loads(payload_str)
    session = get_session()
    group_id = payload["deviceInfo"]["tenantId"]
    group_name = payload["deviceInfo"]["tenantName"]
    group = get_or_add_group(session, group_name=group_name, group_id=group_id)
	
    node_id = payload["deviceInfo"]["applicationId"]
    node_name = payload["deviceInfo"]["applicationName"]
    node = get_or_add_node(session, group_name=group.name, node_name=node_name, node_id=node_id,device_type="Chirpstack")

    device_name = payload["deviceInfo"]["deviceName"]
    device_eui = payload["deviceInfo"]["devEui"]
    device = get_or_add_device(session, group_name=group.name, node_name=node.name, device_name=device_name, device_id=device_eui)

    str_timestamp = payload["time"]
    dt = datetime.fromisoformat(str_timestamp.replace('Z', '+00:00'))
    unix_ts_ms = int(dt.timestamp() * 1000)

    metrics_payload = payload["object"]["metrics"] if "metrics" in payload["object"] else payload["object"]

    # get the metrics list as Metric objects
    metrics_list = metrics_processor_chirpstack(device_id=device.id, metrics_payload=metrics_payload, unix_ts_ms=unix_ts_ms)

    #synchronize the device metrics with the received metrics
    metrics = sync_device_metrics(session=session, device=device, new_metrics=metrics_list)
        

    # Build metrics payload with robust datatype name resolution
    metric_items = []
    for metric in metrics:
        try:
            datatype_name = MetricDataType(metric.dataType).name
        except Exception:
            datatype_name = getattr(metric, 'dataType_name', 'Unknown')
        metric_items.append({'name': metric.name, 'value': metric.value, 'datatype': datatype_name})

    uns_message = UNSMQTTMessage(
        topic = f"uns/data/{group.name}/{node.name}/{device.name}",
        metrics = metric_items,
        timestamp = unix_ts_ms
    )
    session.close()
    return uns_message
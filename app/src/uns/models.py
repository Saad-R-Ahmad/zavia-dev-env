from pydantic import BaseModel
from enum import Enum


# Models to be used for the uns builder. These models represent the structure of nodes, devices, and metrics in the UNS system.
# Data from different sources should be mapped to these models before being sent to the UNS.
#The models are based on the SPB specification foe siemens databus following mapping should be followed:
# ie data bus terminology  -> UNS terminology
# Connector (.e.g. S7Connector) -> Group
# Connection (.e.g. bot_plc_sim) -> Node
# DataPoint (.e.g. default) -> Device
# DataPoint Definition (.e.g. State.FillingTank) -> Metric
# notes on siemens databus : https://www.notion.so/Technical-Specifications-13351ffa6843817982e8ce747fe72251?source=copy_link

class DeviceType(Enum):
	SparkplugB = "SparkplugB"
	Siemens_Databus = "Siemens_Databus"
	Chirpstack = "Chirpstack"
	Generic_JSON = "Generic_JSON"

class MQTTDataSpecification(str):
	JSON = "JSON"
	SparkplugB_Proto = "SparkplugB_Proto"
	SparkplugB_JSON = "SparkplugB_JSON"
	Siemens_Databus_JSON = "Siemens_Databus_JSON"
	Chirpstack_JSON = "Chirpstack_JSON"

class UNSMQTTMessage(BaseModel):
	topic: str
	metrics: list[dict]
	timestamp: int  # Unix timestamp in milliseconds

class InboundMsg(BaseModel):
    topic: str
    payload: bytes
    qos: int
    retain: bool
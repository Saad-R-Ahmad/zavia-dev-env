import queue
import asyncio
from src.core.settings import Settings
from typing import Any
import json
import paho.mqtt.client as mqtt
from sqlalchemy import text
from .crud import get_mqtt_connection_record_by_id, get_uns_mqtt_connection, delete_mqtt_connection_record, create_mqtt_connection,get_all_mqtt_connections
from .sie_databus_handler import sie_databus_msg_handler
from .chirpstack_handler import chirpstack_msg_handler
from src.core.logger import get_logger
from src.postgresql.models import SubscriptionTopic, MQTTConnection
from src.postgresql import get_session
from src.uns.models import MQTTDataSpecification, UNSMQTTMessage, InboundMsg
from .sparkplugB_handler import spb_proto_handler
import os
import socket

logger = get_logger().getChild("mqtt_manager")
mqtt_logger = get_logger().getChild("mqtt_messages")

message_counter_in = 0
message_counter_out = 0

# Store clients with their config hash: {connection_id: {'client': mqtt.Client, 'config_hash': str}}
mqtt_clients: dict[str, dict] = {}

msg_q_inbound: queue.Queue[InboundMsg | None] = queue.Queue(maxsize=2000)
msg_q_outbound: queue.Queue[UNSMQTTMessage | None] = queue.Queue(maxsize=2000)

def get_default_subscription_topics() -> list[SubscriptionTopic]:
	''' Define the default subscription topics for the UNS MQTT client '''
	return [
		SubscriptionTopic(
			topic="JSON/#",
			qos=1,
			enabled=True,
			data_specification=MQTTDataSpecification.JSON,
			# callback = on_message_json
		),
		SubscriptionTopic(
			topic="spBv1.0/#",
			qos=1,
			enabled=True,
			data_specification=MQTTDataSpecification.SparkplugB_Proto,
			# callback = on_spb_proto
		)
		,
		SubscriptionTopic(
			topic="ie/#",
			qos=1,
			enabled=True,
			data_specification=MQTTDataSpecification.Siemens_Databus_JSON,
			# callback = on_sie_databus_json
		),
		SubscriptionTopic(
			topic="chirpstack/application/+/device/+/event/up",
			qos=1,
			enabled=True,
			data_specification=MQTTDataSpecification.Chirpstack_JSON,
			# callback = on_chirpstack_msg
		)
	]

def create_uns_mqtt_connection_record() -> MQTTConnection:
	"""Ensure a default UNS MQTT connection exists in PostgreSQL and return it."""
	settings = Settings()  # type: ignore[call-arg]
	unique_client_id = f"{settings.mqtt_client_id}"

	logger.info(f"Creating UNS MQTT connection for broker: {settings.mqtt_broker}:{settings.mqtt_port}")
	logger.info(f"Client ID: {unique_client_id}")

	session = get_session()
	# Ensure schema has the is_connected column before any queries
	try:
		ensure_is_connected_column(session)
	except Exception as exc:
		logger.error(f"Schema check failed during UNS connection creation: {exc}")
	uns_connection = get_uns_mqtt_connection(session)
	if uns_connection is not None:
		logger.info("UNS MQTT connection already exists")
		session.close()
		return uns_connection

	subscription_topics_data = [
		{"topic": "JSON/#", "qos": 1, "enabled": True, "data_specification": MQTTDataSpecification.JSON},
		{"topic": "spBv1.0/#", "qos": 1, "enabled": True, "data_specification": MQTTDataSpecification.SparkplugB_Proto},
		{"topic": "ie/#", "qos": 1, "enabled": True, "data_specification": MQTTDataSpecification.Siemens_Databus_JSON},
		{"topic": "chirpstack/application/+/device/+/event/up", "qos": 1, "enabled": True, "data_specification": MQTTDataSpecification.Chirpstack_JSON}
	]

	uns_mqtt_connection_record = create_mqtt_connection(
		session=session,
		mqtt_broker=settings.mqtt_broker,
		mqtt_port=settings.mqtt_port,
		mqtt_username=settings.mqtt_username,
		mqtt_password=settings.mqtt_password,
		mqtt_client_id=unique_client_id,
		mqtt_keepalive=settings.mqtt_keepalive,
		mqtt_tls_enabled=settings.mqtt_tls_enabled,
		mqtt_tls_ca_certs=settings.mqtt_tls_ca_certs,
		mqtt_tls_certfile=settings.mqtt_tls_certfile,
		mqtt_tls_keyfile=settings.mqtt_tls_keyfile,
		mqtt_protocol_version=settings.mqtt_protocol_version,
		mqtt_reconnect_delay=settings.mqtt_reconnect_delay,
		mqtt_reconnect_delay_max=settings.mqtt_reconnect_delay_max,
		mqtt_will_topic=settings.mqtt_will_topic,
		mqtt_will_payload=settings.mqtt_will_payload,
		mqtt_will_qos=settings.mqtt_will_qos,
		mqtt_will_retain=settings.mqtt_will_retain,
		is_uns_broker=True,
		mqtt_clean_session=settings.mqtt_clean_session,
		subscription_topics=subscription_topics_data
	)
	session.close()
	return uns_mqtt_connection_record

def clear_mqtt_clients():
	"""Clear all MQTT client references - called from main.py for separation of concerns"""
	global mqtt_clients
	mqtt_clients.clear()
	logger.info("Cleared existing MQTT client references")

def cleanup_disconnected_clients():
	"""Remove only permanently disconnected clients from the global list"""
	global mqtt_clients
	for connection_id in list(mqtt_clients.keys()):
		client_info = mqtt_clients[connection_id]
		client = client_info['client']
		# Only remove clients that are not just temporarily disconnected
		# Check if client is truly dead (not just in reconnection state)
		try:
			if not client.is_connected():  # type: ignore[attr-defined]
				logger.info(f"Client {connection_id} appears to be permanently disconnected")
				del mqtt_clients[connection_id]
		except:
			# Keep the client if we can't determine its state
			pass

def print_client_statuses():
	"""Print status of all MQTT clients from the database."""
	session = get_session()
	client_records = get_all_mqtt_connections(session)
	count_diconnected_clients = 0
	for client in client_records:
		mqtt_client = get_or_create_mqtt_client(mqtt_connection_record=client)
		if not mqtt_client.is_connected():  # type: ignore[attr-defined]
			count_diconnected_clients += 1
			logger.warning(f"MQTT client {client.mqtt_client_id} is NOT connected to {client.mqtt_broker}:{client.mqtt_port}")
		# Also show persisted DB connection state
		logger.info(f"DB connection state: {client.id} ({client.mqtt_client_id}) {client.mqtt_broker}:{client.mqtt_port} is_connected={client.is_connected}")
	logger.info(f"disconnected clients: {count_diconnected_clients} of {len(mqtt_clients)} cached clients")
	session.close()


def get_or_create_mqtt_client(mqtt_connection_record: MQTTConnection) -> mqtt.Client:
	"""Return existing MQTT client or create a new one. Recreates if config changed."""
	global mqtt_clients
	import hashlib
	
	# Create a hash of connection settings to detect changes
	config_str = f"{mqtt_connection_record.mqtt_broker}:{mqtt_connection_record.mqtt_port}:"
	config_str += f"{mqtt_connection_record.mqtt_tls_enabled}:{mqtt_connection_record.mqtt_tls_ca_certs}:"
	config_str += f"{mqtt_connection_record.mqtt_tls_certfile}:{mqtt_connection_record.mqtt_tls_keyfile}:"
	config_str += f"{mqtt_connection_record.mqtt_username}"
	config_hash = hashlib.md5(config_str.encode()).hexdigest()
	
	# Check if client exists and config hasn't changed
	if mqtt_connection_record.id in mqtt_clients:
		cached = mqtt_clients[mqtt_connection_record.id]
		if cached['config_hash'] == config_hash:
			return cached['client']
		else:
			print(f"Connection config changed for {mqtt_connection_record.mqtt_client_id}, recreating client...")
			# Disconnect and remove old client
			old_client = cached['client']
			if old_client.is_connected():
				old_client.disconnect()
			old_client.loop_stop()
			del mqtt_clients[mqtt_connection_record.id]

	# Use a runtime-unique client ID per process to avoid broker-side collisions.
	base_client_id = mqtt_connection_record.mqtt_client_id or "uns-client"
	runtime_client_id = f"{base_client_id}-{socket.gethostname()}-{os.getpid()}"
	print(f'Creating new mqtt client instance with client ID {runtime_client_id} to connect to {mqtt_connection_record.id}')
	mqtt_client = mqtt.Client(
		client_id=runtime_client_id,
		protocol=mqtt.MQTTv5,
		reconnect_on_failure=True  # type: ignore[call-arg]
	)
	
	# Configure TLS at client creation time if enabled
	if mqtt_connection_record.mqtt_tls_enabled:
		print(f"Setting up TLS for MQTT client {mqtt_connection_record.mqtt_client_id}...")
		mqtt_client.tls_set(
			ca_certs=mqtt_connection_record.mqtt_tls_ca_certs,
			certfile=mqtt_connection_record.mqtt_tls_certfile,
			keyfile=mqtt_connection_record.mqtt_tls_keyfile,
			tls_version=mqtt_connection_record.mqtt_tls_version,  # type: ignore[arg-type]
			ciphers=mqtt_connection_record.mqtt_tls_ciphers
		)
		print(f"TLS is enabled for MQTT client {mqtt_connection_record.mqtt_client_id}")
	else:
		print(f"TLS is disabled for MQTT client {mqtt_connection_record.mqtt_client_id}")
	
	mqtt_client.on_connect = on_connect  # type: ignore[assignment]
	mqtt_client.on_connect_fail = on_connect_fail  # type: ignore[assignment]
	mqtt_client.on_disconnect = on_disconnect  # type: ignore[assignment]
	mqtt_client.on_message = on_message  # type: ignore[assignment]
	mqtt_client.on_subscribe = on_subscribe  # type: ignore[assignment]
	mqtt_client.on_unsubscribe = on_unsubscribe  # type: ignore[assignment]
	
	# Store client with config hash
	mqtt_clients[mqtt_connection_record.id] = {
		'client': mqtt_client,
		'config_hash': config_hash,
		'runtime_client_id': runtime_client_id
	}
	return mqtt_client

def mqtt_client_connect(mqtt_connection_record: MQTTConnection) -> mqtt.Client:
	"""
	Connect to the MQTT broker using the client name.
	"""
	mqtt_client = get_or_create_mqtt_client(mqtt_connection_record=mqtt_connection_record)
	
	# Only connect if not already connected and is_enabled is True
	if not mqtt_client.is_connected() and mqtt_connection_record.is_enabled:  # type: ignore[attr-defined]
		userdata = {'connection_id' : mqtt_connection_record.id}
		mqtt_client.user_data_set(userdata)
		mqtt_client.username_pw_set(username=mqtt_connection_record.mqtt_username or "", password=mqtt_connection_record.mqtt_password or "")
		
		# Set up automatic reconnection parameters
		mqtt_client.reconnect_delay_set(min_delay=5, max_delay=120)
		
		mqtt_client.connect_async(
			host=mqtt_connection_record.mqtt_broker, 
			port=mqtt_connection_record.mqtt_port,
			keepalive=mqtt_connection_record.mqtt_keepalive,
			clean_start=mqtt_connection_record.mqtt_clean_session)
		mqtt_client.loop_start()
		logger.info(f"Connecting to MQTT broker {mqtt_connection_record.mqtt_broker}:{mqtt_connection_record.mqtt_port} with client ID: {mqtt_connection_record.mqtt_client_id}")
	else:
		logger.info(f"MQTT client for {mqtt_connection_record.id} is already connected")
	
	return mqtt_client

def subscribe_to_all_topics(mqtt_connection_record: MQTTConnection) -> None:
	"""Subscribe to all topics defined in the mqtt_subscriptions list.
	This function checks if the MQTT client is connected and subscribes to each topic with the specified QoS.
	If the client is not connected or there are no subscriptions, it returns None.
	"""
	mqtt_subscriptions = mqtt_connection_record.subscription_topics
	logger.info(f"Subscribing to all topics {mqtt_subscriptions} for connection {mqtt_connection_record.id}...")
	mqtt_client = get_or_create_mqtt_client(mqtt_connection_record=mqtt_connection_record)
	if len(mqtt_subscriptions) == 0 or not mqtt_client.is_connected():
		return None
	for subscription in mqtt_subscriptions:
		qos_str = subscription.qos or "0:0"
		qos_int = int(qos_str.split(":")[0]) if isinstance(qos_str, str) else int(qos_str)
		mqtt_client.subscribe(subscription.topic, qos=qos_int)
		logger.info(f"Subscribed to {subscription.topic} with QoS {qos_int}")

async def stop_mqtt_clients():
	"""Disconnect all MQTT clients if connected."""
	session = get_session()
	from .crud import get_all_mqtt_connections
	mqtt_connections = get_all_mqtt_connections(session)
	logger.info(f"Stopping {len(mqtt_connections)} MQTT clients...")
	for connection in mqtt_connections:
		mqtt_client = get_or_create_mqtt_client(mqtt_connection_record=connection)
		if mqtt_client.is_connected():
			mqtt_client.disconnect()
	session.close()
	return True


def stop_mqtt_client(mqtt_connection_record: MQTTConnection):
	"""Disconnect a specific MQTT client by connection record."""
	global mqtt_clients
	global logger
	if mqtt_connection_record.id in mqtt_clients:
		mqtt_client = mqtt_clients[mqtt_connection_record.id]['client']
		if mqtt_client.is_connected():  # type: ignore[attr-defined]
			mqtt_client.disconnect()
			mqtt_client.loop_stop()
		del mqtt_clients[mqtt_connection_record.id]
		logger.info(f"Stopped and removed MQTT client for connection {mqtt_connection_record.id}")
	return True


async def start_mqtt_clients():
	"""Connect all configured MQTT clients and subscribe to their topics."""
	session = get_session()
	from .crud import get_all_mqtt_connections
	mqtt_connections = get_all_mqtt_connections(session)
	logger.info(f"Starting {len(mqtt_connections)} MQTT clients...")
	for connection in mqtt_connections:
		mqtt_client = mqtt_client_connect(mqtt_connection_record=connection)
	session.close()
	# Print DB states for verification
	logger.info("Printing client statuses for verification...")
	print_client_statuses()
	
	return True
	
''' Call back functions for the mqtt client '''
def on_connect(client, userdata, flags, reason_code, properties):
	# Paho MQTT v5 may provide an int or ReasonCode object.
	try:
		code_val = int(getattr(reason_code, 'value', reason_code))
	except Exception:
		code_val = 0 if str(reason_code) == 'Success' else -1
	if code_val == 0:
		logger.info(f"Connected successfully to {userdata['connection_id']}")
		session = get_session()
		connection_record = get_mqtt_connection_record_by_id(session, userdata["connection_id"])
		subscribe_to_all_topics(mqtt_connection_record=connection_record)
		# Update connection state in DB
		try:
			ensure_is_connected_column(session)
			if connection_record:
				connection_record.is_connected = True
			session.commit()
		except Exception as exc:
			logger.error(f"Failed to mark connection as connected: {exc}")
		session.close()
	else:
		logger.error("Failed to connect successfully.")

def on_connect_fail(client):
	userdata = client.user_data_get()
	logger.error(f'client failed to connect id: {userdata}')
	# Mark connection as disconnected
	try:
		session = get_session()
		ensure_is_connected_column(session)
		conn = get_mqtt_connection_record_by_id(session, userdata.get("connection_id")) if userdata else None
		if conn:
			conn.is_connected = False
			session.commit()
		session.close()
	except Exception as exc:
		logger.error(f"Failed to mark connection as disconnected on connect fail: {exc}")

def on_disconnect(client, userdata, reason_code, properties=None):  # type: ignore[no-untyped-def]
	userdata = client.user_data_get()
	logger.info(f'disconnected id: {userdata} - reason code: {reason_code}')
	
	# Don't immediately try to reconnect for normal disconnections (code 0)
	try:
		code_val = int(getattr(reason_code, 'value', reason_code)) if reason_code is not None else None
	except Exception:
		code_val = None
	if code_val == 0:
		logger.info(f"Client {userdata.get('connection_id', 'unknown')} disconnected normally, not reconnecting immediately")
	# Update connection state in DB
	try:
		session = get_session()
		ensure_is_connected_column(session)
		conn = get_mqtt_connection_record_by_id(session, userdata.get("connection_id")) if userdata else None
		if conn:
			conn.is_connected = False
			session.commit()
		session.close()
	except Exception as exc:
		logger.error(f"Failed to mark connection as disconnected: {exc}")

def on_subscribe(client, userdata, mid, reason_code_list, properties):
	logger.info(f"subscribed. {mid}, {reason_code_list}, {properties}")

def on_unsubscribe(client:mqtt.Client, userdata, mid, reason_code_list=None, properties=None):  # type: ignore[no-untyped-def]
	logger.info(f"unsubscribed. {mid}, {reason_code_list}, {properties}")

def on_message(client:mqtt.Client, userdata:Any, message:mqtt.MQTTMessage):
	"""Route messages by topic pattern to the right handler."""
	global message_counter_in
	message_counter_in += 1
	logger.info(f"Received message on topic {message.topic} counter incoming messages {message_counter_in}")  # type: ignore[union-attr]
	##############################
	# add to the msg_q and move on
	###############################
	item = InboundMsg(
		topic = message.topic, 
		payload=message.payload,
		qos=message.qos,
		retain=message.retain)
	try:
		msg_q_inbound.put_nowait(item)          # fast, thread-safe
	except queue.Full:
		# choose policy: drop/log/metrics
		# # e.g. drop newest:
		pass

async def on_sie_databus_json(topic:str,payload:bytes):
	logger.info(f"Siemens databus type Message received on {topic}")
	uns_message = sie_databus_msg_handler(mqtt_topic=topic, payload=payload)
	if uns_message is not None:
		add_to_outbound_q(uns_message=uns_message)  # type: ignore[arg-type]

async def on_spb_proto(topic:str, payload:bytes):
	logger.info(f"Sparkplug B [Proto] type Message received on {topic} \n")
	uns_message = spb_proto_handler(mqtt_topic=topic, payload=payload)
	if uns_message is not None:
		add_to_outbound_q(uns_message=uns_message)

async def on_spb_json(topic:str, payload:bytes):
	logger.info(f"Sparkplug B [Json] type Message received on {topic}: {payload}")

async def on_chirpstack_msg(topic:str, payload:bytes):
	logger.info(f"Chirpstack type Message received on {topic}:\n")
	uns_message = chirpstack_msg_handler(mqtt_topic=topic, payload=payload)
	if uns_message is not None:
		add_to_outbound_q(uns_message=uns_message)
	
def add_to_outbound_q(uns_message:UNSMQTTMessage|list[UNSMQTTMessage]):
	global message_counter_out
	message_counter_out += 1
	mqtt_logger.info(f"incoming messages: {message_counter_in} - outgoing messages: {message_counter_out}")
	try:
		if isinstance(uns_message, list):
			for msg in uns_message:
				msg_q_outbound.put_nowait(msg)          # fast, thread-safe
		else:
			msg_q_outbound.put_nowait(uns_message)          # fast, thread-safe
	except queue.Full:
		# choose policy: drop/log/metrics
		# # e.g. drop newest:
		pass

def ensure_is_connected_column(session):
	"""Ensure the mqtt_connections table has the is_connected column."""
	try:
		result = session.execute(text("SELECT 1 FROM information_schema.columns WHERE table_name='mqtt_connections' AND column_name='is_connected'"))
		row = result.fetchone()
		if row is None:
			session.execute(text("ALTER TABLE mqtt_connections ADD COLUMN is_connected BOOLEAN DEFAULT FALSE"))
			session.commit()
	except Exception as exc:
		logger.error(f"Could not ensure is_connected column: {exc}")
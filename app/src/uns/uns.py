"""
High-level orchestration module for UNS services.
This module coordinates service startup/shutdown and model registration.
"""
import asyncio
import logging
import json
from src.postgresql import get_session
from .mqtt_manager import (
    start_mqtt_clients,
    stop_mqtt_clients,
    create_uns_mqtt_connection_record,
	on_spb_proto,
	on_spb_json,
	on_sie_databus_json,
	on_chirpstack_msg,
	get_uns_mqtt_connection,
	get_or_create_mqtt_client,
	msg_q_inbound,
	msg_q_outbound
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
consumer_task_inbound = None
consumer_task_outbound = None

async def consumer_inbound():
    logger.info("Starting consumer_inbound task...")
    while True:
        item = await asyncio.to_thread(msg_q_inbound.get)
        if item is None:
            await asyncio.to_thread(msg_q_inbound.task_done)
            logger.info("Stopping consumer_inbound task...")
            break
        try:
            topic = item.topic
            # Siemens Industrial Edge topics (metadata + data)
            if topic.startswith("ie/"):
                await on_sie_databus_json(item.topic, item.payload)
                continue

            # Chirpstack uplinks
            if topic.startswith("chirpstack/application/"):
                await on_chirpstack_msg(item.topic, item.payload)
                continue

            # Sparkplug B proto messages
            if topic.startswith("spBv1.0/"):
                await on_spb_proto(item.topic, item.payload)
                continue

            # Generic JSON topics
            if topic.startswith("JSON/"):
                logger.info(f"Manual type Message received on {topic}: {item.payload}")
                continue
            # Fallback: safe decode to avoid crashing on binary payloads
            try:
                decoded = item.payload.decode("utf-8", errors="replace")
            except Exception as exc:  # pragma: no cover
                decoded = f"<decode error: {exc}>"
                logger.warning(f"Undeclared Message type received on {topic}: {decoded}")
        except Exception as exc:
            logger.exception(f"Inbound consumer failed processing topic {getattr(item, 'topic', '<unknown>')}: {exc}")
        finally:
            await asyncio.to_thread(msg_q_inbound.task_done)

async def consumer_outbound():
	while True:
		uns_message = await asyncio.to_thread(msg_q_outbound.get)
		if uns_message is None:
			await asyncio.to_thread(msg_q_outbound.task_done)
			logger.info("Stopping consumer_outbound task...")
			break
		try:
			session = get_session()
			uns_connection_record = get_uns_mqtt_connection(session)
			uns_mqtt_client = get_or_create_mqtt_client(mqtt_connection_record=uns_connection_record)
			metrics = uns_message.metrics
			timestamp = uns_message.timestamp
			uns_topic = uns_message.topic

			uns_payload = {
						'timestamp' : timestamp,
						'metrics' : metrics
						}
			uns_mqtt_client.publish(uns_topic, json.dumps(uns_payload))
			session.close()
		finally:
			await asyncio.to_thread(msg_q_outbound.task_done)


async def start_uns_services():
    """Start UNS services and initialize with PostgreSQL-backed MQTT connection."""
    create_uns_mqtt_connection_record()
    await start_mqtt_clients()
    global consumer_task_inbound
    global consumer_task_outbound
    if consumer_task_inbound is None:
        consumer_task_inbound = asyncio.create_task(consumer_inbound())
        logger.info("Started MQTT message consumer task inbound")
    if consumer_task_outbound is None:
        consumer_task_outbound = asyncio.create_task(consumer_outbound())
        logger.info("Started MQTT message consumer task outbound")
    logger.info("UNS services started with PostgreSQL.")


async def stop_uns_services():
    """Stop UNS services."""
    global consumer_task_inbound
    global consumer_task_outbound
    if consumer_task_inbound is not None:
        try:
            await asyncio.wait_for(asyncio.to_thread(msg_q_inbound.put, None), timeout=2.0)
        except asyncio.TimeoutError:
            logger.warning("Timed out enqueueing inbound sentinel during shutdown")
        try:
            await asyncio.wait_for(consumer_task_inbound, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for inbound consumer; cancelling task")
            consumer_task_inbound.cancel()
            try:
                await consumer_task_inbound
            except Exception:
                pass
        except Exception as exc:
            logger.warning(f"Inbound consumer ended with error during shutdown: {exc}")
        consumer_task_inbound = None
    if consumer_task_outbound is not None:
        try:
            await asyncio.wait_for(asyncio.to_thread(msg_q_outbound.put, None), timeout=2.0)
        except asyncio.TimeoutError:
            logger.warning("Timed out enqueueing outbound sentinel during shutdown")
        try:
            await asyncio.wait_for(consumer_task_outbound, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for outbound consumer; cancelling task")
            consumer_task_outbound.cancel()
            try:
                await consumer_task_outbound
            except Exception:
                pass
        except Exception as exc:
            logger.warning(f"Outbound consumer ended with error during shutdown: {exc}")
        consumer_task_outbound = None
    await stop_mqtt_clients()
    logger.info("UNS services stopped.")

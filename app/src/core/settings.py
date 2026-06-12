import ssl
from typing import Optional
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Allow turning off .env loading (e.g., in containers) so runtime env vars win
USE_ENV_FILE = os.getenv("USE_ENV_FILE", "true").lower() == "true"
ENV_FILE = ".env" if USE_ENV_FILE else None

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        case_sensitive=False,
        env_prefix='',
        # Environment variables take precedence over .env file
        env_ignore_empty=True,
        extra='ignore',
    )

    ## default MQTT Client settings
    mqtt_broker: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_client_id : str
    mqtt_tls_enabled : bool
    mqtt_tls_ca_certs: Optional[str] = None
    mqtt_tls_certfile: Optional[str] = None
    mqtt_tls_keyfile: Optional[str] = None
    mqtt_tls_version: Optional[int] = ssl.PROTOCOL_TLSv1_2
    mqtt_tls_ciphers: Optional[str] = None
    mqtt_keepalive :int = 60
    mqtt_clean_session : bool = True
    mqtt_protocol_version : int = 4
    mqtt_reconnect_delay : int = 5
    mqtt_reconnect_delay_max : int = 120
    mqtt_reconnect_delay_jitter : float = 0.1
    mqtt_max_inflight_messages : int = 20
    mqtt_max_queued_messages : int = 1000
    mqtt_message_timeout : int = 60
    mqtt_will_topic : str
    mqtt_will_payload : str
    mqtt_will_qos : int = 1
    mqtt_will_retain : bool = True

    # PostgreSQL settings (replacing Redis)
    db_host: str = 'postgres'
    db_port: int = 5432
    db_name: str = 'uns_builder'
    db_user: str = 'uns_user'
    db_password: str = 'uns_password'
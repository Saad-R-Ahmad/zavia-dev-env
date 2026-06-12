# TODO:

Data message processing for Siemens databus - Metrics not being pulished  

# Introduction

A data aggregation, storage, retrieval and streaming service.

Restructes the data coming in using predefine data specifications (SparkplugB, Siemens Databus format etc.) into a UNS structure:

{Org.}/{Group}/{Node}{Device}

**Feature: Ability to define your own structure**

Stores the data in an influxDB inline with the defined uns structure

Supplies timeseries data by providing and API

**TODO: Define the API**

Provides datastreams over a websocket server through an MQTT broker.

## MQTT Manager

Requires one MQTT broker to be defined as the default broker.

Subscribes to all the topics with the predefined structure on that broker and publishes the UNS / data stream on that broker.

Can connect to other brokers as well.

Brokers can be added/removed and modified. The default broker can not be removed.

Topics with predefined datastructures can be specified for all brokers to connect to.

New connectors can be built and added so long as they follow one of the predefined data specifications.


## Import Structure
main.py (Entry Point)
  ↓
uns.py (Orchestration Layer)
  ↓
mqtt_manager.py (Infrastructure Layer)
  ↓
handlers (sparkplugB_handler, sie_databus_handler, chirpstack_handler)
  ↓
crud.py (Data Access Layer)
  ↓
models.py (Data Models - Lowest Level)
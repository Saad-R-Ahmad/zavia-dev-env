MetricDataType = {
    "Unknown" : 0,
    "Int8" : 1,
    "Int16" : 2,
    "Int32" : 3,
    "Int64" : 4,
    "UInt8" : 5,
    "UInt16" : 6,
    "UInt32" : 7,
    "UInt64" : 8,
    "Float" : 9,
    "Double" : 10,
    "Boolean" : 11,
    "String" : 12,
    "DateTime" : 13,
    "Text" : 14,
    "UUID" : 15,
    "DataSet" : 16,
    "Bytes" : 17,
    "File" : 18,
    "Template" : 19,
}

BIRTH_TAG = "BIRTH"
DEATH_TAG = "DEATH"
DATA_TAG  = "DATA"

state = {
    "aliases":    dict(),
    "devices":    dict(),
    "unresolved": list()
}

load("logging.star", "log")

def convert_value(value_raw,datatype):
    if datatype in ["Int16","Int32","Int64","Int8","UInt16","UInt32","UInt64","UInt8"]:
        value = int(value_raw)
    elif datatype in ["Double","Float"]:
        value = float(value_raw)
    elif datatype == "Boolean":
        value = (value_raw in ["true","True","1","1.0"])
    elif datatype == "Bytes":
        value = bytes(value_raw)
    elif datatype in ["Text","String","UUID","DateTime"]:
        value = str(value_raw)
    elif datatype == "File":
        value = bytes(value_raw)
    else:
        value = value_raw

    return value

def apply(metric):
    '''
    Metric("mqtt_consumer", 
    tags={"source": "mqtt", "topic": "uns/data/ThetaPhiEdge/Nodered/NRDevice_1"}, 
    fields={"metrics_name": "testing/test1", "metrics_value": 58.0, "metrics_datatype": "Int64", "timestamp": 1.763820734611e+12}, 
    time=1763820734636957098)
    '''
    log.info("Starlark script processing metric: {}".format(metric))

    source = metric.tags.get("source", "")
    topic = metric.tags.get("topic", "")
    tokens = topic.split("/")
    ntokens = len(tokens)

    deviceid = ''
    metric_name = ''
    alias = len(state["aliases"])

    #Get info from topic
    if ntokens > 0: topic_root = tokens[0] #uns
    if ntokens > 2: groupid    = tokens[2] #Node GroupID
    if ntokens > 3: nodeid   = tokens[3] #EdgeNode ID
    if ntokens > 4: deviceid     = tokens[4] #Device ID
    if ntokens > 5: device_subid   = tokens[5] #Device Sub-ID

    if source != "mqtt":
        return None

    if topic_root != "uns":
        log.warn("unsupported message format from {}".format(source))
        return None

    #Basic error handling
    if "metrics_datatype" not in metric.fields:
        log.error("metric received without datatype: {}".format(metric))
        return None


    metric_name = metric.fields.get("metrics_name")
    datatype = metric.fields.get("metrics_datatype")

    value_raw = metric.fields.get("metrics_value")
    value = convert_value(value_raw, datatype)

    #strip all fields
    metric.fields.pop("metrics_datatype")
    metric.fields.pop("metrics_name")
    metric.fields.pop("metrics_value")
    metric.fields.pop("timestamp")
    
    # metric.tags.pop("host")
    metric.tags.pop("source")

    #metric.tags["MSG_FORMAT"] = msg_format
    metric.tags["GROUP_ID"]   = groupid
    #metric.tags[MSG_TYPE]   = msg_type
    metric.tags["EDGE_ID"]    = nodeid
    metric.tags["DEVICE_ID"]  = deviceid
    metric.tags["DATA_TYPE"] = datatype
    # metric.tags["DATA_TYPE"] = str([key for key,value in MetricDataType.items() if datatype==value][0])
    # metric.tags["ALIAS"] = id

    measurement_name = str(groupid+"_"+nodeid+"_"+deviceid)
    metric.name = measurement_name

    # Assign fields
    metric.fields[metric_name] = value
    log.info('logging data: {}'.format(metric))
    '''
    logging data: 
    Metric("mqtt_consumer", 
    tags={"DEVICE_ID": "Nodered", 
          "EDGE_ID": "ThetaPhiEdge", 
          "GROUP_ID": "data", 
          "topic": "uns/data/ThetaPhiEdge/Nodered/NRDevice_1"}, 
    fields={"testing/test1": 27.0}, 
    time=1763820908777942637)[tracking ID=41]
    '''

    return metric
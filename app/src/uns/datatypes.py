from enum import Enum
from typing import Any

class MetricDataType(Enum):
	Unknown = 0
	Int8 = 1
	Int16 = 2
	Int32 = 3
	Int64 = 4
	UInt8 = 5
	UInt16 = 6
	UInt32 = 7
	UInt64 = 8
	Float = 9
	Double = 10
	Boolean = 11
	String = 12
	DateTime = 13
	Text = 14
	UUID = 15
	DataSet = 16
	Bytes = 17
	File = 18
	Template = 19

def convert_value_based_on_datatype(value:Any,datatype:MetricDataType)->Any:
    if datatype in [MetricDataType.Int16,MetricDataType.Int32,MetricDataType.Int8,MetricDataType.Int64,MetricDataType.UInt8,MetricDataType.UInt16,MetricDataType.UInt32,MetricDataType.UInt64]:
        return int(value) if value is not None else 0
    if datatype == MetricDataType.Boolean:
        return bool(value) if value is not None else False
    elif datatype ==MetricDataType.Float:
        return float(value) if value is not None else 0.0
    elif datatype == MetricDataType.Double:
        return float(value) if value is not None else 0.0
    elif datatype == MetricDataType.String:
        return str(value) if value is not None else ''
    else:
        return value
    
def get_default_value_for_datatype(datatype:MetricDataType)->Any:
    if datatype in [MetricDataType.Int16,MetricDataType.Int32,MetricDataType.Int8,MetricDataType.Int64,MetricDataType.UInt8,MetricDataType.UInt16,MetricDataType.UInt32,MetricDataType.UInt64]:
        return 0
    if datatype == MetricDataType.Boolean:
        return False
    elif datatype == MetricDataType.Float:
        return 0.0
    elif datatype == MetricDataType.Double:
        return 0.0
    elif datatype == MetricDataType.String:
        return ''
    else:
        return None
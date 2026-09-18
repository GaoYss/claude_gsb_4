"""水源点校验规则。"""

from ..constants import INTAKE_METHOD, WATER_SOURCE_STATUS, WATER_SOURCE_TYPE
from .common import PayloadValidator


def validate_water_source(payload):
    return (
        PayloadValidator(payload)
        .string("code", "水源点编号", max_length=32)
        .string("name", "水源点名称", required=True, max_length=96)
        .string("district", "所在行政区", required=True, max_length=64)
        .string("address", "位置说明", max_length=255)
        .enum("source_type", "水源类型", group=WATER_SOURCE_TYPE, required=True)
        .enum("intake_method", "取水方式", group=INTAKE_METHOD, required=True)
        .string("meter_no", "计量表编号", max_length=64)
        .number("flow_rate", "额定流量", min_value=0.01, max_value=99999)
        .enum("status", "水源点状态", group=WATER_SOURCE_STATUS, default="normal")
        .text("remark", "备注", max_length=2000)
        .done()
    )

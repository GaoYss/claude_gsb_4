"""灌溉水源点校验规则。"""

from ..constants import WATER_SOURCE_STATUS, WATER_SOURCE_TYPE
from .common import PHONE_PATTERN, PayloadValidator


def validate_water_source(payload):
    return (
        PayloadValidator(payload)
        .string("source_no", "水源点编号", max_length=32)
        .string("name", "水源点名称", required=True, max_length=128)
        .enum("source_type", "水源类型", group=WATER_SOURCE_TYPE, required=True)
        .string("district", "所属行政区", required=True, max_length=64)
        .string("address", "取水位置", max_length=255)
        .integer("green_space_id", "关联绿地", min_value=1)
        .enum("status", "水源点状态", group=WATER_SOURCE_STATUS, default="active")
        .string("manager", "管护人", max_length=64)
        .string("contact_phone", "联系电话", max_length=32, pattern=PHONE_PATTERN,
                pattern_message="联系电话格式不正确")
        .date("installed_date", "启用日期")
        .text("remark", "备注", max_length=2000)
        .done()
    )

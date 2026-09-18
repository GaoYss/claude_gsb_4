"""灌溉用水记录校验规则。"""

from ..constants import IRRIGATION_METHOD
from .common import PayloadValidator


def validate_irrigation_record(payload):
    return (
        PayloadValidator(payload)
        .integer("green_space_id", "覆盖绿地", required=True, min_value=1)
        .integer("water_source_id", "水源点", required=True, min_value=1)
        .integer("maintenance_record_id", "关联养护记录", min_value=1)
        .date("irrigation_date", "灌溉日期", required=True)
        .enum("method", "灌溉方式", group=IRRIGATION_METHOD, required=True)
        .number("water_volume", "用水量（吨）", min_value=0.01, max_value=999999)
        .integer("duration_minutes", "灌溉时长（分钟）", min_value=1, max_value=100000)
        .number("covered_area_sqm", "覆盖面积（平方米）", min_value=0.01, max_value=99999999)
        .string("worker_team", "执行班组", max_length=64)
        .string("operator", "登记人", max_length=64)
        .text("remark", "备注", max_length=2000)
        .done()
    )

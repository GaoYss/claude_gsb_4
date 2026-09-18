"""灌溉记录校验规则。"""

from .common import PayloadValidator


def validate_irrigation_record(payload):
    # 用水量与灌溉时长至少填一项、时长折算等跨字段规则在 service 层校验
    return (
        PayloadValidator(payload)
        .integer("green_space_id", "覆盖绿地", required=True, min_value=1)
        .integer("water_source_id", "水源点", min_value=1)
        .date("irrigation_date", "灌溉日期", required=True)
        .number("water_amount", "用水量", min_value=0.01, max_value=999999)
        .number("duration_hours", "灌溉时长", min_value=0.1, max_value=200)
        .string("team", "执行班组", required=True, max_length=64)
        .string("operator", "登记人", max_length=64)
        .text("remark", "备注", max_length=2000)
        .done()
    )

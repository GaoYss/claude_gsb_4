"""灌溉用水记录接口。"""

from flask import Blueprint, request

from ..schemas import irrigation_filters, validate_irrigation_record
from ..services import IrrigationRecordService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("irrigation_records", __name__)


def _load_context(filters):
    """异常标记基于全量记录计算，列表与汇总共用同一份结果。"""

    abnormal = IrrigationRecordService.abnormal_id_set()
    query = IrrigationRecordService.list_records(filters, request.args, abnormal_ids=abnormal)

    def serialize(item):
        data = item.to_dict()
        data["is_abnormal"] = item.id in abnormal
        return data

    return abnormal, query, serialize


@bp.get("/irrigation-records")
def list_irrigation_records():
    filters = irrigation_filters(request.args)
    page, page_size = parse_page_args()
    abnormal, query, serialize = _load_context(filters)
    data = paginate(query, page, page_size, serializer=serialize)
    data["summary"] = IrrigationRecordService.summary(filters, abnormal=abnormal)
    return ok(data)


@bp.get("/irrigation-records/summary")
def irrigation_summary():
    filters = irrigation_filters(request.args)
    return ok(IrrigationRecordService.summary(filters))


@bp.post("/irrigation-records")
def create_irrigation_record():
    payload = validate_irrigation_record(json_body())
    record = IrrigationRecordService.create(payload)
    return created(record.to_dict(detail=True), message="灌溉用水记录登记成功")


@bp.get("/irrigation-records/<int:record_id>")
def get_irrigation_record(record_id):
    return ok(IrrigationRecordService.detail(record_id))


@bp.put("/irrigation-records/<int:record_id>")
def update_irrigation_record(record_id):
    payload = validate_irrigation_record(json_body())
    record = IrrigationRecordService.update(record_id, payload)
    return ok(record.to_dict(detail=True), message="灌溉用水记录已更新")


@bp.delete("/irrigation-records/<int:record_id>")
def delete_irrigation_record(record_id):
    IrrigationRecordService.delete(record_id)
    return ok(None, message="灌溉用水记录已删除")

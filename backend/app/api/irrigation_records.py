"""灌溉记录接口。"""

from flask import Blueprint, request

from ..schemas import validate_irrigation_record
from ..schemas.filters import irrigation_filters
from ..services import IrrigationRecordService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("irrigation_records", __name__)


@bp.get("/irrigation-records")
def list_irrigation_records():
    filters = irrigation_filters(request.args)
    page, page_size = parse_page_args()
    query = IrrigationRecordService.list_records(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = IrrigationRecordService.summary(filters)
    return ok(data)


@bp.get("/irrigation-records/summary")
def irrigation_summary():
    return ok(IrrigationRecordService.summary(irrigation_filters(request.args)))


@bp.get("/irrigation-records/monthly-summary")
def irrigation_monthly_summary():
    """按行政区与月份汇总用水量，异常偏高的单次用水随组返回。"""

    return ok(IrrigationRecordService.monthly_summary(request.args))


@bp.post("/irrigation-records")
def create_irrigation_record():
    payload = validate_irrigation_record(json_body())
    record = IrrigationRecordService.create(payload)
    return created(record.to_dict(detail=True), message="灌溉记录登记成功")


@bp.get("/irrigation-records/<int:record_id>")
def get_irrigation_record(record_id):
    return ok(IrrigationRecordService.detail(record_id))


@bp.put("/irrigation-records/<int:record_id>")
def update_irrigation_record(record_id):
    payload = validate_irrigation_record(json_body())
    record = IrrigationRecordService.update(record_id, payload)
    return ok(record.to_dict(detail=True), message="灌溉记录已更新")


@bp.delete("/irrigation-records/<int:record_id>")
def delete_irrigation_record(record_id):
    IrrigationRecordService.delete(record_id)
    return ok(None, message="灌溉记录已删除")

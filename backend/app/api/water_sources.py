"""水源点接口。"""

from flask import Blueprint, request

from ..schemas import validate_water_source
from ..schemas.filters import water_source_filters
from ..services import WaterSourceService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("water_sources", __name__)


@bp.get("/water-sources")
def list_water_sources():
    filters = water_source_filters(request.args)
    page, page_size = parse_page_args()
    query = WaterSourceService.list_sources(filters, request.args)
    data = paginate(query, page, page_size, serializer=WaterSourceService.serialize_row)
    data["summary"] = WaterSourceService.summary(filters)
    return ok(data)


@bp.get("/water-sources/options")
def water_source_options():
    keyword = (request.args.get("keyword") or "").strip() or None
    return ok({"items": WaterSourceService.options(keyword)})


@bp.get("/water-sources/summary")
def water_source_summary():
    return ok(WaterSourceService.summary(water_source_filters(request.args)))


@bp.post("/water-sources")
def create_water_source():
    payload = validate_water_source(json_body())
    source = WaterSourceService.create(payload)
    return created(source.to_dict(detail=True), message="水源点登记成功")


@bp.get("/water-sources/<int:source_id>")
def get_water_source(source_id):
    return ok(WaterSourceService.detail(source_id))


@bp.put("/water-sources/<int:source_id>")
def update_water_source(source_id):
    payload = validate_water_source(json_body())
    source = WaterSourceService.update(source_id, payload)
    return ok(source.to_dict(detail=True), message="水源点已更新")


@bp.delete("/water-sources/<int:source_id>")
def delete_water_source(source_id):
    force = str(request.args.get("force", "")).lower() in {"1", "true", "yes"}
    WaterSourceService.delete(source_id, force=force)
    return ok(None, message="水源点已删除")

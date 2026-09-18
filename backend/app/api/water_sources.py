"""灌溉水源点接口。"""

from flask import Blueprint, request

from ..schemas import validate_water_source, water_source_filters
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
    data["summary"] = WaterSourceService.filtered_summary(filters)
    return ok(data)


@bp.get("/water-sources/options")
def water_source_options():
    """下拉选项：默认仅返回在用/备用且与绿地同区（或公共）的水源点。"""

    keyword = (request.args.get("keyword") or "").strip() or None
    district = (request.args.get("district") or "").strip() or None
    try:
        green_space_id = int(request.args.get("green_space_id") or 0) or None
    except (TypeError, ValueError):
        green_space_id = None
    items = WaterSourceService.options(
        keyword=keyword, district=district, green_space_id=green_space_id
    )
    return ok({"items": items})


@bp.post("/water-sources")
def create_water_source():
    payload = validate_water_source(json_body())
    source = WaterSourceService.create(payload)
    return created(source.to_dict(detail=True), message="灌溉水源点创建成功")


@bp.get("/water-sources/<int:source_id>")
def get_water_source(source_id):
    return ok(WaterSourceService.get(source_id).to_dict(detail=True))


@bp.put("/water-sources/<int:source_id>")
def update_water_source(source_id):
    payload = validate_water_source(json_body())
    source = WaterSourceService.update(source_id, payload)
    return ok(source.to_dict(detail=True), message="灌溉水源点已更新")


@bp.delete("/water-sources/<int:source_id>")
def delete_water_source(source_id):
    """存在灌溉用水记录的水源点不可删除，仅可置为停用。"""

    WaterSourceService.delete(source_id)
    return ok(None, message="灌溉水源点已删除")

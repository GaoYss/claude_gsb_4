"""水源点业务逻辑。"""

from sqlalchemy import func, or_

from ..errors import ConflictError
from ..extensions import db
from ..models import IrrigationRecord, WaterSource
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import year_prefix


class WaterSourceService(BaseService):
    """水源点：台账维护与删除保护（有灌溉记录时需确认，记录侧置空保留履历）。"""

    model = WaterSource
    label = "水源点"
    code_field = "code"
    code_width = 4

    SORTABLE = {
        "code": WaterSource.code,
        "name": WaterSource.name,
        "flow_rate": WaterSource.flow_rate,
        "created_at": WaterSource.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return year_prefix("WS")

    # ------------------------------------------------------------ 查询
    @staticmethod
    def _apply_filters(query, filters):
        if filters.get("source_type"):
            query = query.filter(WaterSource.source_type == filters["source_type"])
        if filters.get("intake_method"):
            query = query.filter(WaterSource.intake_method == filters["intake_method"])
        if filters.get("status"):
            query = query.filter(WaterSource.status == filters["status"])
        if filters.get("district"):
            query = query.filter(WaterSource.district == filters["district"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    WaterSource.name.like(like),
                    WaterSource.code.like(like),
                    WaterSource.district.like(like),
                    WaterSource.address.like(like),
                    WaterSource.meter_no.like(like),
                )
            )
        return query

    @classmethod
    def list_sources(cls, filters, args):
        irrigation_count = (
            db.select(func.count(IrrigationRecord.id))
            .where(IrrigationRecord.water_source_id == WaterSource.id)
            .correlate(WaterSource)
            .scalar_subquery()
        )
        query = db.session.query(WaterSource, irrigation_count.label("irrigation_count"))
        query = cls._apply_filters(query, filters)
        return query.order_by(parse_sort(args, cls.SORTABLE, WaterSource.code.asc()))

    @classmethod
    def serialize_row(cls, row):
        source, irrigation_count = row
        data = source.to_dict()
        data["irrigation_count"] = irrigation_count or 0
        return data

    @classmethod
    def detail(cls, obj_id):
        source = cls.get(obj_id)
        data = source.to_dict(detail=True)
        data["irrigation_count"] = (
            db.session.query(func.count(IrrigationRecord.id))
            .filter(IrrigationRecord.water_source_id == source.id)
            .scalar()
            or 0
        )
        return data

    @classmethod
    def options(cls, keyword=None, limit=50):
        """下拉选项：仅提供正常使用与维护中的水源点。"""

        query = db.session.query(WaterSource).filter(WaterSource.status != "disabled")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(WaterSource.name.like(like), WaterSource.code.like(like)))
        query = query.order_by(WaterSource.code.asc()).limit(limit)
        return [item.to_brief() for item in query.all()]

    @classmethod
    def summary(cls, filters):
        """水源点汇总：按状态统计处数，并合计额定流量。"""

        status_rows = (
            cls._apply_filters(
                db.session.query(WaterSource.status, func.count(WaterSource.id)), filters
            )
            .group_by(WaterSource.status)
            .all()
        )
        total, flow_total = cls._apply_filters(
            db.session.query(
                func.count(WaterSource.id),
                func.coalesce(func.sum(WaterSource.flow_rate), 0),
            ),
            filters,
        ).one()
        return {
            "total": total or 0,
            "total_flow_rate": to_float(flow_total) or 0,
            "by_status": {status: count for status, count in status_rows},
        }

    # ------------------------------------------------------------ 写入
    @classmethod
    def delete(cls, obj_id, force=False):
        source = cls.get(obj_id)
        irrigation_count = (
            db.session.query(func.count(IrrigationRecord.id))
            .filter(IrrigationRecord.water_source_id == source.id)
            .scalar()
            or 0
        )
        if irrigation_count and not force:
            raise ConflictError(
                f"该水源点已关联灌溉记录 {irrigation_count} 条，删除后记录将保留但解除关联，"
                "请确认后重试",
                details={"irrigation_record": irrigation_count},
            )
        db.session.delete(source)
        db.session.commit()
        return {"irrigation_record": irrigation_count}

"""灌溉水源点业务逻辑。"""

from sqlalchemy import func, or_

from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import GreenSpace, IrrigationRecord, WaterSource
from ..utils.dates import format_date
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import year_prefix


class WaterSourceService(BaseService):
    """水源点：建档、检索、下拉选项与删除保护。"""

    model = WaterSource
    label = "灌溉水源点"
    code_field = "source_no"
    code_width = 4

    SORTABLE = {
        "source_no": WaterSource.source_no,
        "name": WaterSource.name,
        "district": WaterSource.district,
        "installed_date": WaterSource.installed_date,
        "created_at": WaterSource.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return year_prefix("WS")

    # ------------------------------------------------------------ 校验
    @classmethod
    def prepare_instance(cls, instance, payload):
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        if green_space_id:
            space = db.session.get(GreenSpace, green_space_id)
            if space is None:
                raise ValidationError("保存失败", details={"green_space_id": "关联绿地不存在"})
            instance.green_space_id = green_space_id
        else:
            instance.green_space_id = None

    # ------------------------------------------------------------ 查询
    @staticmethod
    def _apply_filters(query, filters):
        if filters.get("green_space_id"):
            query = query.filter(WaterSource.green_space_id == filters["green_space_id"])
        if filters.get("district"):
            query = query.filter(WaterSource.district == filters["district"])
        if filters.get("source_type"):
            query = query.filter(WaterSource.source_type == filters["source_type"])
        if filters.get("status"):
            query = query.filter(WaterSource.status == filters["status"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    WaterSource.source_no.like(like),
                    WaterSource.name.like(like),
                    WaterSource.district.like(like),
                    WaterSource.address.like(like),
                    WaterSource.manager.like(like),
                )
            )
        return query

    @classmethod
    def list_sources(cls, filters, args):
        """列表查询：带出各水源点的灌溉引用次数与最近取用日期。"""

        usage_count = (
            db.select(func.count(IrrigationRecord.id))
            .where(IrrigationRecord.water_source_id == WaterSource.id)
            .correlate(WaterSource)
            .scalar_subquery()
        )
        last_used = (
            db.select(func.max(IrrigationRecord.irrigation_date))
            .where(IrrigationRecord.water_source_id == WaterSource.id)
            .correlate(WaterSource)
            .scalar_subquery()
        )
        query = db.session.query(WaterSource, usage_count.label("usage_count"),
                                 last_used.label("last_used_date"))
        query = cls._apply_filters(query, filters)
        return query.order_by(parse_sort(args, cls.SORTABLE, WaterSource.source_no.asc()))

    @classmethod
    def serialize_row(cls, row):
        source, usage_count, last_used = row
        data = source.to_dict()
        data["statistics"] = {
            "usage_count": usage_count or 0,
            "last_used_date": format_date(last_used),
        }
        return data

    @classmethod
    def filtered_summary(cls, filters):
        rows = cls._apply_filters(
            db.session.query(WaterSource.status, func.count(WaterSource.id)),
            filters,
        ).group_by(WaterSource.status).all()
        status = {code: 0 for code in ("active", "standby", "disabled")}
        for value, count in rows:
            status[value] = count
        return {"total": sum(status.values()), "by_status": status}

    @classmethod
    def options(cls, keyword=None, district=None, green_space_id=None, limit=50):
        """下拉选项：停用的水源点不参与新登记。

        - 按行政区过滤：返回该区全部水源点，外加不绑定绿地的公共取水点；
        - 仅按绿地过滤：返回该绿地自有水源点与公共取水点；
        - 支持按名称/编号搜索。
        """

        query = db.session.query(WaterSource).filter(WaterSource.status != "disabled")
        if district:
            # 同区水源点均可共用，含该区的公共取水点
            query = query.filter(WaterSource.district == district)
        elif green_space_id:
            # 未提供行政区时返回绿地自有水源点与全部公共取水点
            query = query.filter(
                or_(WaterSource.green_space_id == green_space_id,
                    WaterSource.green_space_id.is_(None))
            )
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(WaterSource.name.like(like), WaterSource.source_no.like(like)))
        query = query.order_by(WaterSource.source_no.asc()).limit(limit)
        return [item.to_brief() for item in query.all()]

    # ------------------------------------------------------------ 删除
    @classmethod
    def delete(cls, obj_id):
        source = cls.get(obj_id)
        usage = (
            db.session.query(func.count(IrrigationRecord.id))
            .filter(IrrigationRecord.water_source_id == source.id)
            .scalar()
            or 0
        )
        if usage:
            # 用水台账须保留取水溯源，不随水源点删除，建议改为「停用」
            raise ConflictError(
                f"该水源点已有 {usage} 条灌溉用水记录，为保证用水台账完整不可删除，"
                "可将水源点状态调整为「停用」",
                details={"irrigation_record": usage},
            )
        db.session.delete(source)
        db.session.commit()
        return {"irrigation_record": 0}

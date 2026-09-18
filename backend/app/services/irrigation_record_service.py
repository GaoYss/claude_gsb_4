"""灌溉用水记录业务逻辑。

用水计量口径：

- 每次灌溉登记用水量（吨）或灌溉时长（分钟），二者至少填写一项；
- 用水量按「行政区 × 自然月」汇总；
- 异常偏高：同一行政区、同一月份样本不少于 3 次时，采用稳健的
  MAD 修正标准分（modified z-score）判定单次离高值::

      M = 0.6745 × (x − 中位数) / 中位绝对偏差（MAD），M ≥ 3.5 标记；

  MAD 为 0（半数以上取值相同）时退化为「超过中位数 3 倍」判定。
  相比均值/标准差，该口径不会因单个高值把均值显著抬高而漏检。
"""

from collections import defaultdict

from sqlalchemy import func, or_

from ..errors import ValidationError
from ..extensions import db
from ..models import GreenSpace, IrrigationRecord, MaintenanceRecord, WaterSource
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix

ABNORMAL_MODIFIED_ZSCORE = 3.5
ABNORMAL_MIN_SAMPLES = 3
ABNORMAL_MEDIAN_FACTOR = 3.0


class IrrigationRecordService(BaseService):
    """灌溉用水记录：登记、检索、用水量汇总与异常标记。"""

    model = IrrigationRecord
    label = "灌溉用水记录"
    code_field = "record_no"
    code_width = 3

    SORTABLE = {
        "irrigation_date": IrrigationRecord.irrigation_date,
        "water_volume": IrrigationRecord.water_volume,
        "duration_minutes": IrrigationRecord.duration_minutes,
        "covered_area_sqm": IrrigationRecord.covered_area_sqm,
        "record_no": IrrigationRecord.record_no,
        "created_at": IrrigationRecord.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("IR")

    # ------------------------------------------------------------ 校验
    @classmethod
    def prepare_instance(cls, instance, payload):
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("登记失败", details={"green_space_id": "覆盖绿地不存在"})

        water_source_id = payload.get("water_source_id", instance.water_source_id)
        source = db.session.get(WaterSource, water_source_id) if water_source_id else None
        if source is None:
            raise ValidationError("登记失败", details={"water_source_id": "所选水源点不存在"})

        record_id = payload.get("maintenance_record_id", instance.maintenance_record_id)
        if record_id:
            record = db.session.get(MaintenanceRecord, record_id)
            if record is None:
                raise ValidationError(
                    "登记失败", details={"maintenance_record_id": "关联的养护记录不存在"}
                )
            if record.green_space_id != space.id:
                raise ValidationError(
                    "登记失败",
                    details={"maintenance_record_id": "关联的养护记录不属于覆盖绿地"},
                )

        volume = payload.get("water_volume", instance.water_volume)
        duration = payload.get("duration_minutes", instance.duration_minutes)
        if not volume and not duration:
            raise ValidationError(
                "登记失败",
                details={"water_volume": "用水量与灌溉时长至少填写一项"},
            )

        covered_area = payload.get("covered_area_sqm", instance.covered_area_sqm)
        if covered_area and space.area_sqm and float(covered_area) > float(space.area_sqm):
            raise ValidationError(
                "登记失败",
                details={"covered_area_sqm": f"覆盖面积不能大于绿地总面积 {space.area_sqm:g} 平方米"},
            )

        irrigation_date = payload.get("irrigation_date", instance.irrigation_date)
        if irrigation_date and space.established_date and irrigation_date < space.established_date:
            raise ValidationError(
                "登记失败",
                details={"irrigation_date": f"灌溉日期不能早于该绿地建成日期 {space.established_date}"},
            )

    # ------------------------------------------------------------ 异常判定
    @staticmethod
    def _median(values):
        ordered = sorted(values)
        middle = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[middle]
        return (ordered[middle - 1] + ordered[middle]) / 2

    @classmethod
    def _abnormal_ids(cls, values):
        """values 为 [(record_id, volume)]，返回异常偏高的记录 id 集合。"""

        if len(values) < ABNORMAL_MIN_SAMPLES:
            return set()
        volumes = [volume for _, volume in values]
        median = cls._median(volumes)
        mad = cls._median([abs(volume - median) for volume in volumes])
        if mad > 0:
            abnormal = {
                record_id
                for record_id, volume in values
                if 0.6745 * (volume - median) / mad >= ABNORMAL_MODIFIED_ZSCORE
            }
        else:
            # 半数以上取值相同：直接按中位数倍数识别离高值
            threshold = median * ABNORMAL_MEDIAN_FACTOR
            abnormal = {
                record_id
                for record_id, volume in values
                if median > 0 and volume > threshold
            }
        return abnormal

    @staticmethod
    def abnormal_id_set():
        """全量记录按「行政区 × 月份」分组，返回异常偏高的记录 id 集合。"""

        rows = (
            db.session.query(
                IrrigationRecord.id,
                GreenSpace.district,
                IrrigationRecord.irrigation_date,
                IrrigationRecord.water_volume,
            )
            .join(GreenSpace, GreenSpace.id == IrrigationRecord.green_space_id)
            .filter(IrrigationRecord.water_volume.isnot(None))
            .all()
        )
        groups = defaultdict(list)
        for record_id, district, irrigation_date, volume in rows:
            groups[(district, f"{irrigation_date:%Y-%m}")].append((record_id, float(volume)))

        abnormal = set()
        for values in groups.values():
            abnormal.update(IrrigationRecordService._abnormal_ids(values))
        return abnormal

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        query = query.join(GreenSpace, GreenSpace.id == IrrigationRecord.green_space_id)
        if filters.get("green_space_id"):
            query = query.filter(IrrigationRecord.green_space_id == filters["green_space_id"])
        if filters.get("water_source_id"):
            query = query.filter(IrrigationRecord.water_source_id == filters["water_source_id"])
        if filters.get("maintenance_record_id"):
            query = query.filter(IrrigationRecord.maintenance_record_id == filters["maintenance_record_id"])
        if filters.get("district"):
            query = query.filter(GreenSpace.district == filters["district"])
        if filters.get("method"):
            query = query.filter(IrrigationRecord.method == filters["method"])
        if filters.get("date_from"):
            query = query.filter(IrrigationRecord.irrigation_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(IrrigationRecord.irrigation_date <= filters["date_to"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    IrrigationRecord.record_no.like(like),
                    IrrigationRecord.worker_team.like(like),
                    IrrigationRecord.operator.like(like),
                )
            )
        return query

    @classmethod
    def list_records(cls, filters, args, abnormal_ids=None):
        query = cls._apply_filters(db.session.query(IrrigationRecord), filters)
        if filters.get("abnormal_only"):
            if abnormal_ids is None:
                abnormal_ids = cls.abnormal_id_set()
            query = query.filter(IrrigationRecord.id.in_(abnormal_ids))
        return query.order_by(
            parse_sort(args, cls.SORTABLE, IrrigationRecord.irrigation_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    # ------------------------------------------------------------ 汇总
    @classmethod
    def summary(cls, filters, abnormal=None):
        """按行政区 × 月份汇总用水量，并标记异常偏高的单次用水。"""

        if abnormal is None:
            abnormal = cls.abnormal_id_set()
        rows = cls._apply_filters(
            db.session.query(
                IrrigationRecord.id,
                GreenSpace.district,
                IrrigationRecord.irrigation_date,
                IrrigationRecord.water_volume,
                IrrigationRecord.duration_minutes,
            ),
            filters,
        ).all()

        buckets = {}
        order = []
        total_volume = 0.0
        total_duration = 0
        abnormal_in_scope = []
        for record_id, district, irrigation_date, volume, duration in rows:
            month = f"{irrigation_date:%Y-%m}"
            key = (district, month)
            if key not in buckets:
                buckets[key] = {
                    "district": district,
                    "month": month,
                    "count": 0,
                    "total_volume": 0.0,
                    "total_duration_minutes": 0,
                    "abnormal_count": 0,
                }
                order.append(key)
            bucket = buckets[key]
            bucket["count"] += 1
            if volume is not None:
                bucket["total_volume"] = round(bucket["total_volume"] + float(volume), 2)
                total_volume = round(total_volume + float(volume), 2)
            if duration is not None:
                bucket["total_duration_minutes"] += int(duration)
                total_duration += int(duration)
            if record_id in abnormal:
                bucket["abnormal_count"] += 1
                abnormal_in_scope.append(record_id)

        monthly = [buckets[key] for key in order]
        monthly.sort(key=lambda item: (item["month"], item["total_volume"]), reverse=True)

        abnormal_records = (
            db.session.query(IrrigationRecord)
            .filter(IrrigationRecord.id.in_(abnormal_in_scope))
            .order_by(IrrigationRecord.water_volume.desc())
            .limit(20)
            .all()
            if abnormal_in_scope
            else []
        )

        return {
            "total_count": len(rows),
            "total_volume": to_float(total_volume) or 0,
            "total_duration_minutes": total_duration,
            "abnormal_count": len(abnormal_in_scope),
            "monthly_by_district": monthly,
            "abnormal_records": [item.to_dict() for item in abnormal_records],
        }

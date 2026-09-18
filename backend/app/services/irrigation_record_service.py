"""灌溉记录业务逻辑。"""

from datetime import timedelta
from decimal import Decimal

from flask import current_app
from sqlalchemy import func, or_

from ..errors import ValidationError
from ..extensions import db
from ..models import GreenSpace, IrrigationRecord, WaterSource
from ..utils.dates import parse_date, today
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix


class IrrigationRecordService(BaseService):
    """灌溉记录：登记用水量或时长（按水源点额定流量折算），并按行政区×月份汇总。"""

    model = IrrigationRecord
    label = "灌溉记录"
    code_field = "record_no"
    code_width = 3

    SORTABLE = {
        "irrigation_date": IrrigationRecord.irrigation_date,
        "water_amount": IrrigationRecord.water_amount,
        "duration_hours": IrrigationRecord.duration_hours,
        "created_at": IrrigationRecord.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("IR")

    # ------------------------------------------------------------ 校验与派生
    @classmethod
    def prepare_instance(cls, instance, payload):
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("登记失败", details={"green_space_id": "所选绿地不存在"})

        water_source_id = payload.get("water_source_id", instance.water_source_id)
        if water_source_id and db.session.get(WaterSource, water_source_id) is None:
            raise ValidationError("登记失败", details={"water_source_id": "所选水源点不存在"})

        irrigation_date = payload.get("irrigation_date", instance.irrigation_date)
        if irrigation_date and space.established_date and irrigation_date < space.established_date:
            raise ValidationError(
                "登记失败",
                details={
                    "irrigation_date": f"灌溉日期不能早于该绿地建成日期 {space.established_date}"
                },
            )

        # 显式登记了用水量：以登记值为准，取消估算标记（避免旧估算标记覆盖新登记值）
        if payload.get("water_amount") is not None:
            instance.is_estimated = False

    @classmethod
    def apply_derived(cls, instance):
        """用水量折算：登记了实际水量则以登记为准；否则按时长 × 水源点额定流量折算。

        估算记录（is_estimated=True）在修改班组、更换水源点等场景下会按最新
        时长与流量重新折算，保证结果幂等。
        """

        if not instance.is_estimated and instance.water_amount is not None:
            return
        if instance.duration_hours is None:
            raise ValidationError(
                "登记失败", details={"water_amount": "用水量与灌溉时长至少填写一项"}
            )
        source = (
            db.session.get(WaterSource, instance.water_source_id)
            if instance.water_source_id
            else None
        )
        if source is None or not source.flow_rate:
            raise ValidationError(
                "登记失败",
                details={"water_amount": "该水源点未维护额定流量，无法按时长折算，请直接登记用水量"},
            )
        instance.water_amount = (
            Decimal(str(instance.duration_hours)) * Decimal(str(source.flow_rate))
        ).quantize(Decimal("0.01"))
        instance.is_estimated = True

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("green_space_id"):
            query = query.filter(IrrigationRecord.green_space_id == filters["green_space_id"])
        if filters.get("water_source_id"):
            query = query.filter(IrrigationRecord.water_source_id == filters["water_source_id"])
        if filters.get("team"):
            query = query.filter(IrrigationRecord.team == filters["team"])
        if filters.get("estimated"):
            query = query.filter(IrrigationRecord.is_estimated.is_(True))
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
                    IrrigationRecord.team.like(like),
                    IrrigationRecord.operator.like(like),
                )
            )
        return query

    @classmethod
    def list_records(cls, filters, args):
        query = cls._apply_filters(db.session.query(IrrigationRecord), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, IrrigationRecord.irrigation_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def summary(cls, filters):
        """列表汇总：条数、用水量（实际/估算拆分）与灌溉时长。"""

        total_count, total_amount, total_duration = cls._apply_filters(
            db.session.query(
                func.count(IrrigationRecord.id),
                func.coalesce(func.sum(IrrigationRecord.water_amount), 0),
                func.coalesce(func.sum(IrrigationRecord.duration_hours), 0),
            ),
            filters,
        ).one()
        estimated_count, estimated_amount = cls._apply_filters(
            db.session.query(
                func.count(IrrigationRecord.id),
                func.coalesce(func.sum(IrrigationRecord.water_amount), 0),
            ).filter(IrrigationRecord.is_estimated.is_(True)),
            filters,
        ).one()
        return {
            "total_count": total_count or 0,
            "total_water_amount": to_float(total_amount) or 0,
            "total_duration_hours": to_float(total_duration) or 0,
            "estimated_count": estimated_count or 0,
            "estimated_amount": to_float(estimated_amount) or 0,
        }

    # ------------------------------------------------------------ 行政区 × 月份汇总
    @staticmethod
    def _parse_month(value, label):
        """YYYY-MM 解析为当月第一天，非法值返回 None。"""

        try:
            return parse_date(f"{value}-01", label)
        except (TypeError, ValueError):
            return None

    @classmethod
    def monthly_summary(cls, args):
        """按行政区与月份汇总用水量，并标记异常偏高的单次用水。

        异常判定：单次用水量 > 同区同月其他记录平均值 × 配置倍数
        （IRRIGATION_ANOMALY_MULTIPLIER，默认 2.0）；组内仅一条记录时不标记。
        """

        district = (args.get("district") or "").strip() or None
        month_to = cls._parse_month(args.get("month_to"), "截止月份")
        month_from = cls._parse_month(args.get("month_from"), "起始月份")
        if month_to is None:
            month_to = today().replace(day=1)
        if month_from is None:
            cursor = month_to
            for _ in range(5):
                cursor = (cursor - timedelta(days=1)).replace(day=1)
            month_from = cursor
        if month_from > month_to:
            month_from, month_to = month_to, month_from
        # 截止月月末（含）：取下个月第一天之前
        next_month = (month_to.replace(day=28) + timedelta(days=7)).replace(day=1)

        query = (
            db.session.query(IrrigationRecord, GreenSpace.district, GreenSpace.name)
            .join(GreenSpace, IrrigationRecord.green_space_id == GreenSpace.id)
            .filter(
                IrrigationRecord.irrigation_date >= month_from,
                IrrigationRecord.irrigation_date < next_month,
                IrrigationRecord.water_amount.isnot(None),
            )
            .order_by(IrrigationRecord.irrigation_date.asc(), IrrigationRecord.id.asc())
        )
        if district:
            query = query.filter(GreenSpace.district == district)

        multiplier = float(current_app.config.get("IRRIGATION_ANOMALY_MULTIPLIER", 2.0))
        groups = {}
        for record, district_name, space_name in query.all():
            key = (district_name, f"{record.irrigation_date:%Y-%m}")
            groups.setdefault(key, []).append((record, space_name))

        result_groups = []
        totals = {
            "record_count": 0,
            "total_water_amount": 0.0,
            "actual_amount": 0.0,
            "estimated_amount": 0.0,
            "anomaly_count": 0,
        }
        for (district_name, month), rows in sorted(groups.items()):
            amounts = [float(record.water_amount or 0) for record, _ in rows]
            total_amount = round(sum(amounts), 2)
            count = len(rows)

            anomalies = []
            for (record, space_name), amount in zip(rows, amounts):
                if count < 2:
                    break
                others_avg = (total_amount - amount) / (count - 1)
                if others_avg > 0 and amount > multiplier * others_avg:
                    anomalies.append(
                        {
                            "record_id": record.id,
                            "record_no": record.record_no,
                            "irrigation_date": record.irrigation_date.isoformat(),
                            "green_space_id": record.green_space_id,
                            "green_space_name": space_name,
                            "team": record.team,
                            "water_amount": round(amount, 2),
                            "is_estimated": record.is_estimated,
                            "others_avg": round(others_avg, 2),
                            "ratio": round(amount / others_avg, 1),
                        }
                    )

            estimated_amount = round(
                sum(amount for (record, _), amount in zip(rows, amounts) if record.is_estimated), 2
            )
            duration_total = round(
                sum(float(record.duration_hours or 0) for record, _ in rows), 2
            )
            result_groups.append(
                {
                    "district": district_name,
                    "month": month,
                    "record_count": count,
                    "total_water_amount": total_amount,
                    "actual_amount": round(total_amount - estimated_amount, 2),
                    "estimated_amount": estimated_amount,
                    "total_duration_hours": duration_total,
                    "avg_amount": round(total_amount / count, 2) if count else 0,
                    "anomaly_count": len(anomalies),
                    "anomalies": anomalies,
                }
            )
            totals["record_count"] += count
            totals["total_water_amount"] = round(totals["total_water_amount"] + total_amount, 2)
            totals["estimated_amount"] = round(totals["estimated_amount"] + estimated_amount, 2)
            totals["anomaly_count"] += len(anomalies)
        totals["actual_amount"] = round(
            totals["total_water_amount"] - totals["estimated_amount"], 2
        )

        return {
            "params": {
                "district": district,
                "month_from": f"{month_from:%Y-%m}",
                "month_to": f"{month_to:%Y-%m}",
                "anomaly_multiplier": multiplier,
            },
            "groups": result_groups,
            "totals": totals,
        }

"""灌溉记录模型。"""

from ..extensions import db
from ..utils.dates import format_date, format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class IrrigationRecord(TimestampMixin, db.Model):
    """灌溉记录：一次灌溉的用水量（或时长折算）、覆盖绿地与执行班组。"""

    __tablename__ = "irrigation_record"

    id = db.Column(db.Integer, primary_key=True)
    record_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    water_source_id = db.Column(
        db.Integer, db.ForeignKey("water_source.id", ondelete="SET NULL"), nullable=True, index=True
    )
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    irrigation_date = db.Column(db.Date, nullable=False, index=True)
    water_amount = db.Column(quantity_column())  # 用水量 m³；按时长折算时由后端回填
    duration_hours = db.Column(quantity_column())
    is_estimated = db.Column(db.Boolean, nullable=False, default=False)  # 时长×额定流量折算
    team = db.Column(db.String(64), nullable=False, index=True)
    operator = db.Column(db.String(64))
    remark = db.Column(db.Text)

    water_source = db.relationship("WaterSource", back_populates="irrigations", lazy="joined")
    green_space = db.relationship("GreenSpace", back_populates="irrigations", lazy="joined")

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "record_no": self.record_no,
            "water_source_id": self.water_source_id,
            "water_source": self.water_source.to_brief() if self.water_source else None,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "irrigation_date": format_date(self.irrigation_date),
            "water_amount": to_float(self.water_amount),
            "duration_hours": to_float(self.duration_hours),
            "is_estimated": self.is_estimated,
            "team": self.team,
            "operator": self.operator,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data

"""灌溉用水记录模型。"""

from ..constants import IRRIGATION_METHOD
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class IrrigationRecord(TimestampMixin, db.Model):
    """灌溉用水记录：每次灌溉登记用水量或时长、覆盖绿地与执行班组。"""

    __tablename__ = "irrigation_record"

    id = db.Column(db.Integer, primary_key=True)
    record_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    water_source_id = db.Column(
        db.Integer,
        db.ForeignKey("water_source.id"),
        nullable=False,
        index=True,
    )
    maintenance_record_id = db.Column(
        db.Integer,
        db.ForeignKey("maintenance_record.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    irrigation_date = db.Column(db.Date, nullable=False, index=True)
    method = db.Column(db.String(32), nullable=False, index=True)
    water_volume = db.Column(quantity_column())
    duration_minutes = db.Column(db.Integer)
    covered_area_sqm = db.Column(quantity_column())
    worker_team = db.Column(db.String(64), index=True)
    operator = db.Column(db.String(64))
    remark = db.Column(db.Text)

    green_space = db.relationship("GreenSpace", back_populates="irrigations", lazy="joined")
    water_source = db.relationship("WaterSource", back_populates="irrigation_records", lazy="joined")
    record = db.relationship("MaintenanceRecord", back_populates="irrigations")

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "record_no": self.record_no,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "water_source_id": self.water_source_id,
            "water_source": self.water_source.to_brief() if self.water_source else None,
            "maintenance_record_id": self.maintenance_record_id,
            "record": (
                {
                    "id": self.record.id,
                    "record_no": self.record.record_no,
                    "record_date": format_date(self.record.record_date),
                }
                if self.record
                else None
            ),
            "irrigation_date": format_date(self.irrigation_date),
            "method": self.method,
            "method_label": IRRIGATION_METHOD.label(self.method),
            "water_volume": to_float(self.water_volume),
            "duration_minutes": self.duration_minutes,
            "covered_area_sqm": to_float(self.covered_area_sqm),
            "worker_team": self.worker_team,
            "operator": self.operator,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data

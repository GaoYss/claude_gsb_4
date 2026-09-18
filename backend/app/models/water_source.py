"""水源点模型。"""

from ..constants import INTAKE_METHOD, WATER_SOURCE_STATUS, WATER_SOURCE_TYPE
from ..extensions import db
from ..utils.dates import format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class WaterSource(TimestampMixin, db.Model):
    """水源点：灌溉取水的来源与取水方式台账。"""

    __tablename__ = "water_source"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), nullable=False, unique=True, index=True)
    name = db.Column(db.String(96), nullable=False, index=True)
    district = db.Column(db.String(64), nullable=False, index=True)
    address = db.Column(db.String(255))
    source_type = db.Column(db.String(32), nullable=False, index=True)
    intake_method = db.Column(db.String(32), nullable=False, index=True)
    meter_no = db.Column(db.String(64))
    flow_rate = db.Column(quantity_column())  # 额定流量 m³/h，用于按时长折算用水量
    status = db.Column(db.String(16), nullable=False, default="normal", index=True)
    remark = db.Column(db.Text)

    irrigations = db.relationship("IrrigationRecord", back_populates="water_source")

    def to_brief(self):
        """下拉框与关联展示用的精简结构。"""

        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "district": self.district,
            "intake_method": self.intake_method,
            "intake_method_label": INTAKE_METHOD.label(self.intake_method),
            "flow_rate": to_float(self.flow_rate),
        }

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "district": self.district,
            "address": self.address,
            "source_type": self.source_type,
            "source_type_label": WATER_SOURCE_TYPE.label(self.source_type),
            "intake_method": self.intake_method,
            "intake_method_label": INTAKE_METHOD.label(self.intake_method),
            "meter_no": self.meter_no,
            "flow_rate": to_float(self.flow_rate),
            "status": self.status,
            "status_label": WATER_SOURCE_STATUS.label(self.status),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data

"""灌溉水源点模型。"""

from ..constants import WATER_SOURCE_STATUS, WATER_SOURCE_TYPE
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from .mixins import TimestampMixin


class WaterSource(TimestampMixin, db.Model):
    """灌溉水源点：登记取水位置、取水方式与状态，供灌溉记录引用。"""

    __tablename__ = "water_source"

    id = db.Column(db.Integer, primary_key=True)
    source_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    source_type = db.Column(db.String(32), nullable=False, index=True)
    district = db.Column(db.String(64), nullable=False, index=True)
    address = db.Column(db.String(255))
    green_space_id = db.Column(
        db.Integer,
        db.ForeignKey("green_space.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = db.Column(db.String(16), nullable=False, default="active", index=True)
    manager = db.Column(db.String(64))
    contact_phone = db.Column(db.String(32))
    installed_date = db.Column(db.Date)
    remark = db.Column(db.Text)

    green_space = db.relationship("GreenSpace", back_populates="water_sources", lazy="joined")
    irrigation_records = db.relationship("IrrigationRecord", back_populates="water_source")

    def to_brief(self):
        """下拉框与关联展示用的精简结构。"""

        return {
            "id": self.id,
            "source_no": self.source_no,
            "name": self.name,
            "source_type": self.source_type,
            "district": self.district,
        }

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "source_no": self.source_no,
            "name": self.name,
            "source_type": self.source_type,
            "source_type_label": WATER_SOURCE_TYPE.label(self.source_type),
            "district": self.district,
            "address": self.address,
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "status": self.status,
            "status_label": WATER_SOURCE_STATUS.label(self.status),
            "manager": self.manager,
            "contact_phone": self.contact_phone,
            "installed_date": format_date(self.installed_date),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data

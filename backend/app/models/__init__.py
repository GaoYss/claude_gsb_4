"""模型包：导入全部模型，保证 db.create_all() 能建全表。"""

from .green_space import GreenSpace
from .irrigation_record import IrrigationRecord
from .maintenance_record import MaintenanceRecord
from .maintenance_task import MaintenanceTask
from .plant_replacement import PlantReplacement
from .water_source import WaterSource

__all__ = [
    "GreenSpace",
    "MaintenanceTask",
    "MaintenanceRecord",
    "PlantReplacement",
    "WaterSource",
    "IrrigationRecord",
]

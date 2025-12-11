# temperature_model.py

from dataclasses import dataclass
from typing import Dict


@dataclass
class TemperatureResourceDef:
    path: str         # pełna ścieżka, np. "/3303/0/5700"
    name: str         # nazwa z LwM2M, np. "Sensor Value"
    description: str  # opis zasobu
    datatype: str     # np. "float", "string"
    operations: str   # np. "R", "RW"
    units: str | None = None  # np. "°C" albo None


# Minimalny data model temperatury – JEDEN zasób: 5700
TEMPERATURE_RESOURCES: Dict[str, TemperatureResourceDef] = {
    "/3303/0/5700": TemperatureResourceDef(
        path="/3303/0/5700",
        name="Sensor Value",
        description="Current temperature of the sensor",
        datatype="float",
        operations="R",
        units="°C",
    ),
}
DISCOVER_3303_0_PAYLOAD = b"</3303/0/5700>"

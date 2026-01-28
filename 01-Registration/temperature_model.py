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


def get_temperature_value() -> float:
    """
    Zwraca aktualną wartość temperatury jako float.
    Do użycia w TLV encoding i innych operacjach.
    
    :return: temperatura jako float
    """
    # Ta funkcja będzie wywołana z lwm2m_client.py
    # Na razie zwracamy wartość przykładową, 
    # faktyczna implementacja jest w lwm2m_client._current_temp
    # Zostanie to połączone w refaktoringu
    import random
    T_MIN = 20.0
    T_MAX = 26.0
    return random.uniform(T_MIN, T_MAX)

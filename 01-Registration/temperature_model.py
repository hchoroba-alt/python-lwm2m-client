# temperature_model.py

from dataclasses import dataclass
from typing import Dict
import requests


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


def get_katowice_temperature() -> float:
    """
    Pobiera aktualną temperaturę z Katowic używając API Open-Meteo.
    Zwraca temperaturę w stopniach Celsjusza.
    W przypadku błędu zwraca 20.0 jako wartość domyślną.
    """
    try:
        # Współrzędne Katowic: 50.2649, 19.0238
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 50.2649,
            "longitude": 19.0238,
            "current_weather": True
        }
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        temperature = data["current_weather"]["temperature"]
        print(f"DEBUG: Pobrano temperaturę z Katowic: {temperature}°C")
        return float(temperature)
    except Exception as e:
        print(f"ERROR: Nie udało się pobrać temperatury z Katowic: {e}")
        print("DEBUG: Zwracam domyślną wartość 20.0°C")
        return 20.0

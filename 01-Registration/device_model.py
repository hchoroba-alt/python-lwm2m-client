# device_model.py
"""
Prosta implementacja LwM2M Device Object (ID: 3) dla instancji /3/0.

Obsługiwane zasoby (zgodnie z OMA Device Object):
- /3/0/0  Manufacturer (string)
- /3/0/1  Model number (string)
- /3/0/2  Serial number (string)
- /3/0/3  Firmware version (string)
- /3/0/6  Available power sources (string, uproszczenie)
- /3/0/7  Power source voltage (string, mV)
- /3/0/8  Power source current (string, mA)
- /3/0/9  Battery level (string, %)
- /3/0/10 Memory free (string, kB)
- /3/0/11 Error code (string; 0 = no error)
- /3/0/13 Current time (string, epoch seconds)
- /3/0/14 UTC offset (string, np. "+01:00")
- /3/0/15 Timezone (string, np. "Europe/Warsaw")
- /3/0/16 Supported binding and modes (string, np. "U")
"""

from __future__ import annotations

from typing import Optional
import time
from datetime import datetime, timezone


# Lista zasobów dla DISCOVER /3/0 w application/link-format
# Musi być spójna z tym, co wystawiasz w main.py przez DeviceValueResource.
DISCOVER_3_0_PAYLOAD: bytes = b",".join(
    [
        b"</3/0/0>",
        b"</3/0/1>",
        b"</3/0/2>",
        b"</3/0/3>",
        b"</3/0/6>",
        b"</3/0/7>",
        b"</3/0/8>",
        b"</3/0/9>",
        b"</3/0/10>",
        b"</3/0/11>",
        b"</3/0/13>",
        b"</3/0/14>",
        b"</3/0/15>",
        b"</3/0/16>",
    ]
)


# Statyczne wartości Device Object.
# Dla prostoty przechowujemy je jako stringi i przy odczycie zamieniamy na bytes.
DEVICE_STATIC_VALUES = {
    "/3/0/0": "Malaria Corp.",         # Manufacturer
    "/3/0/1": "Malaria-Client-01",     # Model number
    "/3/0/2": "SN-00000001",           # Serial number
    "/3/0/3": "1.0.0",                 # Firmware version
    # Uproszczone multi-instance – tutaj jako zwykły tekst.
    # W "prawdziwym" TLV byłaby to tablica instancji.
    "/3/0/6": "0",                     # Available power sources (0 = DC)
    "/3/0/7": "5000",                  # Power source voltage (mV)
    "/3/0/8": "100",                   # Power source current (mA)
    "/3/0/9": "100",                   # Battery level (%)
    "/3/0/10": "1024",                 # Memory free (kB) – wartość przykładowa
    "/3/0/11": "0",                    # Error code (0 = no error)
    "/3/0/14": "+01:00",               # UTC offset (np. Europa/Warszawa zimą)
    "/3/0/15": "Europe/Warsaw",        # Timezone
    "/3/0/16": "U",                    # Supported binding and modes (U = UDP)
}


def _read_current_time_epoch() -> str:
    """
    Zwraca bieżący czas w sekundach od epoch (string),
    zgodnie z Device Object /3/0/13 Current Time.
    """
    # Specyfikacja zakłada wartość jako "time_t" (epoch seconds).
    return str(int(time.time()))


def read_device_value(path: str) -> Optional[bytes]:
    """
    Zwraca wartość zasobu Device Object jako bytes (text/plain).

    :param path: pełna ścieżka, np. "/3/0/0"
    :return: wartość jako bytes (np. b"Malaria Corp.") lub None jeśli brak zasobu
    """
    # Dynamiczny zasób: Current time /3/0/13
    if path == "/3/0/13":
        value = _read_current_time_epoch()
        print(f"DEBUG: Device /3/0/13 (Current time) -> {value}")
        return value.encode("utf-8")

    # Statyczne zasoby:
    if path in DEVICE_STATIC_VALUES:
        value = DEVICE_STATIC_VALUES[path]
        print(f"DEBUG: Device {path} -> {value}")
        return value.encode("utf-8")

    print(f"DEBUG: Device resource not defined for path {path}")
    return None


def get_all_device_resources() -> Dict[int, str]:
    """
    Zwraca wszystkie zasoby Device Object /3/0 jako słownik {resource_id: value}.
    Do użycia w TLV encoding.
    
    :return: słownik {0: "Manufacturer", 1: "Model", ...}
    """
    resources = {}
    
    # Dodaj wszystkie statyczne zasoby
    for path, value in DEVICE_STATIC_VALUES.items():
        # Wyciągnij resource_id z path "/3/0/X"
        parts = path.split('/')
        if len(parts) == 4 and parts[1] == '3' and parts[2] == '0':
            resource_id = int(parts[3])
            resources[resource_id] = value
    
    # Dodaj dynamiczny zasób: Current time (13)
    resources[13] = _read_current_time_epoch()
    
    return resources

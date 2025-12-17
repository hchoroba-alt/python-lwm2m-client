# models.py
#
# Ten plik zawiera WYŁĄCZNIE:
# - modele danych (dataclasses)
# - logikę zamiany danych → bytes
#
# NIE MA tu wysyłania requestów (POST/GET).
# Operacje sieciowe są w lwm2m_client.py

from dataclasses import dataclass, field
from typing import List, Optional, Union
import json
import time


# ============================================================
# 1) MODELE DANYCH DO REGISTER
# ============================================================

@dataclass
class DeviceObjectDefinition:
    # np. "</3303/0>"
    path: str


@dataclass
class DeviceObjectLinks:
    # lista obiektów zgłaszanych w REGISTER
    objects: List[DeviceObjectDefinition]

    @classmethod
    def from_string(cls, raw: str) -> "DeviceObjectLinks":
        # raw: "</1/1>,</3/0>,</3303/0>"
        return cls(objects=[DeviceObjectDefinition(obj) for obj in raw.split(",")])

    def to_registration_payload(self) -> bytes:
        # Payload REGISTER w link-format
        return ",".join([obj.path for obj in self.objects]).encode("utf-8")


def _default_links() -> "DeviceObjectLinks":
    return DeviceObjectLinks.from_string("</1/1>,</3/0>,</3303/0>")


@dataclass
class RegistrationParameters:
    # Parametry query string /rd?...
    device_name: str
    lifetime_seconds: int = 60
    lwm2m_version: str = "1.2"
    binding: str = "U"
    enable_queue_binding: bool = True
    object_links: DeviceObjectLinks = field(default_factory=_default_links)

    def register_path(self) -> str:
        # Buduje ścieżkę REGISTER
        return (
            f"/rd?ep={self.device_name}"
            f"&lt={self.lifetime_seconds}"
            f"&lwm2m={self.lwm2m_version}"
            f"&b={self.binding}&Q"
        )


# ============================================================
# 2) MODELE DANYCH DO SEND (LwM2M 1.2 Data Push)
#    Format: SenML JSON (application/senml+json)
# ============================================================

# Typ wartości, jaką można wysłać w SEND
SendValue = Union[int, float, str, bool]


@dataclass
class SenmlRecord:
    """
    Pojedynczy rekord SenML.

    Mapowanie:
    - n  → nazwa (u nas: ścieżka LwM2M, np. "/3303/0/5700")
    - v  → wartość numeryczna
    - vs → wartość string
    - vb → wartość boolean
    - t  → timestamp (sekundy od epoch)
    """
    n: str
    v: Optional[float] = None
    vs: Optional[str] = None
    vb: Optional[bool] = None
    t: Optional[int] = None

    @classmethod
    def from_lwm2m(cls, path: str, value: SendValue, timestamp: Optional[int] = None):
        # Upewniamy się, że path ma format "/x/y/z"
        if not path.startswith("/"):
            path = "/" + path

        if timestamp is None:
            timestamp = int(time.time())

        record = cls(n=path, t=timestamp)

        if isinstance(value, bool):
            record.vb = value
        elif isinstance(value, (int, float)):
            record.v = float(value)
        else:
            record.vs = str(value)

        return record

    def to_dict(self) -> dict:
        # Usuwamy pola None (SenML tego nie chce)
        d = {"n": self.n}
        if self.t is not None:
            d["t"] = self.t
        if self.v is not None:
            d["v"] = self.v
        if self.vs is not None:
            d["vs"] = self.vs
        if self.vb is not None:
            d["vb"] = self.vb
        return d


@dataclass
class SendPayload:
    """
    Payload SEND.
    Zawiera LISTĘ rekordów SenML.
    """
    records: List[SenmlRecord] = field(default_factory=list)

    def add(self, path: str, value: SendValue, timestamp: Optional[int] = None):
        # Dodaje nowy pomiar do payloadu
        self.records.append(
            SenmlRecord.from_lwm2m(path, value, timestamp)
        )

    def to_senml_json_bytes(self) -> bytes:
        """
        Zwraca payload gotowy do wysłania w SEND:
        Content-Format: application/senml+json
        """
        data = [record.to_dict() for record in self.records]
        return json.dumps(
            data,
            separators=(",", ":"),   # bez zbędnych spacji
            ensure_ascii=False
        ).encode("utf-8")

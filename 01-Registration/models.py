# models.py

from dataclasses import dataclass, field
from typing import List


@dataclass
class DeviceObjectDefinition:
    path: str


@dataclass
class DeviceObjectLinks:
    objects: List[DeviceObjectDefinition]

    @classmethod
    def from_string(cls, raw: str) -> "DeviceObjectLinks":
        return cls(objects=[DeviceObjectDefinition(obj) for obj in raw.split(",")])

    def to_registration_payload(self) -> bytes:
        # Np. </1/1>,</3/0>
        return ",".join([obj.path for obj in self.objects]).encode("utf-8")


def _default_links() -> "DeviceObjectLinks":
    # Domyślnie: LwM2M Server (/1/1) i Device (/3/0)
    return DeviceObjectLinks.from_string("</1/1>,</3/0>")


@dataclass
class RegistrationParameters:
    device_name: str
    lifetime_seconds: int = 60
    lwm2m_version: str = "1.2"
    binding: str = "U"
    enable_queue_binding: bool = True
    object_links: DeviceObjectLinks = field(default_factory=_default_links)

    def register_path(self) -> str:
        return (
            f"/rd?ep={self.device_name}"
            f"&lt={self.lifetime_seconds}"
            f"&lwm2m={self.lwm2m_version}"
            f"&b={self.binding}&Q"
        )

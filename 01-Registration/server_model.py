# server_model.py

from dataclasses import dataclass
from typing import Dict


@dataclass
class ServerResourceDef:
    path: str         # np. "/1/1/0"
    name: str         # nazwa, np. "Short Server ID"
    description: str  # opis
    datatype: str     # "integer", "string", "boolean", "none" (dla Execute)
    operations: str   # "R", "RW", "E" itd.


# Minimalny data model dla /1/1

SERVER_RESOURCES: Dict[str, ServerResourceDef] = {
    "/1/1/0": ServerResourceDef(
        path="/1/1/0",
        name="Short Server ID",
        description="Identifier of the LwM2M Server",
        datatype="integer",
        operations="R",
    ),
    "/1/1/1": ServerResourceDef(
        path="/1/1/1",
        name="Lifetime",
        description="Registration lifetime in seconds",
        datatype="integer",
        operations="R",
    ),
    "/1/1/7": ServerResourceDef(
        path="/1/1/7",
        name="Binding",
        description="Transport binding used (e.g. U, UQ, S)",
        datatype="string",
        operations="R",
    ),
    "/1/1/8": ServerResourceDef(
        path="/1/1/8",
        name="Registration Update Trigger",
        description="Trigger to send an Update registration message",
        datatype="none",
        operations="E",  # Execute
    ),
}
# Domyślne wartości dla /1/1
SHORT_SERVER_ID = 1
LIFETIME = 60        # powinno pasować do lt=60 w REGISTER
BINDING = "U"        # tak jak w RegistrationParameters.binding


# Prosty słownik z runtime values
SERVER_VALUES = {
    "/1/1/0": str(SHORT_SERVER_ID).encode("utf-8"),
    "/1/1/1": str(LIFETIME).encode("utf-8"),
    "/1/1/7": BINDING.encode("utf-8"),
}


def read_server_value(path: str) -> bytes | None:
    """Zwraca wartość zasobu /1/1/x jako bytes albo None, jeśli nie znamy."""
    return SERVER_VALUES.get(path)

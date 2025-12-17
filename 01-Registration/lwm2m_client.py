# lwm2m_client.py
"""
LwM2M Client (Malaria-debug) — uporządkowana wersja.

Cel pliku:
1) Trzymamy w JEDNYM miejscu opis tego, co urządzenie obsługuje (endpointy + operacje + formaty).
2) Z tego opisu budujemy routing (aiocoap Site).
3) Implementacje handlerów są poniżej, bez "rozsypywania" wiedzy o operacjach po całym pliku.

Konwencje:
- "DISCOVER" = GET z Accept: application/link-format (40) → zwracamy link-format.
- "READ"     = GET zwracający wartość zasobu (tu: text/plain).
- REGISTER/UPDATE to osobne requesty wychodzące (POST).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
import random

import aiocoap
from aiocoap import Message, POST, CONTENT
from aiocoap import resource as aiocoap_resource

from temperature_model import TEMPERATURE_RESOURCES, DISCOVER_3303_0_PAYLOAD, get_katowice_temperature
from server_model import read_server_value
from device_model import read_device_value, DISCOVER_3_0_PAYLOAD
from models import RegistrationParameters, SendPayload



# =============================================================================
# 1) Content-Formats (LwM2M/CoAP)
# =============================================================================

TEXT_PLAIN = aiocoap.numbers.media_types_rev["text/plain"]  # 0
APPLICATION_LINK_FORMAT = aiocoap.numbers.media_types_rev["application/link-format"]  # 40

# SEND payload formats (LwM2M 1.2)
SENML_JSON = aiocoap.numbers.media_types_rev.get("application/senml+json", 110)  # 110 = IANA


# (na przyszłość)
LWM2M_TLV = 11542   # application/vnd.oma.lwm2m+tlv
LWM2M_JSON = 11543  # application/vnd.oma.lwm2m+json


# =============================================================================
# 2) Jedno miejsce: katalog możliwości (endpointy + operacje + formaty)
# =============================================================================

@dataclass(frozen=True)
class Capability:
    """
    Opis "co umiem" dla danej ścieżki.
    """
    path: str
    ops: Tuple[str, ...]           # np. ("DISCOVER",) lub ("READ",)
    formats: Tuple[int, ...]       # np. (APPLICATION_LINK_FORMAT,) lub (TEXT_PLAIN,)


CAPABILITIES: Tuple[Capability, ...] = (
    # --- Root ---
    Capability("/", ("DISCOVER",), (APPLICATION_LINK_FORMAT,)),

    # --- Temperature (3303) ---
    Capability("/3303", ("DISCOVER",), (APPLICATION_LINK_FORMAT,)),
    Capability("/3303/0", ("DISCOVER",), (APPLICATION_LINK_FORMAT,)),
    Capability("/3303/0/5700", ("READ",), (TEXT_PLAIN,)),

    # --- Device (3) ---
    Capability("/3", ("DISCOVER",), (APPLICATION_LINK_FORMAT,)),
    Capability("/3/0", ("DISCOVER",), (APPLICATION_LINK_FORMAT,)),
    # Uwaga: /3/0/x to wiele zasobów — routing robimy poniżej, ale READ jest wspólny:
    Capability("/3/0/*", ("READ",), (TEXT_PLAIN,)),

    # --- Server (1) ---
    Capability("/1/1/*", ("READ",), (TEXT_PLAIN,)),
)


def print_capabilities() -> None:
    """Pomocniczo: szybkie wypisanie 'co obsługuję'."""
    print("=== CAPABILITIES (what device supports) ===")
    for c in CAPABILITIES:
        fmts = ", ".join(str(f) for f in c.formats)
        print(f"- {c.path:10s} ops={c.ops} formats={fmts}")
    print("==========================================")


# =============================================================================
# 3) Symulacja temperatury /3303/0/5700
# =============================================================================

T_MIN = 20.0
T_MAX = 26.0
T_STEP = 0.3
_current_temp: Optional[float] = None


def read_temperature_value() -> bytes:
    """Zwraca temperaturę z Katowic jako bytes, np. b'21.37'."""
    global _current_temp

    # Pobierz aktualną temperaturę z Katowic
    _current_temp = get_katowice_temperature()

    meta = TEMPERATURE_RESOURCES.get("/3303/0/5700")
    if meta:
        print(f"DEBUG: temperature ({meta.units}) -> {_current_temp:.2f}")
    else:
        print(f"DEBUG: temperature -> {_current_temp:.2f}")

    return f"{_current_temp:.2f}".encode("utf-8")


# =============================================================================
# 4) Handler-y (Resource classes): DISCOVER + READ
# =============================================================================

def _require_accept(request: Message, expected_format: int, *, path: str) -> Optional[Message]:
    """
    W LwM2M/CoAP serwer może wysłać Accept.
    Jeśli Accept jest ustawione i nie pasuje — zwracamy 4.06 Not Acceptable.
    """
    accept = request.opt.accept
    if accept is not None and accept != expected_format:
        print(f"DEBUG: {path} Accept={accept} not supported (expected {expected_format})")
        return Message(code=aiocoap.NOT_ACCEPTABLE)
    return None


class RootResource(aiocoap_resource.Resource):
    """
    GET /  (DISCOVER)
    Zwraca listę obiektów/instancji w application/link-format.
    """

    async def render_get(self, request: Message) -> Message:
        maybe = _require_accept(request, APPLICATION_LINK_FORMAT, path="/")
        if maybe:
            return maybe

        print("DEBUG: GET / (DISCOVER)")
        payload = b"</1/1>,</3/0>,</3303/0>"
        return Message(code=CONTENT, payload=payload, content_format=APPLICATION_LINK_FORMAT)


# ----- Temperature /3303 -----

class TemperatureObjectResource(aiocoap_resource.Resource):
    """
    GET /3303 (DISCOVER) → lista instancji obiektu Temperature.
    """

    async def render_get(self, request: Message) -> Message:
        maybe = _require_accept(request, APPLICATION_LINK_FORMAT, path="/3303")
        if maybe:
            return maybe

        print("DEBUG: GET /3303 (DISCOVER)")
        payload = b"</3303/0>"
        return Message(code=CONTENT, payload=payload, content_format=APPLICATION_LINK_FORMAT)


class TemperatureInstanceResource(aiocoap_resource.Resource):
    """
    GET /3303/0 (DISCOVER) → lista zasobów instancji 0.
    """

    async def render_get(self, request: Message) -> Message:
        maybe = _require_accept(request, APPLICATION_LINK_FORMAT, path="/3303/0")
        if maybe:
            return maybe

        print("DEBUG: GET /3303/0 (DISCOVER)")
        return Message(code=CONTENT, payload=DISCOVER_3303_0_PAYLOAD, content_format=APPLICATION_LINK_FORMAT)


class TemperatureValueResource(aiocoap_resource.Resource):
    """
    GET /3303/0/5700 (READ) → Sensor Value (float) w text/plain.
    """

    async def render_get(self, request: Message) -> Message:
        maybe = _require_accept(request, TEXT_PLAIN, path="/3303/0/5700")
        if maybe:
            return maybe

        print("DEBUG: GET /3303/0/5700 (READ)")
        value = read_temperature_value()
        return Message(code=CONTENT, payload=value, content_format=TEXT_PLAIN)


# ----- Device /3 -----

class DeviceObjectResource(aiocoap_resource.Resource):
    """
    GET /3 (DISCOVER) → lista instancji obiektu Device.
    """

    async def render_get(self, request: Message) -> Message:
        maybe = _require_accept(request, APPLICATION_LINK_FORMAT, path="/3")
        if maybe:
            return maybe

        print("DEBUG: GET /3 (DISCOVER)")
        payload = b"</3/0>"
        return Message(code=CONTENT, payload=payload, content_format=APPLICATION_LINK_FORMAT)


class DeviceInstanceResource(aiocoap_resource.Resource):
    """
    GET /3/0 (DISCOVER) → lista zasobów instancji Device.
    """

    async def render_get(self, request: Message) -> Message:
        maybe = _require_accept(request, APPLICATION_LINK_FORMAT, path="/3/0")
        if maybe:
            return maybe

        print("DEBUG: GET /3/0 (DISCOVER)")
        return Message(code=CONTENT, payload=DISCOVER_3_0_PAYLOAD, content_format=APPLICATION_LINK_FORMAT)


class DeviceValueResource(aiocoap_resource.Resource):
    """
    GET /3/0/x (READ) → pojedynczy zasób Device.
    """

    def __init__(self, path: str):
        super().__init__()
        self.path = path  # np. "/3/0/0"

    async def render_get(self, request: Message) -> Message:
        maybe = _require_accept(request, TEXT_PLAIN, path=self.path)
        if maybe:
            return maybe

        print(f"DEBUG: GET {self.path} (READ Device)")
        value = read_device_value(self.path)
        if value is None:
            return Message(code=aiocoap.NOT_FOUND)
        return Message(code=CONTENT, payload=value, content_format=TEXT_PLAIN)


# ----- Server /1 -----

class ServerValueResource(aiocoap_resource.Resource):
    """
    GET /1/1/x (READ) → zasób obiektu Server.
    """

    def __init__(self, path: str):
        super().__init__()
        self.path = path  # np. "/1/1/0"

    async def render_get(self, request: Message) -> Message:
        maybe = _require_accept(request, TEXT_PLAIN, path=self.path)
        if maybe:
            return maybe

        print(f"DEBUG: GET {self.path} (READ Server)")
        value = read_server_value(self.path)
        if value is None:
            return Message(code=aiocoap.NOT_FOUND)
        return Message(code=CONTENT, payload=value, content_format=TEXT_PLAIN)


# =============================================================================
# 5) Routing (jedno miejsce): ścieżka → handler
# =============================================================================

def build_site() -> aiocoap_resource.Site:
    """
    Tworzy aiocoap Site i podpina zasoby.
    To jest jedyne miejsce, gdzie decydujemy "co naprawdę istnieje" po stronie serwera.
    """
    root = aiocoap_resource.Site()

    # Root
    root.add_resource((), RootResource())

    # Temperature
    root.add_resource(("3303",), TemperatureObjectResource())
    root.add_resource(("3303", "0"), TemperatureInstanceResource())
    root.add_resource(("3303", "0", "5700"), TemperatureValueResource())

    # Device
    root.add_resource(("3",), DeviceObjectResource())
    root.add_resource(("3", "0"), DeviceInstanceResource())

    # Device resources (przykład: jeśli obsługujesz 0..16)
    # Jeśli masz inną listę, ustaw ją tu w jednym miejscu.
    for rid in range(0, 17):
        root.add_resource(("3", "0", str(rid)), DeviceValueResource(f"/3/0/{rid}"))

    # Server resources (przykład: jeśli obsługujesz 0..6)
    for rid in range(0, 7):
        root.add_resource(("1", "1", str(rid)), ServerValueResource(f"/1/1/{rid}"))

    return root


# =============================================================================
# 6) REGISTER / UPDATE (wychodzące requesty)
# =============================================================================

def make_register_message(server_addr: str, params: RegistrationParameters) -> Message:
    path = params.register_path()
    payload = params.object_links.to_registration_payload()

    print("=== REGISTER REQUEST ===")
    print("URI:", f"{server_addr}{path}")
    try:
        print("Payload:", payload.decode("utf-8"))
    except Exception:
        print("Payload (bytes):", payload)
    print("Content-Format: application/link-format (40)")
    print("========================")

    return Message(
        code=POST,
        uri=f"{server_addr}{path}",
        payload=payload,
        content_format=APPLICATION_LINK_FORMAT,
    )


def extract_location_path(response: Message) -> List[str]:
    """Zwraca np. ["rd", "Malaria"] (Location-Path z odpowiedzi REGISTER)."""
    return list(response.opt.location_path or ())


async def register(
    coap_client: aiocoap.Context, server: str, device_name: str
) -> Tuple[Message, List[str], RegistrationParameters]:
    print("DEBUG: starting register()")

    params = RegistrationParameters(device_name=device_name)
    register_message = make_register_message(server, params)

    print("DEBUG: sending REGISTER to", register_message.get_request_uri())
    response = await coap_client.request(register_message).response

    print("DEBUG: got response for REGISTER")
    print("Register response code:", response.code)
    print("Register response options:", response.opt)
    print("Register response payload:", response.payload)

    location = extract_location_path(response)
    print("Extracted Location-Path:", location)

    return response, location, params


def make_update_message(
    server_addr: str, device_location_parts: List[str], params: RegistrationParameters
) -> Message:
    path = "/" + "/".join(device_location_parts)
    uri = f"{server_addr}{path}?lt={params.lifetime_seconds}&b={params.binding}"

    print("=== UPDATE REQUEST ===")
    print("URI:", uri)
    print("Payload: (empty)")
    print("======================")

    return Message(code=POST, uri=uri)


async def send_update_loop(
    coap_client: aiocoap.Context,
    server: str,
    device_location_parts: List[str],
    params: RegistrationParameters,
) -> None:
    """
    Co połowę lifetime'u wysyłamy UPDATE (minimum 10s).
    """
    interval = max(10, params.lifetime_seconds // 2)
    print(f"DEBUG: starting UPDATE loop every {interval} seconds")

    while True:
        await asyncio.sleep(interval)
        print("DEBUG: sending UPDATE")
        update_msg = make_update_message(server, device_location_parts, params)
        resp = await coap_client.request(update_msg).response
        print("Update response code:", resp.code)
# =============================================================================
# 7) SEND (LwM2M 1.2 Data Push) — wychodzący request POST /dp
# =============================================================================

def make_send_message(server_addr: str, payload_bytes: bytes) -> Message:
    """
    Buduje wiadomość SEND.
    LwM2M 1.2: Client wysyła POST na /dp z payloadem (tu: SenML JSON).
    """
    uri = f"{server_addr}/dp"

    print("=== SEND REQUEST ===")
    print("URI:", uri)
    try:
        print("Payload:", payload_bytes.decode("utf-8"))
    except Exception:
        print("Payload (bytes):", payload_bytes)
    print("Content-Format: application/senml+json (110)")
    print("====================")

    return Message(
        code=POST,
        uri=uri,
        payload=payload_bytes,
        content_format=SENML_JSON,
    )


async def send(
    coap_client: aiocoap.Context,
    server: str,
    payload: SendPayload,
) -> Message:
    """
    Wysyła SEND do serwera.
    payload: obiekt z models.py (buduje bytes przez to_senml_json_bytes()).
    """
    payload_bytes = payload.to_senml_json_bytes()
    msg = make_send_message(server, payload_bytes)

    print("DEBUG: sending SEND to", msg.get_request_uri())
    response = await coap_client.request(msg).response
    print("Send response code:", response.code)
    return response

# lwm2m_client.py

from temperature_model import TEMPERATURE_RESOURCES, DISCOVER_3303_0_PAYLOAD
from server_model import read_server_value
from device_model import read_device_value, DISCOVER_3_0_PAYLOAD  

from typing import List, Tuple
import asyncio
import random

import aiocoap
from aiocoap import Message, POST, CONTENT
from aiocoap import resource as aiocoap_resource

from models import RegistrationParameters

# ---------- Content-Formats używane przez LwM2M ----------

TEXT_PLAIN = aiocoap.numbers.media_types_rev["text/plain"]                      # 0
APPLICATION_LINK_FORMAT = aiocoap.numbers.media_types_rev["application/link-format"]  # 40
# Dla pełnej specyfikacji mamy jeszcze TLV/JSON:
LWM2M_TLV = 11542   # application/vnd.oma.lwm2m+tlv
LWM2M_JSON = 11543  # application/vnd.oma.lwm2m+json

# ---------- PROSTA SYMULACJA TEMPERATURY /3303/0/5700 ----------

T_MIN = 20.0
T_MAX = 26.0
T_STEP = 0.3
_current_temp = None  # ostatnia wartość


def read_temperature_value() -> bytes:
    """Zwraca temperaturę jako bytes, np. b'21.37'."""
    global _current_temp

    if _current_temp is None:
        _current_temp = random.uniform(T_MIN, T_MAX)
    else:
        delta = random.uniform(-T_STEP, T_STEP)
        _current_temp = max(T_MIN, min(T_MAX, _current_temp + delta))

    # opcjonalnie użyjemy data modelu do debugowania
    meta = TEMPERATURE_RESOURCES.get("/3303/0/5700")
    if meta:
        print(f"DEBUG: temperature ({meta.units}) -> {_current_temp:.2f}")
    else:
        print(f"DEBUG: temperature -> {_current_temp:.2f}")

    return f"{_current_temp:.2f}".encode("utf-8")


# ---------- RESOURCE HANDLERS (READ / DISCOVER) ----------

class RootResource(aiocoap_resource.Resource):
    """
    Root LwM2M resource: DISCOVER na "/"
    Zwraca listę obiektów/instancji w application/link-format.
    """

    async def render_get(self, request: Message) -> Message:
        accept = request.opt.accept or APPLICATION_LINK_FORMAT
        print("DEBUG: GET /  (accept =", accept, ")")

        if accept == APPLICATION_LINK_FORMAT:
            # Klient ogłasza, że ma /1/1, /3/0, /3303/0 – to samo co w REGISTER
            payload = b"</1/1>,</3/0>,</3303/0>"
            return Message(
                code=CONTENT,
                payload=payload,
                content_format=APPLICATION_LINK_FORMAT,
            )

        # Inne formaty na razie nieobsługiwane na root
        return Message(code=aiocoap.NOT_ACCEPTABLE)


# ----- Temperature /3303 -----

class TemperatureObjectResource(aiocoap_resource.Resource):
    """
    /3303 – Discover instancji obiektu Temperature.
    """

    async def render_get(self, request: Message) -> Message:
        accept = request.opt.accept or APPLICATION_LINK_FORMAT
        print("DEBUG: GET /3303 (accept =", accept, ")")

        if accept == APPLICATION_LINK_FORMAT:
            # Mamy jedną instancję: /3303/0
            payload = b"</3303/0>"
            return Message(
                code=CONTENT,
                payload=payload,
                content_format=APPLICATION_LINK_FORMAT,
            )

        return Message(code=aiocoap.NOT_ACCEPTABLE)


class TemperatureInstanceResource(aiocoap_resource.Resource):
    """
    /3303/0 – Discover zasobów instancji 0.
    Na razie tylko 5700 (Sensor Value).
    """

    async def render_get(self, request: Message) -> Message:
        accept = request.opt.accept or APPLICATION_LINK_FORMAT
        print("DEBUG: GET /3303/0 (accept =", accept, ")")

        if accept == APPLICATION_LINK_FORMAT:
            # Używamy payloadu zdefiniowanego w temperature_model
            payload = DISCOVER_3303_0_PAYLOAD
            return Message(
                code=CONTENT,
                payload=payload,
                content_format=APPLICATION_LINK_FORMAT,
            )

        # Gdyby serwer chciał READ całej instancji w TLV/JSON,
        # tutaj powinnaś zbudować TLV / JSON z wszystkimi zasobami.
        return Message(code=aiocoap.NOT_ACCEPTABLE)


class TemperatureValueResource(aiocoap_resource.Resource):
    """
    /3303/0/5700 – Sensor Value (float), READ w text/plain.
    """

    async def render_get(self, request: Message) -> Message:
        accept = request.opt.accept or TEXT_PLAIN
        print("DEBUG: GET /3303/0/5700 (accept =", accept, ")")

        value = read_temperature_value()

        return Message(
            code=CONTENT,
            payload=value,
            content_format=TEXT_PLAIN,
        )


# ----- Server /1 -----

class ServerValueResource(aiocoap_resource.Resource):
    """
    /1/1/x – zasoby obiektu Server.
    Wartości są pobierane z server_model.read_server_value(path).
    """

    def __init__(self, path: str):
        super().__init__()
        self.path = path  # np. "/1/1/0"

    async def render_get(self, request: Message) -> Message:
        print(f"DEBUG: GET {self.path} (Server resource)")
        value = read_server_value(self.path)
        if value is not None:
            return Message(
                code=CONTENT,
                payload=value,
                content_format=TEXT_PLAIN,
            )

        print("DEBUG: no value defined for", self.path)
        return Message(code=aiocoap.NOT_FOUND)


# ----- Device /3 -----

class DeviceObjectResource(aiocoap_resource.Resource):
    """
    /3 – Device Object, Discover instancji.
    """

    async def render_get(self, request: Message) -> Message:
        accept = request.opt.accept
        print("DEBUG: GET /3 (accept =", accept, ")")
        print("DEBUG: Request options:", request.opt)

        # DISCOVER ma content-format 40, READ nie ma accept lub ma TLV/JSON
        if accept == APPLICATION_LINK_FORMAT:
            # DISCOVER
            payload = b"</3/0>"
            print("DEBUG: DISCOVER - zwracam link-format")
            return Message(
                code=CONTENT,
                payload=payload,
                content_format=APPLICATION_LINK_FORMAT,
            )
        
        # READ - nie obsługujemy, serwer powinien czytać pojedyncze zasoby
        print("DEBUG: READ operation - zwracam 4.06 Not Acceptable")
        return Message(code=aiocoap.NOT_ACCEPTABLE)


class DeviceInstanceResource(aiocoap_resource.Resource):
    """
    /3/0 – Discover zasobów Device Object instancja 0.
    DISCOVER_3_0_PAYLOAD powinien zawierać listę zasobów, np.:
    b"</3/0/0>,</3/0/1>,</3/0/2>,...</3/0/16>"
    """

    async def render_get(self, request: Message) -> Message:
        accept = request.opt.accept or APPLICATION_LINK_FORMAT
        print("DEBUG: GET /3/0 (accept =", accept, ")")

        if accept == APPLICATION_LINK_FORMAT:
            payload = DISCOVER_3_0_PAYLOAD
            return Message(
                code=CONTENT,
                payload=payload,
                content_format=APPLICATION_LINK_FORMAT,
            )

        # READ całej instancji w TLV/JSON można dodać później
        return Message(code=aiocoap.NOT_ACCEPTABLE)


class DeviceValueResource(aiocoap_resource.Resource):
    """
    /3/0/x – pojedyncze zasoby Device Object (Manufacturer, Model, itp.).
    Wartości są pobierane z device_model.read_device_value(path).
    """

    def __init__(self, path: str):
        super().__init__()
        self.path = path  # np. "/3/0/0" – Manufacturer

    async def render_get(self, request: Message) -> Message:
        print(f"DEBUG: GET {self.path} (Device resource)")
        value = read_device_value(self.path)
        if value is not None:
            return Message(
                code=CONTENT,
                payload=value,
                content_format=TEXT_PLAIN,
            )

        print("DEBUG: no value defined for", self.path)
        return Message(code=aiocoap.NOT_FOUND)


# ---------- REGISTER / UPDATE ----------

def make_register_message(server_addr: str, params: RegistrationParameters) -> Message:
    path = params.register_path()
    payload = params.object_links.to_registration_payload()

    print("=== REGISTER REQUEST ===")
    print("URI:", f"{server_addr}{path}")
    try:
        print("Payload:", payload.decode("utf-8"))
    except Exception:
        print("Payload (bytes):", payload)
    print("Content-Format: application/link-format")
    print("========================")

    return Message(
        code=POST,
        uri=f"{server_addr}{path}",
        payload=payload,
        content_format=APPLICATION_LINK_FORMAT,
    )


def extract_location_path(response: Message) -> List[str]:
    # Zwraca np. ["rd", "Malaria"]
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

    return Message(
        code=POST,
        uri=uri,
    )


async def send_update_loop(
    coap_client: aiocoap.Context,
    server: str,
    device_location_parts: List[str],
    params: RegistrationParameters,
):
    # co połowę lifetime'u wysyłamy UPDATE
    interval = max(10, params.lifetime_seconds // 2)
    print(f"DEBUG: starting UPDATE loop every {interval} seconds")

    while True:
        await asyncio.sleep(interval)
        print("DEBUG: sending UPDATE")
        update_msg = make_update_message(server, device_location_parts, params)
        resp = await coap_client.request(update_msg).response
        print("Update response code:", resp.code)

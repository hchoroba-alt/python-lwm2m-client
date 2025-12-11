# lwm2m_client.py

import asyncio
from typing import List, Tuple

from aiocoap import Context, Message, POST
from models import RegistrationParameters


def make_register_message(server_addr: str, params: RegistrationParameters) -> Message:
    path = params.register_path()
    print("DEBUG: register path:", path)
    msg = Message(
        code=POST,
        uri=f"{server_addr}{path}",
        payload=params.object_links.to_registration_payload(),
    )
    print("DEBUG: register payload:", msg.payload)
    return msg


def extract_location_path(response) -> List[str]:
    # Zwraca np. ["rd", "Malaria"]
    return list(response.opt.location_path or ())


async def register(
    coap_client: Context, server: str, device_name: str
) -> Tuple[object, List[str], RegistrationParameters]:
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
    # device_location_parts: ["rd", "Malaria"]
    path = "/" + "/".join(device_location_parts)
    uri = f"{server_addr}{path}?lt={params.lifetime_seconds}&b={params.binding}"
    print("DEBUG: UPDATE URI:", uri)
    msg = Message(
        code=POST,
        uri=uri,
    )
    return msg


async def send_update_loop(
    coap_client: Context,
    server: str,
    device_location_parts: List[str],
    params: RegistrationParameters,
):
    # prosty loop: co połowę lifetime'u wysyłamy UPDATE
    interval = max(10, params.lifetime_seconds // 2)
    print(f"DEBUG: starting UPDATE loop every {interval} seconds")

    while True:
        await asyncio.sleep(interval)
        print("DEBUG: sending UPDATE")
        update_msg = make_update_message(server, device_location_parts, params)
        resp = await coap_client.request(update_msg).response
        print("Update response code:", resp.code)

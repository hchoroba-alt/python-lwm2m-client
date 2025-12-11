from typing import List
import asyncio
from dataclasses import dataclass, field
from aiocoap import Context, Message, POST, DELETE

endpoint_name = "Malaria"
server_url = "coap://eu.iot.avsystem.cloud:5683"


# --- Modele obiektów LwM2M ---

@dataclass
class DeviceObjectDefinition:
    path: str


@dataclass
class DeviceObjectLinks:
    objects: List[DeviceObjectDefinition]

    @classmethod
    def from_string(cls, raw: str):
        return cls(objects=[DeviceObjectDefinition(object_def) for object_def in raw.split(",")])
    
    def to_registration_string(self) -> bytes:
        # Np. </1/1>,</3/0>
        return ",".join([obj.path for obj in self.objects]).encode("utf-8")
    
    @staticmethod
    def default_links():
        # Domyślnie: LwM2M Server (/1/1) i Device (/3/0)
        return DeviceObjectLinks.from_string("</1/1>,</3/0>")


@dataclass
class RegistrationParameters:
    device_name: str
    lifetime_seconds: int = 60
    lwm2m_version: str = "1.2"
    binding: str = "U"
    enable_queue_binding: bool = True
    # WAŻNE: podajemy FUNKCJĘ, nie wynik
    object_links: DeviceObjectLinks = field(default_factory=DeviceObjectLinks.default_links)

    def to_register_path(self) -> str:
        return (
            f"/rd?ep={self.device_name}"
            f"&lt={self.lifetime_seconds}"
            f"&lwm2m={self.lwm2m_version}"
            f"&b={self.binding}&Q"
        )


# --- Tworzenie wiadomości CoAP ---

def make_register_message(server_addr: str, parameters: RegistrationParameters) -> Message:
    path = parameters.to_register_path()
    print("DEBUG: register path:", path)
    msg = Message(
        code=POST,
        uri=f"{server_addr}{path}",
        payload=parameters.object_links.to_registration_string()
    )
    print("DEBUG: register payload:", msg.payload)
    return msg


def extract_location_path(response):
    # Zwraca listę segmentów Location-Path, np. ["rd", "123456"]
    return list(response.opt.location_path or ())


# --- Logika rejestracji ---

async def register(coap_client, server, device_name):
    print("DEBUG: starting register()")
    registration_params = RegistrationParameters(
        device_name=device_name,
    )
    register_message = make_register_message(
        server_addr=server,
        parameters=registration_params
    )

    print("DEBUG: sending REGISTER to", register_message.get_request_uri())
    response = await coap_client.request(register_message).response

    print("DEBUG: got response for REGISTER")
    print("Register response code:", response.code)
    print("Register response options:", response.opt)
    print("Register response payload:", response.payload)

    device_location_parts = extract_location_path(response)
    print("Extracted Location-Path:", device_location_parts)

    return response, device_location_parts


# --- Główna pętla programu ---

async def main():
    print("DEBUG: main() start")
    try:
        coap_client = await Context.create_client_context()
        print("DEBUG: CoAP client context created")
        print("Making request to server to register device")

        response, device_location_parts = await register(coap_client, server_url, endpoint_name)

        if not response.code.is_successful():
            print("Registration failed, code:", response.code)
            return

        if not device_location_parts:
            print("No Location-Path in register response, cannot continue.")
            return

        print("Device registered successfully, keeping client alive.")
        print("Location-Path:", device_location_parts)

        # Trzymamy klienta przy życiu, żeby Device Center mógł robić Discover/Read
        while True:
            await asyncio.sleep(60)

    except Exception as e:
        print(f"Client error when working with LwM2M server at {server_url}")
        print("Exception:", e)

    finally:
        print("DEBUG: main() end")


if __name__ == "__main__":
    print("DEBUG: module imported, starting asyncio.run(main())")
    asyncio.run(main())

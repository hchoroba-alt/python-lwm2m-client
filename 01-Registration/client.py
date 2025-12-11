from typing import List
import asyncio
from dataclasses import dataclass, field
from aiocoap import Context, Message, POST, DELETE

endpoint_name = "Malaria"
server_url = "coap://eu.iot.avsystem.cloud:5683"


@dataclass
class DeviceObjectDefinition:
    path: str


@dataclass
class DeviceObjectLinks:
    objects: List[DeviceObjectDefinition]

    @classmethod
    def from_string(cls, raw: str):
        return cls(objects=[DeviceObjectDefinition(object_def) for object_def in raw.split(",")])
    
    def to_registration_string(self):
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
    # ważne: przekazujemy FUNKCJĘ, nie wynik funkcji
    object_links: DeviceObjectLinks = field(default_factory=DeviceObjectLinks.default_links)

    def to_register_path(self):
        return (
            f"/rd?ep={self.device_name}"
            f"&lt={self.lifetime_seconds}"
            f"&lwm2m={self.lwm2m_version}"
            f"&b={self.binding}&Q"
        )


def make_register_path(device_name, lifetime_seconds="60", lwm2m_version="1.2", binding="U"):
    return f"/rd?ep={device_name}&lt={lifetime_seconds}&lwm2m={lwm2m_version}&b={binding}&Q"


def make_register_message(server_addr, parameters: RegistrationParameters):
    path = parameters.to_register_path()
    msg = Message(
        code=POST,
        uri=f"{server_addr}{path}",
        payload=parameters.object_links.to_registration_string()
    )
    return msg


def make_deregister_path(device_location_parts):
    assert len(device_location_parts) > 1
    return "/" + "/".join(device_location_parts)


def make_deregister_message(server_addr, device_location_parts):
    path = make_deregister_path(device_location_parts)
    msg = Message(
        code=DELETE,
        uri=f"{server_addr}{path}"
    )
    return msg


def extract_location_path(response):
    # Zwraca listę segmentów Location-Path, np. ["rd", "123456"]
    return list(response.opt.location_path or ())


async def register(coap_client, server, device_name):
    registration_params = RegistrationParameters(
        device_name=device_name,
    )
    register_message = make_register_message(
        server_addr=server,
        parameters=registration_params
    )

    print("Register request URI:", register_message.get_request_uri())
    print("Register request payload:", register_message.payload)

    response = await coap_client.request(register_message).response

    # Debug odpowiedzi serwera
    print("Register response code:", response.code)
    print("Register response options:", response.opt)
    print("Register response payload:", response.payload)

    device_location_parts = extract_location_path(response)
    print("Extracted Location-Path:", device_location_parts)

    return response, device_location_parts


async def main():
    try:
        coap_client = await Context.create_client_context()
        print("Making request to server to register device")

        response, device_location_parts = await register(coap_client, server_url, endpoint_name)

        # Jeśli rejestracja się nie udała – nie próbujemy deregister
        if not response.code.is_successful():
            print("Registration failed, skipping deregister.")
            return

        # Jeśli nie ma Location-Path – też nie próbujemy deregister
        if not device_location_parts:
            print("No Location-Path in register response, skipping deregister.")
            return

        print(f"Deregistering device at location {device_location_parts}")
        deregister_response = await coap_client.request(
            make_deregister_message(server_url, device_location_parts)
        ).response

        print(f"Response for deregister operation: {deregister_response.code}\n"
              f"{deregister_response.opt}\n{deregister_response.payload}")

    except Exception as e:
        print(f"Failed to register/deregister device in LwM2M server at {server_url}")
        print(e)

    else:
        print("Successfully completed device operations")


if __name__ == "__main__":
    asyncio.run(main())

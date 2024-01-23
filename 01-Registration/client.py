from typing import List
import asyncio
from dataclasses import dataclass
from aiocoap import Context, Message, POST, DELETE

endpoint_name = "urn:nai:no-sec@mikegpl.dev"

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
        return str.encode(",".join([obj.path for obj in self.objects]))
    
    @staticmethod
    def default_links():
        return DeviceObjectLinks.from_string("</1/1>,</3/0>")

@dataclass
class RegistrationParameters:
    device_name: str
    lifetime_seconds: int = 60
    lwm2m_version: str = 1.2
    binding = "U"
    enable_queue_binding: bool = True
    object_links: DeviceObjectLinks = DeviceObjectLinks.default_links()

    def to_register_path(self):
        return f"/rd?ep={self.device_name}&lt={self.lifetime_seconds}&lwm2m={self.lwm2m_version}&b={self.binding}&Q"


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

def response_options_as_list(coap_response):
    return [str(option) for option in coap_response.opt.option_list()]


async def register(coap_client, server, device_name):
    registration_params = RegistrationParameters(
        device_name=device_name,
    )
    register_message = make_register_message(
        server_addr=server,
        parameters=registration_params
    )
    response = await coap_client.request(register_message).response
    return response, response_options_as_list(response)


async def main():
    try:
        coap_client = await Context.create_client_context()
        print("Making request to server to register device")
        (_, device_location_parts) = await register(coap_client, server_url, endpoint_name)
        print(f"Deregistering device at location {device_location_parts}")
        deregister_response = await coap_client.request(make_deregister_message(server_url, device_location_parts)).response
        print(f"Response for deregister operation: {deregister_response.code}\n{deregister_response.opt}\n{deregister_response.payload}")
    except Exception as e:
        print(
            f"Failed to register/deregister device in LwM2M server at {server_url}")
        print(e)
    else:
        print(f"Succesfully completed device operations")

if __name__ == "__main__":
    asyncio.run(main())

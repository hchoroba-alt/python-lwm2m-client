import asyncio
from aiocoap import Context,Message, POST

endpoint_name = "urn:nai:no-sec@mikegpl.dev"

server_url = "coap://eu.iot.avsystem.cloud:5683"

def make_register_path(device_name, lifetime_seconds="60", lwm2m_version="1.2", binding="U"):
    return f"/rd?ep={device_name}&lt={lifetime_seconds}&lwm2m={lwm2m_version}&b={binding}&Q"

def make_register_message(server_addr, device_name, lifetime_seconds="60", lwm2m_version="1.2", binding="U"):
    path = make_register_path(device_name, lifetime_seconds, lwm2m_version, binding)
    msg = Message(
        code=POST,
        uri=f"{server_addr}{path}"
    )
    return msg


async def register(server, device_name):
    client_context = await Context.create_client_context()
    register_message = make_register_message(
        server_addr=server,
        device_name=device_name
    )
    return await client_context.request(register_message).response

async def main():
    try:
        print("Making request to server to register device")
        response = await register(server_url, endpoint_name)
    except Exception as e:
        print(f"Failed to register device in LwM2M server at {server_url}")
        print(e)
    else:
        print(f"Response from server: {response.code}\n{response.payload}")

asyncio.run(main())
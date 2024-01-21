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

def response_options_as_list(coap_response):
    return [str(option) for option in coap_response.opt.option_list()]


async def register(coap_client, server, device_name):
    register_message = make_register_message(
        server_addr=server,
        device_name=device_name
    )
    response = await coap_client.request(register_message).response
    return response, response_options_as_list(response)

async def main():
    try:
        coap_client = await Context.create_client_context()
        print("Making request to server to register device")
        register_response = await register(coap_client, server_url, endpoint_name)
    except Exception as e:
        print(f"Failed to register/deregister device in LwM2M server at {server_url}")
        print(e)
    else:
        print(f"Response from server: {register_response[0].code}\n{register_response[1]}")

asyncio.run(main())
# main.py

import asyncio
from aiocoap import Context

from config import endpoint_name, server_url
from lwm2m_client import register, send_update_loop


async def main():
    print("DEBUG: main() start")
    coap_client = await Context.create_client_context()
    print("DEBUG: CoAP client context created")
    print("Making request to server to register device")

    response, location, params = await register(coap_client, server_url, endpoint_name)

    if not response.code.is_successful():
        print("Registration failed, code:", response.code)
        return

    if not location:
        print("No Location-Path in register response, cannot continue.")
        return

    print("Device registered successfully.")
    print("Location-Path:", location)
    print("Starting UPDATE loop to keep device registered.")

    await send_update_loop(coap_client, server_url, location, params)


if __name__ == "__main__":
    print("DEBUG: module main imported, starting asyncio.run(main())")
    asyncio.run(main())

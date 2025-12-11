# main.py
import asyncio
from aiocoap import Context, resource

from config import endpoint_name, server_url
from lwm2m_client import register, send_update_loop, Lwm2mResource


async def main():
    print("DEBUG: main() start")

    # --- CoAP client used for REGISTER + UPDATE ---
    coap_client = await Context.create_client_context()
    print("DEBUG: CoAP client context created")

    # --- CoAP server used for READ requests ---
    root = resource.Site()

    # Discover dla instancji 0
    root.add_resource(('3303', '0'), Lwm2mResource("/3303/0"))

    # Register temperature READ handler for /3303/0/5700
    root.add_resource(('3303', '0', '5700'), Lwm2mResource("/3303/0/5700"))

    # Start local CoAP server in background
    asyncio.create_task(Context.create_server_context(root))
    print("DEBUG: CoAP server for READ started")

    # --- REGISTER operation ---
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

    # --- UPDATE LOOP (keeps device alive) ---
    await send_update_loop(coap_client, server_url, location, params)


if __name__ == "__main__":
    print("DEBUG: module main imported, starting asyncio.run(main())")
    asyncio.run(main())

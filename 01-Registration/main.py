# main.py

import asyncio
from aiocoap import Context  # type: ignore
from aiocoap import resource as aiocoap_resource

from config import endpoint_name, server_url
from models import SendPayload
from lwm2m_client import (
    register,
    send_update_loop,
    send,  # <-- NOWE (SEND)
    read_temperature_value,  # <-- NOWE (bierzemy temp tak samo jak READ)
    RootResource,
    TemperatureObjectResource,
    TemperatureInstanceResource,
    TemperatureValueResource,
    ServerValueResource,
    DeviceObjectResource,
    DeviceInstanceResource,
    DeviceValueResource,
)


async def main():
    print("DEBUG: main() start")

    # --- CoAP server used for READ + DISCOVER ---
    root = aiocoap_resource.Site()

    # Root "/" – Discover całego klienta
    root.add_resource(('',), RootResource())

    # Obiekt Temperature /3303
    root.add_resource(('3303',), TemperatureObjectResource())
    root.add_resource(('3303', '0'), TemperatureInstanceResource())
    root.add_resource(('3303', '0', '5700'), TemperatureValueResource())

    # Obiekt Server /1/1/x
    root.add_resource(('1', '1', '0'), ServerValueResource("/1/1/0"))
    root.add_resource(('1', '1', '1'), ServerValueResource("/1/1/1"))
    root.add_resource(('1', '1', '7'), ServerValueResource("/1/1/7"))

    # Obiekt Device /3
    root.add_resource(('3',), DeviceObjectResource())
    root.add_resource(('3', '0'), DeviceInstanceResource())

    # Przykładowe zasoby Device /3/0/x
    root.add_resource(('3', '0', '0'), DeviceValueResource("/3/0/0"))
    root.add_resource(('3', '0', '1'), DeviceValueResource("/3/0/1"))
    root.add_resource(('3', '0', '2'), DeviceValueResource("/3/0/2"))
    root.add_resource(('3', '0', '3'), DeviceValueResource("/3/0/3"))
    root.add_resource(('3', '0', '6'), DeviceValueResource("/3/0/6"))
    root.add_resource(('3', '0', '7'), DeviceValueResource("/3/0/7"))
    root.add_resource(('3', '0', '8'), DeviceValueResource("/3/0/8"))
    root.add_resource(('3', '0', '9'), DeviceValueResource("/3/0/9"))
    root.add_resource(('3', '0', '10'), DeviceValueResource("/3/0/10"))
    root.add_resource(('3', '0', '11'), DeviceValueResource("/3/0/11"))
    root.add_resource(('3', '0', '13'), DeviceValueResource("/3/0/13"))
    root.add_resource(('3', '0', '14'), DeviceValueResource("/3/0/14"))
    root.add_resource(('3', '0', '15'), DeviceValueResource("/3/0/15"))
    root.add_resource(('3', '0', '16'), DeviceValueResource("/3/0/16"))

    # --- ONE CONTEXT: server + client on same port ---
    coap_client = await Context.create_server_context(root)
    print("DEBUG: CoAP server & client context created (one context)")

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

    # --- SEND LOOP (LwM2M 1.2 Data Push) ---
    async def send_loop():
        while True:
            payload = SendPayload()
            temp = float(read_temperature_value().decode("utf-8"))
            payload.add("/3303/0/5700", temp)
            await send(coap_client, server_url, payload)
            await asyncio.sleep(30)

    asyncio.create_task(send_loop())
    print("DEBUG: SEND loop started (every 30 seconds)")

    # --- UPDATE LOOP (keeps device alive) ---
    await send_update_loop(coap_client, server_url, location, params)


if __name__ == "__main__":
    print("DEBUG: module main imported, starting asyncio.run(main())")
    asyncio.run(main())

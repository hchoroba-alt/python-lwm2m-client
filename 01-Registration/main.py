# main.py

import asyncio
from aiocoap import Context
from aiocoap import resource as aiocoap_resource

from config import endpoint_name, server_url
from lwm2m_client import (
    register,
    send_update_loop,
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

    # --- CoAP client used for REGISTER + UPDATE ---
    coap_client = await Context.create_client_context()
    print("DEBUG: CoAP client context created")

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

    # Przykładowe zasoby Device /3/0/x (Manufacturer, Model, Serial, Firmware, itp.)
    root.add_resource(('3', '0', '0'), DeviceValueResource("/3/0/0"))   # Manufacturer
    root.add_resource(('3', '0', '1'), DeviceValueResource("/3/0/1"))   # Model number
    root.add_resource(('3', '0', '2'), DeviceValueResource("/3/0/2"))   # Serial number
    root.add_resource(('3', '0', '3'), DeviceValueResource("/3/0/3"))   # Firmware version
    root.add_resource(('3', '0', '6'), DeviceValueResource("/3/0/6"))   # Available power sources
    root.add_resource(('3', '0', '7'), DeviceValueResource("/3/0/7"))   # Power source voltage
    root.add_resource(('3', '0', '8'), DeviceValueResource("/3/0/8"))   # Power source current
    root.add_resource(('3', '0', '9'), DeviceValueResource("/3/0/9"))   # Battery level
    root.add_resource(('3', '0', '10'), DeviceValueResource("/3/0/10")) # Memory free
    root.add_resource(('3', '0', '11'), DeviceValueResource("/3/0/11")) # Error code (aktualny)
    root.add_resource(('3', '0', '13'), DeviceValueResource("/3/0/13")) # Current time
    root.add_resource(('3', '0', '14'), DeviceValueResource("/3/0/14")) # UTC offset
    root.add_resource(('3', '0', '15'), DeviceValueResource("/3/0/15")) # Timezone
    root.add_resource(('3', '0', '16'), DeviceValueResource("/3/0/16")) # Supported binding and modes
    # Możesz dodać kolejne: 17, 18, 19, 20, 21 itd. jeśli chcesz.

    # Start local CoAP server (background task)
    asyncio.create_task(Context.create_server_context(root))
    print("DEBUG: CoAP server for READ + DISCOVER started")

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

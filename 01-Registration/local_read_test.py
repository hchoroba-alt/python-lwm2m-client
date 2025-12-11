import asyncio
from aiocoap import Context, Message, GET

async def test_read(uri: str):
    print(f"\n=== TEST READ {uri} ===")
    protocol = await Context.create_client_context()
    try:
        request = Message(code=GET, uri=uri)
        response = await protocol.request(request).response
        print("Response code:", response.code)
        print("Response payload:", response.payload)
    except Exception as e:
        print("ERROR:", e)

async def main():
    # dopasuj ścieżki do tego, co mamy zaimplementowane
    await test_read("coap://localhost:5683/3303/0/5700")
    await test_read("coap://localhost:5683/1/1/0")

if __name__ == "__main__":
    asyncio.run(main())

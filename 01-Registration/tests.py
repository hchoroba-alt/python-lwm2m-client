from client import make_register_path, make_register_message
from aiocoap import POST


def test_register_path():
    assert make_register_path(device_name="urn:nai:no-sec@mikegpl.dev",
                              lifetime_seconds="60",
                              lwm2m_version="1.2",
                              binding="U") == "/rd?ep=urn:nai:no-sec@mikegpl.dev&lt=60&lwm2m=1.2&b=U&Q", "Register path for COAP transport should follow 6.4.3 section of https://openmobilealliance.org/RELEASE/LightweightM2M/V1_1-20180612-C/OMA-TS-LightweightM2M_Transport-V1_1-20180612-C.pdf"


def test_register_message():
    msg = make_register_message(
        server_addr="coap://eu.iot.avsystem.cloud",
        device_name="urn:nai:no-sec@mikegpl.dev",
        lifetime_seconds="60",
        lwm2m_version="1.2",
        binding="U") 
    
    assert msg.code == POST 
    assert "coap://eu.iot.avsystem.clsoud" in msg.get_request_uri(), f"Server should be included in request URI: {msg.get_request_uri()}"

test_register_path()
test_register_message()

print("Tests passed")

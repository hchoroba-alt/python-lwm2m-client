# tlv_encoder.py
"""
Encoder dla formatu LwM2M TLV (Type-Length-Value).

Format TLV zgodnie z OMA LwM2M specyfikacją:
- Type (6-8 bitów): określa typ elementu i długość pól Length i Identifier
- Identifier: ID zasobu/instancji
- Length: długość wartości
- Value: surowe dane

Uproszczona implementacja dla podstawowych przypadków:
- Resource Instance: pojedyncza wartość zasobu
- Multiple Resources: zasób z wieloma instancjami
- Object Instance: pełna instancja obiektu z zasobami
"""

from typing import Dict, Union, List
import struct


# Typy TLV (Type Identifier byte)
class TLVType:
    """
    Bits 7-6: Type of Identifier
      00 = Object Instance
      01 = Resource Instance with value
      10 = Multiple Resource
      11 = Resource with value
    
    Bit 5: Length of Identifier
      0 = 8 bits
      1 = 16 bits
    
    Bits 4-3: Type of Length
      00 = no length field, value follows Identifier field
      01 = length field is 8 bits
      10 = length field is 16 bits
      11 = length field is 24 bits
    
    Bits 2-0: Length (gdy Type of Length = 00)
      Value 0-7 reprezentuje długość
    """
    OBJECT_INSTANCE = 0b00_0_00_000  # 0x00
    RESOURCE_VALUE = 0b11_0_00_000   # 0xC0
    RESOURCE_INSTANCE = 0b01_0_00_000  # 0x40
    MULTIPLE_RESOURCE = 0b10_0_00_000  # 0x80


def _encode_tlv_header(tlv_type: int, identifier: int, length: int) -> bytes:
    """
    Koduje nagłówek TLV (Type, Identifier, Length).
    
    Uproszczona wersja:
    - Identifier zawsze 8-bit (0-255)
    - Length:
      - jeśli length <= 7: kodujemy w Type byte (bits 2-0)
      - jeśli length <= 255: Type of Length = 01 (8-bit length field)
      - jeśli length <= 65535: Type of Length = 10 (16-bit length field)
    """
    # Identifier 8-bit (bit 5 = 0)
    identifier_16bit = False
    
    if length <= 7:
        # Length w Type byte (bits 2-0)
        type_byte = tlv_type | length
        if identifier_16bit:
            return struct.pack('!BH', type_byte, identifier)
        else:
            return struct.pack('!BB', type_byte, identifier)
    
    elif length <= 255:
        # 8-bit length field (bits 4-3 = 01)
        type_byte = tlv_type | (0b01 << 3)
        if identifier_16bit:
            return struct.pack('!BHB', type_byte, identifier, length)
        else:
            return struct.pack('!BBB', type_byte, identifier, length)
    
    elif length <= 65535:
        # 16-bit length field (bits 4-3 = 10)
        type_byte = tlv_type | (0b10 << 3)
        if identifier_16bit:
            return struct.pack('!BHH', type_byte, identifier, length)
        else:
            return struct.pack('!BBH', type_byte, identifier, length)
    
    else:
        # 24-bit length field (bits 4-3 = 11)
        type_byte = tlv_type | (0b11 << 3)
        length_bytes = struct.pack('!I', length)[1:]  # Bierzemy 3 bajty
        if identifier_16bit:
            return struct.pack('!BH', type_byte, identifier) + length_bytes
        else:
            return struct.pack('!BB', type_byte, identifier) + length_bytes


def encode_resource_tlv(resource_id: int, value: Union[str, int, float, bytes]) -> bytes:
    """
    Koduje pojedynczy zasób jako TLV Resource with value.
    
    :param resource_id: ID zasobu (np. 0 dla /3/0/0, 5700 dla /3303/0/5700)
    :param value: wartość zasobu (string, int, float, bytes)
    :return: zakodowane TLV
    """
    # Konwertuj wartość na bytes
    if isinstance(value, bytes):
        value_bytes = value
    elif isinstance(value, str):
        value_bytes = value.encode('utf-8')
    elif isinstance(value, int):
        # Integer jako 4-byte signed
        value_bytes = struct.pack('!i', value)
    elif isinstance(value, float):
        # Float jako 4-byte float
        value_bytes = struct.pack('!f', value)
    else:
        value_bytes = str(value).encode('utf-8')
    
    header = _encode_tlv_header(TLVType.RESOURCE_VALUE, resource_id, len(value_bytes))
    return header + value_bytes


def encode_instance_tlv(instance_id: int, resources: Dict[int, Union[str, int, float, bytes]]) -> bytes:
    """
    Koduje instancję obiektu jako TLV Object Instance z zagnieżdżonymi zasobami.
    
    :param instance_id: ID instancji (np. 0 dla /3/0)
    :param resources: słownik {resource_id: value}
    :return: zakodowane TLV
    """
    # Koduj wszystkie zasoby
    resources_tlv = b''
    for res_id, value in sorted(resources.items()):
        resources_tlv += encode_resource_tlv(res_id, value)
    
    # Koduj Object Instance z zagnieżdżonymi zasobami
    header = _encode_tlv_header(TLVType.OBJECT_INSTANCE, instance_id, len(resources_tlv))
    return header + resources_tlv


def encode_multiple_resources_tlv(resource_id: int, values: List[Union[str, int, float, bytes]]) -> bytes:
    """
    Koduje zasób z wieloma instancjami (Multiple Resource).
    
    :param resource_id: ID zasobu
    :param values: lista wartości (każda jako osobna instancja)
    :return: zakodowane TLV
    """
    # Koduj każdą instancję
    instances_tlv = b''
    for idx, value in enumerate(values):
        # Resource Instance
        if isinstance(value, bytes):
            value_bytes = value
        elif isinstance(value, str):
            value_bytes = value.encode('utf-8')
        elif isinstance(value, int):
            value_bytes = struct.pack('!i', value)
        elif isinstance(value, float):
            value_bytes = struct.pack('!f', value)
        else:
            value_bytes = str(value).encode('utf-8')
        
        header = _encode_tlv_header(TLVType.RESOURCE_INSTANCE, idx, len(value_bytes))
        instances_tlv += header + value_bytes
    
    # Opakowujemy w Multiple Resource
    header = _encode_tlv_header(TLVType.MULTIPLE_RESOURCE, resource_id, len(instances_tlv))
    return header + instances_tlv


# ===== Helpery do szybkiego budowania payloadów =====

def build_device_instance_tlv(device_values: Dict[int, Union[str, int, float, bytes]]) -> bytes:
    """
    Buduje TLV dla instancji Device Object /3/0.
    
    :param device_values: słownik {resource_id: value}, np. {0: "Manufacturer", 1: "Model", ...}
    :return: zakodowane TLV dla instancji
    """
    return encode_instance_tlv(0, device_values)


def build_server_instance_tlv(server_values: Dict[int, Union[str, int, float, bytes]]) -> bytes:
    """
    Buduje TLV dla instancji Server Object /1/1.
    
    :param server_values: słownik {resource_id: value}, np. {0: 1, 1: 60, 7: "U"}
    :return: zakodowane TLV dla instancji
    """
    return encode_instance_tlv(1, server_values)


def build_temperature_instance_tlv(temperature_values: Dict[int, Union[str, int, float, bytes]]) -> bytes:
    """
    Buduje TLV dla instancji Temperature Sensor /3303/0.
    
    :param temperature_values: słownik {resource_id: value}, np. {5700: 24.5}
    :return: zakodowane TLV dla instancji
    """
    return encode_instance_tlv(0, temperature_values)

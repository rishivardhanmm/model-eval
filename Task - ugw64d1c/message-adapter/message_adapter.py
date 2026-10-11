
import struct

def send_message(message: str) -> bytes:
    """Build a frame: 4-byte big-endian length + UTF-8 payload."""
     # BUG: counts characters, not UTF-8 bytes
    payload = message.encode("utf-8")
    length = len(message) 

    return struct.pack(">I", length) + payload



def decode_messages(data: bytes) -> tuple[list[str], int]:
    """Decode complete frames and return messages and bytes consumed."""
    messages = []
    offset = 0

    while offset < len(data):
        if len(data) - offset < 4:
            raise ValueError("Truncated frame header")

        length = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4

        if len(data) - offset < length:
            raise ValueError("Truncated frame payload")

        payload = data[offset:offset + length]
        offset += length
        messages.append(payload.decode("utf-8"))

    return messages, offset

from pathlib import Path

from PIL import Image

from crypto import decrypt_bytes
from utils import (
    LENGTH_PREFIX_SIZE,
    PAYLOAD_TYPE_TEXT,
    calculate_capacity,
    parse_payload,
)


def decode_message(image_path, end_marker):
    end_marker_bytes = end_marker.encode("utf-8")

    with Image.open(image_path) as image:
        rgb_image = image.convert("RGB")

    data_bytes = bytearray()
    current_bits = []

    # Read bits from the least significant bit of each RGB channel.
    for pixel in rgb_image.getdata():
        for channel in pixel[:3]:
            current_bits.append(str(channel & 1))
            if len(current_bits) == 8:
                byte = int("".join(current_bits), 2)
                data_bytes.append(byte)
                current_bits.clear()

                if len(data_bytes) >= len(end_marker_bytes):
                    if data_bytes[-len(end_marker_bytes) :] == end_marker_bytes:
                        message_bytes = data_bytes[: -len(end_marker_bytes)]
                        return message_bytes.decode("utf-8", errors="replace")

    raise ValueError("No hidden message found. The end marker was not detected.")


def _lsb_bit_stream(rgb_image):
    for pixel in rgb_image.getdata():
        for channel in pixel[:3]:
            yield channel & 1


def _read_bytes(bit_iter, byte_count):
    data = bytearray()
    for _ in range(byte_count):
        bits = []
        for _ in range(8):
            try:
                bits.append(str(next(bit_iter)))
            except StopIteration as exc:
                raise ValueError("Hidden data is corrupted or incomplete.") from exc
        data.append(int("".join(bits), 2))
    return bytes(data)


def decode_payload_bytes(image_path):
    image_path = Path(image_path)
    if image_path.suffix.lower() != ".png":
        raise ValueError("Please provide a PNG image.")

    with Image.open(image_path) as image:
        rgb_image = image.convert("RGB")

    capacity_bits = calculate_capacity(rgb_image)
    max_payload_bytes = capacity_bits // 8 - LENGTH_PREFIX_SIZE
    if max_payload_bytes <= 0:
        raise ValueError("Image is too small to contain hidden data.")

    bit_iter = _lsb_bit_stream(rgb_image)
    length_bytes = _read_bytes(bit_iter, LENGTH_PREFIX_SIZE)
    payload_length = int.from_bytes(length_bytes, "big")

    if payload_length <= 0 or payload_length > max_payload_bytes:
        raise ValueError("No valid hidden payload found in this image.")

    payload_bytes = _read_bytes(bit_iter, payload_length)
    return payload_bytes


def extract_encrypted_text(image_path, password):
    payload_bytes = decode_payload_bytes(image_path)
    payload_type, metadata, encrypted_bytes = parse_payload(payload_bytes)

    if payload_type != PAYLOAD_TYPE_TEXT:
        raise ValueError("Hidden data is not an encrypted text message.")

    decrypted_bytes = decrypt_bytes(encrypted_bytes, password)
    encoding = metadata.get("encoding", "utf-8")
    return decrypted_bytes.decode(encoding, errors="replace")

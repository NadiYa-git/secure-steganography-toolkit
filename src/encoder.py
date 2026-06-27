from pathlib import Path

from PIL import Image

from crypto import encrypt_bytes
from utils import (
    LENGTH_PREFIX_SIZE,
    PAYLOAD_TYPE_TEXT,
    bytes_to_bits,
    build_payload,
    calculate_capacity,
    generate_timestamped_filename,
    text_to_binary,
)


def encode_message(input_path, output_dir, secret_text, end_marker):
    with Image.open(input_path) as image:
        rgb_image = image.convert("RGB")

    message_bits = text_to_binary(secret_text + end_marker)
    capacity_bits = calculate_capacity(rgb_image)

    if len(message_bits) > capacity_bits:
        raise ValueError(
            "Message is too long for this image. Use a larger image or a shorter message."
        )

    pixels = list(rgb_image.getdata())
    new_pixels = []
    bit_index = 0

    # Replace the least significant bit of each RGB channel with message bits.
    for pixel in pixels:
        channels = list(pixel)
        for i in range(3):
            if bit_index < len(message_bits):
                channels[i] = (channels[i] & ~1) | int(message_bits[bit_index])
                bit_index += 1
        new_pixels.append(tuple(channels))

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = generate_timestamped_filename("stego_image", ".png")
    base_name = Path(filename).stem
    suffix = Path(filename).suffix
    output_path = output_dir / f"{base_name}{suffix}"
    counter = 1
    while output_path.exists():
        output_path = output_dir / f"{base_name}_{counter:02d}{suffix}"
        counter += 1

    rgb_image.putdata(new_pixels)
    rgb_image.save(output_path, "PNG")

    capacity_chars = max(0, capacity_bits // 8 - len(end_marker.encode("utf-8")))
    return {
        "output_path": output_path,
        "capacity_bits": capacity_bits,
        "capacity_chars": capacity_chars,
        "message_bits": len(message_bits),
        "message_chars": len(secret_text),
    }


def encode_payload_bytes(input_path, output_dir, payload_bytes, output_prefix="stego_image"):
    input_path = Path(input_path)
    if input_path.suffix.lower() != ".png":
        raise ValueError("Please provide a PNG image.")

    with Image.open(input_path) as image:
        rgb_image = image.convert("RGB")

    payload_length = len(payload_bytes)
    length_prefix = payload_length.to_bytes(LENGTH_PREFIX_SIZE, "big")
    message_bytes = length_prefix + payload_bytes
    message_bits = bytes_to_bits(message_bytes)
    capacity_bits = calculate_capacity(rgb_image)

    if len(message_bits) > capacity_bits:
        raise ValueError(
            "Message is too long for this image. Use a larger image or a smaller payload."
        )

    pixels = list(rgb_image.getdata())
    new_pixels = []
    bit_index = 0

    for pixel in pixels:
        channels = list(pixel)
        for i in range(3):
            if bit_index < len(message_bits):
                channels[i] = (channels[i] & ~1) | int(message_bits[bit_index])
                bit_index += 1
        new_pixels.append(tuple(channels))

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = generate_timestamped_filename(output_prefix, ".png")
    base_name = Path(filename).stem
    suffix = Path(filename).suffix
    output_path = output_dir / f"{base_name}{suffix}"
    counter = 1
    while output_path.exists():
        output_path = output_dir / f"{base_name}_{counter:02d}{suffix}"
        counter += 1

    rgb_image.putdata(new_pixels)
    rgb_image.save(output_path, "PNG")

    capacity_bytes = max(0, capacity_bits // 8 - LENGTH_PREFIX_SIZE)
    return {
        "output_path": output_path,
        "capacity_bits": capacity_bits,
        "capacity_bytes": capacity_bytes,
        "payload_bytes": payload_length,
        "message_bits": len(message_bits),
    }


def build_encrypted_text_payload(secret_text, password):
    if not secret_text:
        raise ValueError("Message cannot be empty.")

    encrypted_bytes = encrypt_bytes(secret_text.encode("utf-8"), password)
    metadata = {"encoding": "utf-8", "text_length": len(secret_text)}
    payload_bytes = build_payload(PAYLOAD_TYPE_TEXT, encrypted_bytes, metadata)
    return payload_bytes, metadata


def hide_encrypted_text(input_path, output_dir, secret_text, password):
    payload_bytes, metadata = build_encrypted_text_payload(secret_text, password)
    result = encode_payload_bytes(
        input_path, output_dir, payload_bytes, output_prefix="stego_text"
    )
    result["metadata"] = metadata
    return result

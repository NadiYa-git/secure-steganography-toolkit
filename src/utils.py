from pathlib import Path
from datetime import datetime
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

END_MARKER = "<END_OF_SECRET_MESSAGE>"
PAYLOAD_MAGIC = b"STEG"
PAYLOAD_VERSION = 1
PAYLOAD_TYPE_TEXT = 1
PAYLOAD_TYPE_FILE = 2
PAYLOAD_HEADER_SIZE = 14
LENGTH_PREFIX_SIZE = 4
BLOCKED_EXECUTABLE_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".msi", ".scr"}


def text_to_binary(text):
    data = text.encode("utf-8")
    return "".join(f"{byte:08b}" for byte in data)


def binary_to_text(bits):
    if len(bits) % 8 != 0:
        raise ValueError("Binary data length must be a multiple of 8.")

    bytes_list = [int(bits[i : i + 8], 2) for i in range(0, len(bits), 8)]
    return bytes(bytes_list).decode("utf-8", errors="replace")


def bytes_to_bits(data):
    return "".join(f"{byte:08b}" for byte in data)


def format_bytes(size_bytes):
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.2f} {units[unit_index]}"


def build_payload(payload_type, encrypted_bytes, metadata=None):
    if metadata is None:
        metadata = {}
    if not isinstance(encrypted_bytes, (bytes, bytearray)):
        raise ValueError("Encrypted data must be bytes.")

    metadata_json = json.dumps(
        metadata, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    header = (
        PAYLOAD_MAGIC
        + bytes([PAYLOAD_VERSION, payload_type])
        + len(metadata_json).to_bytes(4, "big")
        + len(encrypted_bytes).to_bytes(4, "big")
    )
    return header + metadata_json + bytes(encrypted_bytes)


def parse_payload(payload_bytes):
    if len(payload_bytes) < PAYLOAD_HEADER_SIZE:
        raise ValueError("Hidden data is corrupted or incomplete.")

    if payload_bytes[:4] != PAYLOAD_MAGIC:
        raise ValueError("No encrypted payload found in this image.")

    version = payload_bytes[4]
    if version != PAYLOAD_VERSION:
        raise ValueError("Unsupported payload version.")

    payload_type = payload_bytes[5]
    metadata_length = int.from_bytes(payload_bytes[6:10], "big")
    encrypted_length = int.from_bytes(payload_bytes[10:14], "big")
    expected_length = PAYLOAD_HEADER_SIZE + metadata_length + encrypted_length

    if expected_length != len(payload_bytes):
        raise ValueError("Hidden data is corrupted or incomplete.")

    metadata_end = PAYLOAD_HEADER_SIZE + metadata_length
    metadata_bytes = payload_bytes[PAYLOAD_HEADER_SIZE:metadata_end]
    metadata = {}
    if metadata_bytes:
        try:
            metadata = json.loads(metadata_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Hidden data is corrupted or incomplete.") from exc

    encrypted_bytes = payload_bytes[metadata_end:expected_length]
    return payload_type, metadata, encrypted_bytes


def calculate_capacity(image):
    width, height = image.size
    return width * height * 3


def create_required_folders(paths):
    for folder in paths:
        folder.mkdir(parents=True, exist_ok=True)


def normalize_path_input(raw_text):
    cleaned = raw_text.strip().strip('"').strip("'")
    return Path(cleaned).expanduser()


def is_png_file(path):
    return path.suffix.lower() == ".png"


def file_exists(path):
    return path.exists()


def generate_timestamped_filename(prefix, extension, timestamp=None):
    if not extension.startswith("."):
        extension = f".{extension}"
    if timestamp is None:
        timestamp = datetime.now()
    stamp = timestamp.strftime("%Y_%m_%d_%H%M%S")
    return f"{prefix}_{stamp}{extension}"


def save_extracted_message(message, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = generate_timestamped_filename("extracted_message", ".txt")
    output_path = output_dir / filename
    output_path.write_text(message, encoding="utf-8")
    return output_path


def open_file_with_default_app(file_path):
    path = Path(file_path)
    if not path.exists():
        raise ValueError("The file does not exist.")
    if path.is_dir():
        raise ValueError("Please select a file, not a folder.")
    if path.suffix.lower() in BLOCKED_EXECUTABLE_EXTENSIONS:
        raise ValueError("Opening executable files is blocked for safety.")

    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as exc:
        raise ValueError("Unable to open the file with the default application.") from exc


def open_folder(folder_path):
    path = Path(folder_path)
    if not path.exists():
        raise ValueError("The folder does not exist.")
    if not path.is_dir():
        raise ValueError("Please select a valid folder path.")

    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as exc:
        raise ValueError("Unable to open the folder.") from exc


def create_sample_image(image_path):
    image_path.parent.mkdir(parents=True, exist_ok=True)

    size = (200, 200)
    image = Image.new("RGB", size, color=(240, 240, 240))
    draw = ImageDraw.Draw(image)

    # Draw simple nested squares so the image is not empty.
    step = 20
    for i in range(0, size[0] // 2, step):
        color = (40 + i, 120, max(0, 200 - i))
        draw.rectangle([i, i, size[0] - 1 - i, size[1] - 1 - i], outline=color)

    image.save(image_path, "PNG")


def create_sample_image_if_missing(image_path):
    if not image_path.exists():
        create_sample_image(image_path)

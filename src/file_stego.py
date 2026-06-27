from crypto import decrypt_bytes, encrypt_bytes
from decoder import decode_payload_bytes
from encoder import encode_payload_bytes
from utils import (
    PAYLOAD_TYPE_FILE,
    build_payload,
    format_bytes,
    generate_timestamped_filename,
    parse_payload,
)

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".json", ".zip", ".csv"}


def build_encrypted_file_payload(file_path, password):
    if not file_path.exists():
        raise ValueError("The secret file does not exist.")

    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Allowed: {allowed_list}.")

    file_bytes = file_path.read_bytes()
    encrypted_bytes = encrypt_bytes(file_bytes, password)
    metadata = {
        "original_name": file_path.name,
        "extension": file_path.suffix.lower(),
        "size": len(file_bytes),
    }
    payload_bytes = build_payload(PAYLOAD_TYPE_FILE, encrypted_bytes, metadata)
    return payload_bytes, metadata


def hide_encrypted_file(image_path, output_dir, file_path, password):
    payload_bytes, metadata = build_encrypted_file_payload(file_path, password)
    result = encode_payload_bytes(
        image_path, output_dir, payload_bytes, output_prefix="stego_file"
    )
    result["metadata"] = metadata
    return result


def extract_encrypted_file(image_path, password, output_dir):
    payload_bytes = decode_payload_bytes(image_path)
    payload_type, metadata, encrypted_bytes = parse_payload(payload_bytes)

    if payload_type != PAYLOAD_TYPE_FILE:
        raise ValueError("Hidden data is not an encrypted file payload.")

    decrypted_bytes = decrypt_bytes(encrypted_bytes, password)
    expected_size = metadata.get("size")
    if isinstance(expected_size, int) and expected_size != len(decrypted_bytes):
        raise ValueError("Extracted file size does not match expected metadata.")

    extension = metadata.get("extension", ".bin")
    if not extension.startswith("."):
        extension = f".{extension}"

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = generate_timestamped_filename("extracted_file", extension)
    output_path = output_dir / filename
    output_path.write_bytes(decrypted_bytes)

    return {
        "output_path": output_path,
        "original_name": metadata.get("original_name", "unknown"),
        "file_size": len(decrypted_bytes),
        "file_size_display": format_bytes(len(decrypted_bytes)),
    }

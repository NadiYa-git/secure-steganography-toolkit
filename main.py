from pathlib import Path
import sys
from getpass import getpass

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

# Allow imports from the src folder without installing a package.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from analyzer import analyze_image, format_analysis_report
from comparator import compare_images, format_comparison_report
from decoder import extract_encrypted_text
from encoder import build_encrypted_text_payload, encode_payload_bytes
from file_stego import build_encrypted_file_payload, extract_encrypted_file
from utils import (
    LENGTH_PREFIX_SIZE,
    calculate_capacity,
    create_required_folders,
    create_sample_image_if_missing,
    file_exists,
    format_bytes,
    is_png_file,
    normalize_path_input,
    save_extracted_message,
)


def prompt_for_path(prompt_text, default_path=None):
    user_input = input(prompt_text).strip()
    if user_input:
        return normalize_path_input(user_input)
    return default_path


def prompt_for_password():
    password = getpass("Enter password: ").strip()
    if not password:
        print("Error: Password cannot be empty.")
        return None
    return password


def format_display_path(path):
    if path is None:
        return ""
    try:
        return path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return str(path)


def get_latest_stego_path(output_dir):
    candidates = sorted(
        output_dir.glob("stego_*.png"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    return output_dir / "stego_image.png"


def hide_encrypted_text_flow(default_image_path, output_dir):
    print("\n-- Hide Encrypted Text Message --")
    image_path = prompt_for_path(
        f"Enter image path (PNG). Press Enter for default [{default_image_path}]: ",
        default_image_path,
    )

    if not file_exists(image_path):
        print("Error: The image file does not exist.")
        return

    if not is_png_file(image_path):
        print("Error: Please provide a PNG image.")
        return

    secret_text = input("Enter your secret message: ").strip()
    if not secret_text:
        print("Error: Message cannot be empty.")
        return

    password = prompt_for_password()
    if not password:
        return

    try:
        with Image.open(image_path) as image:
            rgb_image = image.convert("RGB")
    except Exception:
        print("Error: Could not open the image. Please use a valid PNG file.")
        return

    width, height = rgb_image.size
    capacity_bits = calculate_capacity(rgb_image)
    capacity_bytes = max(0, capacity_bits // 8 - LENGTH_PREFIX_SIZE)

    try:
        payload_bytes, _ = build_encrypted_text_payload(secret_text, password)
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    payload_size = len(payload_bytes)
    print("Image loaded successfully.")
    print(f"Image size: {width} x {height}")
    print(f"Maximum capacity: {format_bytes(capacity_bytes)}")
    print(f"Plain message length: {len(secret_text)} characters")
    print(f"Encrypted payload size: {format_bytes(payload_size)}")

    if payload_size > capacity_bytes:
        print("Status: Too large to encode")
        print(
            "Error: Message is too long for this image. Please choose a larger image or a shorter message."
        )
        return

    try:
        result = encode_payload_bytes(
            image_path, output_dir, payload_bytes, output_prefix="stego_text"
        )
        output_path = result["output_path"]
        print("Status: Safe to encode")
        print(
            "Success! Encoded image saved to: "
            f"{format_display_path(output_path)}"
        )
    except ValueError as exc:
        print(f"Error: {exc}")
    except Exception:
        print("Error: Something went wrong while encoding the image.")


def extract_encrypted_text_flow(default_stego_path, extracted_dir):
    print("\n-- Extract Encrypted Text Message --")
    image_path = prompt_for_path(
        f"Enter stego image path (PNG). Press Enter for default [{default_stego_path}]: ",
        default_stego_path,
    )

    if not file_exists(image_path):
        print("Error: The image file does not exist.")
        return

    if not is_png_file(image_path):
        print("Error: Please provide a PNG image.")
        return

    password = prompt_for_password()
    if not password:
        return

    try:
        message = extract_encrypted_text(image_path, password)
        output_path = save_extracted_message(message, extracted_dir)
        print("Hidden message extracted successfully.")
        print("Message:")
        print(message)
        print(
            "Saved extracted message to: "
            f"{format_display_path(output_path)}"
        )
    except ValueError as exc:
        print(f"Error: {exc}")
    except Exception:
        print("Error: Something went wrong while decoding the image.")


def hide_encrypted_file_flow(default_image_path, output_dir):
    print("\n-- Hide Encrypted File --")
    image_path = prompt_for_path(
        f"Enter image path (PNG). Press Enter for default [{default_image_path}]: ",
        default_image_path,
    )

    if not file_exists(image_path):
        print("Error: The image file does not exist.")
        return

    if not is_png_file(image_path):
        print("Error: Please provide a PNG image.")
        return

    raw_file_path = input("Enter secret file path: ").strip()
    if not raw_file_path:
        print("Error: File path cannot be empty.")
        return

    file_path = normalize_path_input(raw_file_path)
    if not file_exists(file_path):
        print("Error: The secret file does not exist.")
        return

    password = prompt_for_password()
    if not password:
        return

    try:
        with Image.open(image_path) as image:
            rgb_image = image.convert("RGB")
    except Exception:
        print("Error: Could not open the image. Please use a valid PNG file.")
        return

    width, height = rgb_image.size
    capacity_bits = calculate_capacity(rgb_image)
    capacity_bytes = max(0, capacity_bits // 8 - LENGTH_PREFIX_SIZE)

    try:
        file_size_on_disk = file_path.stat().st_size
    except Exception:
        print("Error: Unable to read the secret file size.")
        return

    print("Image loaded successfully.")
    print(f"Image size: {width} x {height}")
    print(f"Maximum capacity: {format_bytes(capacity_bytes)}")
    print(f"Secret file size: {format_bytes(file_size_on_disk)}")

    if file_size_on_disk > capacity_bytes:
        print("Status: Too large to encode")
        print(
            "Error: File is too large for this image. Please choose a larger image or a smaller file."
        )
        return

    try:
        payload_bytes, _ = build_encrypted_file_payload(file_path, password)
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    payload_size = len(payload_bytes)
    print(f"Encrypted payload size: {format_bytes(payload_size)}")

    if payload_size > capacity_bytes:
        print("Status: Too large to encode")
        print(
            "Error: File is too large for this image. Please choose a larger image or a smaller file."
        )
        return

    try:
        result = encode_payload_bytes(
            image_path, output_dir, payload_bytes, output_prefix="stego_file"
        )
        output_path = result["output_path"]
        print("Status: Safe to encode")
        print(
            "Success! Encoded image saved to: "
            f"{format_display_path(output_path)}"
        )
    except ValueError as exc:
        print(f"Error: {exc}")
    except Exception:
        print("Error: Something went wrong while encoding the image.")


def extract_encrypted_file_flow(default_stego_path, extracted_dir):
    print("\n-- Extract Encrypted File --")
    image_path = prompt_for_path(
        f"Enter stego image path (PNG). Press Enter for default [{default_stego_path}]: ",
        default_stego_path,
    )

    if not file_exists(image_path):
        print("Error: The image file does not exist.")
        return

    if not is_png_file(image_path):
        print("Error: Please provide a PNG image.")
        return

    password = prompt_for_password()
    if not password:
        return

    try:
        result = extract_encrypted_file(image_path, password, extracted_dir)
        output_path = result["output_path"]
        print("Hidden file extracted successfully.")
        print(f"Original name: {result['original_name']}")
        print(f"File size: {result['file_size_display']}")
        print(
            "Saved extracted file to: "
            f"{format_display_path(output_path)}"
        )
    except ValueError as exc:
        print(f"Error: {exc}")
    except Exception:
        print("Error: Something went wrong while extracting the file.")


def analyze_image_flow():
    print("\n-- Analyze Image --")
    raw_path = input("Enter image path: ").strip()
    if not raw_path:
        print("Error: Image path cannot be empty.")
        return

    image_path = normalize_path_input(raw_path)
    try:
        report = analyze_image(image_path)
        print(format_analysis_report(report))
    except ValueError as exc:
        print(f"Error: {exc}")
    except Exception:
        print("Error: Something went wrong while analyzing the image.")


def compare_images_flow(output_dir):
    print("\n-- Compare Images --")
    original_raw = input("Enter original image path: ").strip()
    stego_raw = input("Enter stego image path: ").strip()

    if not original_raw or not stego_raw:
        print("Error: Both image paths are required.")
        return

    original_path = normalize_path_input(original_raw)
    stego_path = normalize_path_input(stego_raw)

    save_diff = input("Save a difference image? (y/n): ").strip().lower() == "y"

    try:
        report = compare_images(
            original_path, stego_path, output_dir=output_dir, save_diff=save_diff
        )
        print(format_comparison_report(report))
    except ValueError as exc:
        print(f"Error: {exc}")
    except Exception:
        print("Error: Something went wrong while comparing the images.")


def launch_gui_flow():
    try:
        from gui.app import launch_gui

        launch_gui()
    except Exception:
        print("Error: Unable to launch the GUI.")


def main():
    test_images_dir = BASE_DIR / "test_images"
    output_dir = BASE_DIR / "output"
    extracted_dir = BASE_DIR / "extracted"
    create_required_folders([test_images_dir, output_dir, extracted_dir])

    default_image_path = test_images_dir / "original.png"
    create_sample_image_if_missing(default_image_path)

    while True:
        print("\n===== Secure Steganography Toolkit =====")
        print("1. Hide encrypted text message in image")
        print("2. Extract encrypted text message from image")
        print("3. Hide encrypted file in image")
        print("4. Extract encrypted file from image")
        print("5. Analyze image")
        print("6. Compare original and stego image")
        print("7. Launch GUI")
        print("8. Exit")

        choice = input("Select an option (1-8): ").strip()

        if choice == "1":
            hide_encrypted_text_flow(default_image_path, output_dir)
        elif choice == "2":
            default_stego_path = get_latest_stego_path(output_dir)
            extract_encrypted_text_flow(default_stego_path, extracted_dir)
        elif choice == "3":
            hide_encrypted_file_flow(default_image_path, output_dir)
        elif choice == "4":
            default_stego_path = get_latest_stego_path(output_dir)
            extract_encrypted_file_flow(default_stego_path, extracted_dir)
        elif choice == "5":
            analyze_image_flow()
        elif choice == "6":
            compare_images_flow(output_dir)
        elif choice == "7":
            launch_gui_flow()
        elif choice == "8":
            print("Goodbye!")
            break
        else:
            print("Please choose a number between 1 and 8.")


if __name__ == "__main__":
    main()

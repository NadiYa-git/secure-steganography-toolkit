from PIL import Image

from decoder import decode_message
from utils import END_MARKER, format_bytes


def analyze_image(image_path, check_end_marker=True):
    if not image_path.exists():
        raise ValueError("The image file does not exist.")

    try:
        with Image.open(image_path) as image:
            image_format = image.format
            image_mode = image.mode
            width, height = image.size
            rgb_required = image_mode != "RGB"
    except Exception as exc:
        raise ValueError("Could not open the image. Please use a valid image file.") from exc

    file_size = image_path.stat().st_size
    total_pixels = width * height
    capacity_bits = width * height * 3
    capacity_chars = max(0, capacity_bits // 8)

    is_png = (image_format or "").upper() == "PNG"
    status = "Suitable for LSB steganography"
    warning = None
    if not is_png:
        status = "Not recommended for LSB steganography"
        warning = "Warning: File is not PNG. Convert to PNG for best results."

    marker_status = None
    if check_end_marker:
        try:
            _ = decode_message(image_path, END_MARKER)
            marker_status = "Possible end marker detected"
        except ValueError:
            marker_status = "End marker not detected"
        except Exception:
            marker_status = "End marker check failed"

    return {
        "path": image_path,
        "format": image_format or "Unknown",
        "mode": image_mode,
        "width": width,
        "height": height,
        "total_pixels": total_pixels,
        "file_size": file_size,
        "file_size_display": format_bytes(file_size),
        "capacity_chars": capacity_chars,
        "status": status,
        "warning": warning,
        "rgb_required": rgb_required,
        "marker_status": marker_status,
    }


def format_analysis_report(report):
    lines = [
        "Image Analysis Report",
        f"File: {report['path'].as_posix()}",
        f"Format: {report['format']}",
        f"Mode: {report['mode']}",
        f"Size: {report['width']} x {report['height']}",
        f"Total pixels: {report['total_pixels']}",
        f"File size: {report['file_size_display']}",
        f"Estimated text capacity: {report['capacity_chars']} characters",
        f"Status: {report['status']}",
    ]

    if report.get("rgb_required"):
        lines.append("Note: Image will be converted to RGB for encoding.")

    if report.get("warning"):
        lines.append(report["warning"])

    if report.get("marker_status"):
        lines.append(f"Marker check: {report['marker_status']}")

    return "\n".join(lines)

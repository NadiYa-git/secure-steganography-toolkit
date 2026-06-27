from PIL import Image, ImageChops

from utils import format_bytes, generate_timestamped_filename


def _classify_visual_impact(percent_changed):
    if percent_changed < 0.1:
        return "Very low"
    if percent_changed < 1.0:
        return "Low"
    if percent_changed < 5.0:
        return "Medium"
    return "High"


def compare_images(original_path, stego_path, output_dir=None, save_diff=False):
    if not original_path.exists():
        raise ValueError("Original image file does not exist.")
    if not stego_path.exists():
        raise ValueError("Stego image file does not exist.")

    try:
        with Image.open(original_path) as original_img, Image.open(stego_path) as stego_img:
            original_rgb = original_img.convert("RGB")
            stego_rgb = stego_img.convert("RGB")
    except Exception as exc:
        raise ValueError("One or both images could not be opened.") from exc

    if original_rgb.size != stego_rgb.size:
        raise ValueError("Images must have the same dimensions to compare.")

    width, height = original_rgb.size
    total_pixels = width * height

    diff_image = ImageChops.difference(original_rgb, stego_rgb)
    diff_gray = diff_image.convert("L")
    diff_data = diff_gray.getdata()
    changed_pixels = sum(1 for value in diff_data if value != 0)
    percent_changed = (changed_pixels / total_pixels * 100) if total_pixels else 0.0
    impact = _classify_visual_impact(percent_changed)

    original_size = original_path.stat().st_size
    stego_size = stego_path.stat().st_size
    size_diff = stego_size - original_size

    diff_path = None
    if save_diff and output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = generate_timestamped_filename("diff_image", ".png")
        diff_path = output_dir / filename
        diff_image.save(diff_path, "PNG")

    return {
        "original_path": original_path,
        "stego_path": stego_path,
        "original_size": original_size,
        "stego_size": stego_size,
        "size_diff": size_diff,
        "size_diff_display": format_bytes(abs(size_diff)),
        "changed_pixels": changed_pixels,
        "percent_changed": percent_changed,
        "impact": impact,
        "diff_path": diff_path,
    }


def format_comparison_report(report):
    lines = [
        "Image Comparison Report",
        f"Original size: {format_bytes(report['original_size'])}",
        f"Stego size: {format_bytes(report['stego_size'])}",
        f"File size difference: {report['size_diff_display']}",
        f"Changed pixels: {report['changed_pixels']}",
        f"Changed pixel percentage: {report['percent_changed']:.2f}%",
        f"Visual impact: {report['impact']}",
    ]

    if report.get("diff_path"):
        lines.append(f"Difference image saved to: {report['diff_path'].as_posix()}")

    return "\n".join(lines)

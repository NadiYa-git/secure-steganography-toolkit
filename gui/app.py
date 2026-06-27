from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from analyzer import analyze_image, format_analysis_report
from comparator import compare_images, format_comparison_report
from decoder import extract_encrypted_text
from encoder import hide_encrypted_text
from file_stego import extract_encrypted_file, hide_encrypted_file
from utils import (
    LENGTH_PREFIX_SIZE,
    calculate_capacity,
    create_required_folders,
    format_bytes,
    is_png_file,
    normalize_path_input,
    open_file_with_default_app,
    open_folder,
    save_extracted_message,
)

BG_COLOR = "#f4f7fb"
CARD_BG = "#ffffff"
PRIMARY_COLOR = "#1f6feb"
PRIMARY_HOVER = "#1959c1"
SECONDARY_COLOR = "#e2e8f0"
SECONDARY_HOVER = "#cbd5e1"
DANGER_COLOR = "#f07474"
DANGER_HOVER = "#e96464"
TEXT_COLOR = "#0f172a"
MUTED_TEXT = "#475569"
BORDER_COLOR = "#d0d7e2"
STATUS_BG = "#0b2545"
STATUS_FG = "#ffffff"

FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_SUBTITLE = ("Segoe UI", 11)
FONT_LABEL = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 10, "bold")
FONT_TEXT = ("Segoe UI", 10)

PAGE_PAD = (16, 14)
SECTION_GAP = 12
FIELD_PAD_X = 10
FIELD_PAD_Y = 6
BUTTON_PAD_X = 6
BUTTON_PAD_Y = 6


def _apply_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("App.TFrame", background=BG_COLOR)
    style.configure("Card.TFrame", background=CARD_BG)
    style.configure(
        "Card.TLabelframe",
        background=CARD_BG,
        foreground=TEXT_COLOR,
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=CARD_BG,
        foreground=TEXT_COLOR,
        font=FONT_LABEL,
    )
    style.configure("Title.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=FONT_TITLE)
    style.configure(
        "Subtitle.TLabel", background=BG_COLOR, foreground=MUTED_TEXT, font=FONT_SUBTITLE
    )
    style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_COLOR, font=FONT_LABEL)
    style.configure("Hint.TLabel", background=CARD_BG, foreground=MUTED_TEXT, font=FONT_LABEL)

    style.configure(
        "TEntry",
        fieldbackground="white",
        foreground=TEXT_COLOR,
        font=FONT_LABEL,
        padding=(6, 4),
    )
    style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        padding=(12, 8),
        font=FONT_LABEL,
        background=SECONDARY_COLOR,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", CARD_BG)],
        foreground=[("selected", TEXT_COLOR)],
    )

    style.configure(
        "Primary.TButton",
        background=PRIMARY_COLOR,
        foreground="white",
        font=FONT_BUTTON,
        padding=(14, 8),
    )
    style.map(
        "Primary.TButton",
        background=[("active", PRIMARY_HOVER), ("pressed", PRIMARY_HOVER)],
    )
    style.configure(
        "Secondary.TButton",
        background=SECONDARY_COLOR,
        foreground=TEXT_COLOR,
        font=FONT_LABEL,
        padding=(12, 8),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", SECONDARY_HOVER), ("pressed", SECONDARY_HOVER)],
    )
    style.configure(
        "Danger.TButton",
        background=DANGER_COLOR,
        foreground="white",
        font=FONT_LABEL,
        padding=(12, 8),
    )
    style.map(
        "Danger.TButton",
        background=[("active", DANGER_HOVER), ("pressed", DANGER_HOVER)],
    )

    style.configure(
        "Status.TLabel",
        background=STATUS_BG,
        foreground=STATUS_FG,
        font=FONT_LABEL,
        padding=(10, 6),
    )


def _create_section(parent, title):
    frame = ttk.LabelFrame(
        parent,
        text=title,
        style="Card.TLabelframe",
        padding=(12, 10),
    )
    frame.columnconfigure(1, weight=1)
    return frame


def _card_label(parent, text):
    return ttk.Label(parent, text=text, style="Card.TLabel")


def _primary_button(parent, text, command):
    return ttk.Button(parent, text=text, command=command, style="Primary.TButton")


def _secondary_button(parent, text, command, state="normal"):
    return ttk.Button(
        parent,
        text=text,
        command=command,
        style="Secondary.TButton",
        state=state,
    )


def _style_text_widget(widget):
    widget.configure(
        background=CARD_BG,
        foreground=TEXT_COLOR,
        insertbackground=TEXT_COLOR,
        font=FONT_TEXT,
        relief="solid",
        borderwidth=1,
        highlightthickness=1,
        highlightbackground=BORDER_COLOR,
        highlightcolor=PRIMARY_COLOR,
    )


def _select_file_path(entry, filetypes):
    path = filedialog.askopenfilename(filetypes=filetypes)
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


def _get_path(entry):
    raw = entry.get().strip()
    if not raw:
        return None
    return normalize_path_input(raw)


def _set_status(status_var, message):
    status_var.set(message)


def _validate_png_path(path, label_text):
    if path is None:
        messagebox.showwarning("Missing Image", f"Please select a {label_text} PNG image.")
        return False
    if not path.exists():
        messagebox.showerror("Missing Image", "The image file does not exist.")
        return False
    if not is_png_file(path):
        messagebox.showwarning("Invalid Image", "Please provide a PNG image.")
        return False
    return True


def _validate_file_path(path, label_text):
    if path is None:
        messagebox.showwarning("Missing File", f"Please select a {label_text} file.")
        return False
    if not path.exists():
        messagebox.showerror("Missing File", "The selected file does not exist.")
        return False
    return True


def _validate_password(password):
    if not password:
        messagebox.showwarning("Missing Password", "Password cannot be empty.")
        return False
    return True


def _calculate_capacity_bytes(image_path):
    with Image.open(image_path) as image:
        rgb_image = image.convert("RGB")
    capacity_bits = calculate_capacity(rgb_image)
    return max(0, capacity_bits // 8 - LENGTH_PREFIX_SIZE)


def _update_capacity_label(image_path, capacity_var, status_var):
    if not _validate_png_path(image_path, "cover"):
        return None
    try:
        capacity_bytes = _calculate_capacity_bytes(image_path)
        capacity_var.set(f"Capacity: {format_bytes(capacity_bytes)}")
        _set_status(status_var, "Capacity updated")
        return capacity_bytes
    except Exception:
        messagebox.showerror("Error", "Unable to read image capacity.")
        _set_status(status_var, "Capacity check failed")
        return None


def _update_file_size_label(file_path, size_var, status_var):
    if not _validate_file_path(file_path, "secret"):
        return None
    try:
        size = file_path.stat().st_size
        size_var.set(f"File size: {format_bytes(size)}")
        _set_status(status_var, "File size updated")
        return size
    except Exception:
        messagebox.showerror("Error", "Unable to read file size.")
        _set_status(status_var, "File size check failed")
        return None


def _clear_entry(entry):
    entry.delete(0, tk.END)


def _clear_text(text_widget):
    text_widget.delete("1.0", tk.END)




def _build_hide_text_tab(notebook, output_dir, status_var):
    frame = ttk.Frame(notebook, padding=PAGE_PAD, style="App.TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    input_section = _create_section(frame, "Input")
    input_section.grid(row=0, column=0, sticky="ew", pady=(0, SECTION_GAP))
    input_section.columnconfigure(1, weight=1)
    input_section.rowconfigure(1, weight=1)

    cover_label = _card_label(input_section, "Cover image (PNG):")
    cover_label.grid(row=0, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    cover_entry = ttk.Entry(input_section)
    cover_entry.grid(row=0, column=1, sticky="ew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    cover_button = _secondary_button(
        input_section,
        "Browse",
        command=lambda: _select_file_path(cover_entry, [("PNG Images", "*.png")]),
    )
    cover_button.grid(row=0, column=2, padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    message_label = _card_label(input_section, "Secret message:")
    message_label.grid(row=1, column=0, sticky="nw", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    message_text = scrolledtext.ScrolledText(input_section, height=7, wrap="word")
    message_text.grid(
        row=1, column=1, columnspan=2, sticky="nsew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y
    )
    _style_text_widget(message_text)

    password_label = _card_label(input_section, "Password:")
    password_label.grid(row=2, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    password_entry = ttk.Entry(input_section, show="*")
    password_entry.grid(row=2, column=1, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    capacity_var = tk.StringVar(value="Capacity: --")
    capacity_label = ttk.Label(input_section, textvariable=capacity_var, style="Hint.TLabel")
    capacity_label.grid(row=3, column=1, sticky="w", padx=FIELD_PAD_X, pady=(0, FIELD_PAD_Y))
    capacity_button = _secondary_button(
        input_section,
        "Check Capacity",
        command=lambda: _update_capacity_label(
            _get_path(cover_entry), capacity_var, status_var
        ),
    )
    capacity_button.grid(row=3, column=2, padx=FIELD_PAD_X, pady=(0, FIELD_PAD_Y))

    result_section = _create_section(frame, "Result")
    result_section.grid(row=1, column=0, sticky="nsew", pady=(0, SECTION_GAP))
    result_section.columnconfigure(1, weight=1)
    result_section.rowconfigure(0, weight=1)

    result_label = _card_label(result_section, "Result output:")
    result_label.grid(row=0, column=0, sticky="nw", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    result_output = scrolledtext.ScrolledText(result_section, height=6, wrap="word")
    result_output.grid(
        row=0, column=1, columnspan=2, sticky="nsew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y
    )
    _style_text_widget(result_output)

    output_var = tk.StringVar(value="Saved stego image: --")
    output_label = ttk.Label(result_section, textvariable=output_var, style="Hint.TLabel")
    output_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=FIELD_PAD_X, pady=(0, FIELD_PAD_Y))

    def handle_hide_text():
        image_path = _get_path(cover_entry)
        secret_text = message_text.get("1.0", tk.END).strip()
        password = password_entry.get().strip()

        if not _validate_png_path(image_path, "cover"):
            return
        if not secret_text:
            messagebox.showwarning("Missing Message", "Please enter a secret message.")
            return
        if not _validate_password(password):
            return

        capacity_bytes = _update_capacity_label(image_path, capacity_var, status_var)
        if capacity_bytes is None:
            return

        try:
            result = hide_encrypted_text(image_path, output_dir, secret_text, password)
            output_path = result["output_path"]
            _clear_text(result_output)
            result_output.insert(
                tk.END,
                "Encrypted message hidden successfully.\n"
                f"Output: {output_path.as_posix()}",
            )
            output_var.set(f"Saved stego image: {output_path.as_posix()}")
            _set_status(status_var, "Encoding completed")
            messagebox.showinfo("Success", "Encrypted message hidden successfully.")
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            _set_status(status_var, "Encoding failed")
        except Exception:
            messagebox.showerror("Error", "Something went wrong while hiding the message.")
            _set_status(status_var, "Encoding failed")

    def handle_clear():
        _clear_entry(cover_entry)
        _clear_text(message_text)
        _clear_entry(password_entry)
        _clear_text(result_output)
        capacity_var.set("Capacity: --")
        output_var.set("Saved stego image: --")
        _set_status(status_var, "Ready")

    action_frame = ttk.Frame(frame, style="App.TFrame")
    action_frame.grid(row=2, column=0, sticky="w")
    _primary_button(action_frame, "Hide Message", handle_hide_text).grid(
        row=0, column=0, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )
    _secondary_button(action_frame, "Clear", handle_clear).grid(
        row=0, column=1, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )

    return frame


def _build_extract_text_tab(notebook, extracted_dir, status_var):
    frame = ttk.Frame(notebook, padding=PAGE_PAD, style="App.TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    input_section = _create_section(frame, "Input")
    input_section.grid(row=0, column=0, sticky="ew", pady=(0, SECTION_GAP))
    input_section.columnconfigure(1, weight=1)

    stego_label = _card_label(input_section, "Stego image (PNG):")
    stego_label.grid(row=0, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    stego_entry = ttk.Entry(input_section)
    stego_entry.grid(row=0, column=1, sticky="ew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    stego_button = _secondary_button(
        input_section,
        "Browse",
        command=lambda: _select_file_path(stego_entry, [("PNG Images", "*.png")]),
    )
    stego_button.grid(row=0, column=2, padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    password_label = _card_label(input_section, "Password:")
    password_label.grid(row=1, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    password_entry = ttk.Entry(input_section, show="*")
    password_entry.grid(row=1, column=1, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    result_section = _create_section(frame, "Result")
    result_section.grid(row=1, column=0, sticky="nsew", pady=(0, SECTION_GAP))
    result_section.columnconfigure(1, weight=1)
    result_section.rowconfigure(0, weight=1)

    output_label = _card_label(result_section, "Extracted message:")
    output_label.grid(row=0, column=0, sticky="nw", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    output_box = scrolledtext.ScrolledText(result_section, height=7, wrap="word")
    output_box.grid(
        row=0, column=1, columnspan=2, sticky="nsew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y
    )
    _style_text_widget(output_box)

    saved_var = tk.StringVar(value="Saved text file: --")
    saved_label = ttk.Label(result_section, textvariable=saved_var, style="Hint.TLabel")
    saved_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=FIELD_PAD_X, pady=(0, FIELD_PAD_Y))

    def handle_extract_text():
        image_path = _get_path(stego_entry)
        password = password_entry.get().strip()

        if not _validate_png_path(image_path, "stego"):
            return
        if not _validate_password(password):
            return

        try:
            message = extract_encrypted_text(image_path, password)
            output_path = save_extracted_message(message, extracted_dir)
            _clear_text(output_box)
            output_box.insert(tk.END, message)
            saved_var.set(f"Saved text file: {output_path.as_posix()}")
            _set_status(status_var, "Extraction completed")
            messagebox.showinfo("Success", "Message extracted successfully.")
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            _set_status(status_var, "Extraction failed")
        except Exception:
            messagebox.showerror("Error", "Something went wrong while extracting the message.")
            _set_status(status_var, "Extraction failed")

    def handle_clear():
        _clear_entry(stego_entry)
        _clear_entry(password_entry)
        _clear_text(output_box)
        saved_var.set("Saved text file: --")
        _set_status(status_var, "Ready")

    action_frame = ttk.Frame(frame, style="App.TFrame")
    action_frame.grid(row=2, column=0, sticky="w")
    _primary_button(action_frame, "Extract Message", handle_extract_text).grid(
        row=0, column=0, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )
    _secondary_button(action_frame, "Clear", handle_clear).grid(
        row=0, column=1, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )

    return frame


def _build_hide_file_tab(notebook, output_dir, status_var):
    frame = ttk.Frame(notebook, padding=PAGE_PAD, style="App.TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    input_section = _create_section(frame, "Input")
    input_section.grid(row=0, column=0, sticky="ew", pady=(0, SECTION_GAP))
    input_section.columnconfigure(1, weight=1)

    cover_label = _card_label(input_section, "Cover image (PNG):")
    cover_label.grid(row=0, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    cover_entry = ttk.Entry(input_section)
    cover_entry.grid(row=0, column=1, sticky="ew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    cover_button = _secondary_button(
        input_section,
        "Browse",
        command=lambda: _select_file_path(cover_entry, [("PNG Images", "*.png")]),
    )
    cover_button.grid(row=0, column=2, padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    file_label = _card_label(input_section, "Secret file:")
    file_label.grid(row=1, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    file_entry = ttk.Entry(input_section)
    file_entry.grid(row=1, column=1, sticky="ew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    file_button = _secondary_button(
        input_section,
        "Browse",
        command=lambda: _select_file_path(file_entry, [("All Files", "*.*")]),
    )
    file_button.grid(row=1, column=2, padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    password_label = _card_label(input_section, "Password:")
    password_label.grid(row=2, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    password_entry = ttk.Entry(input_section, show="*")
    password_entry.grid(row=2, column=1, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    capacity_var = tk.StringVar(value="Capacity: --")
    file_size_var = tk.StringVar(value="File size: --")
    ttk.Label(input_section, textvariable=capacity_var, style="Hint.TLabel").grid(
        row=3, column=1, sticky="w", padx=FIELD_PAD_X, pady=(0, FIELD_PAD_Y)
    )
    ttk.Label(input_section, textvariable=file_size_var, style="Hint.TLabel").grid(
        row=4, column=1, sticky="w", padx=FIELD_PAD_X, pady=(0, FIELD_PAD_Y)
    )
    info_button = _secondary_button(
        input_section,
        "Check Capacity",
        command=lambda: (
            _update_capacity_label(_get_path(cover_entry), capacity_var, status_var),
            _update_file_size_label(_get_path(file_entry), file_size_var, status_var),
        ),
    )
    info_button.grid(row=3, column=2, rowspan=2, padx=FIELD_PAD_X, pady=(0, FIELD_PAD_Y))

    result_section = _create_section(frame, "Result")
    result_section.grid(row=1, column=0, sticky="nsew", pady=(0, SECTION_GAP))
    result_section.columnconfigure(1, weight=1)
    result_section.rowconfigure(0, weight=1)

    result_label = _card_label(result_section, "Result output:")
    result_label.grid(row=0, column=0, sticky="nw", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    result_output = scrolledtext.ScrolledText(result_section, height=6, wrap="word")
    result_output.grid(
        row=0, column=1, columnspan=2, sticky="nsew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y
    )
    _style_text_widget(result_output)

    output_var = tk.StringVar(value="Saved stego image: --")
    output_label = ttk.Label(result_section, textvariable=output_var, style="Hint.TLabel")
    output_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=FIELD_PAD_X, pady=(0, FIELD_PAD_Y))

    def handle_hide_file():
        image_path = _get_path(cover_entry)
        secret_path = _get_path(file_entry)
        password = password_entry.get().strip()

        if not _validate_png_path(image_path, "cover"):
            return
        if not _validate_file_path(secret_path, "secret"):
            return
        if not _validate_password(password):
            return

        capacity_bytes = _update_capacity_label(image_path, capacity_var, status_var)
        file_size = _update_file_size_label(secret_path, file_size_var, status_var)
        if capacity_bytes is None or file_size is None:
            return
        if file_size > capacity_bytes:
            messagebox.showwarning(
                "File Too Large",
                "The file is too large for this image. Please choose a larger image or a smaller file.",
            )
            _set_status(status_var, "Encoding blocked: file too large")
            return

        try:
            result = hide_encrypted_file(image_path, output_dir, secret_path, password)
            output_path = result["output_path"]
            _clear_text(result_output)
            result_output.insert(
                tk.END,
                "Encrypted file hidden successfully.\n"
                f"Output: {output_path.as_posix()}",
            )
            output_var.set(f"Saved stego image: {output_path.as_posix()}")
            _set_status(status_var, "Encoding completed")
            messagebox.showinfo("Success", "Encrypted file hidden successfully.")
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            _set_status(status_var, "Encoding failed")
        except Exception:
            messagebox.showerror("Error", "Something went wrong while hiding the file.")
            _set_status(status_var, "Encoding failed")

    def handle_clear():
        _clear_entry(cover_entry)
        _clear_entry(file_entry)
        _clear_entry(password_entry)
        _clear_text(result_output)
        capacity_var.set("Capacity: --")
        file_size_var.set("File size: --")
        output_var.set("Saved stego image: --")
        _set_status(status_var, "Ready")

    action_frame = ttk.Frame(frame, style="App.TFrame")
    action_frame.grid(row=2, column=0, sticky="w")
    _primary_button(action_frame, "Hide File", handle_hide_file).grid(
        row=0, column=0, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )
    _secondary_button(action_frame, "Clear", handle_clear).grid(
        row=0, column=1, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )

    return frame


def _build_extract_file_tab(notebook, extracted_dir, status_var):
    frame = ttk.Frame(notebook, padding=PAGE_PAD, style="App.TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    input_section = _create_section(frame, "Input")
    input_section.grid(row=0, column=0, sticky="ew", pady=(0, SECTION_GAP))
    input_section.columnconfigure(1, weight=1)

    stego_label = _card_label(input_section, "Stego image (PNG):")
    stego_label.grid(row=0, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    stego_entry = ttk.Entry(input_section)
    stego_entry.grid(row=0, column=1, sticky="ew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    stego_button = _secondary_button(
        input_section,
        "Browse",
        command=lambda: _select_file_path(stego_entry, [("PNG Images", "*.png")]),
    )
    stego_button.grid(row=0, column=2, padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    password_label = _card_label(input_section, "Password:")
    password_label.grid(row=1, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    password_entry = ttk.Entry(input_section, show="*")
    password_entry.grid(row=1, column=1, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    result_section = _create_section(frame, "Result")
    result_section.grid(row=1, column=0, sticky="nsew", pady=(0, SECTION_GAP))
    result_section.columnconfigure(1, weight=1)
    result_section.rowconfigure(0, weight=1)

    result_label = _card_label(result_section, "Result output:")
    result_label.grid(row=0, column=0, sticky="nw", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    result_output = scrolledtext.ScrolledText(result_section, height=6, wrap="word")
    result_output.grid(
        row=0, column=1, columnspan=2, sticky="nsew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y
    )
    _style_text_widget(result_output)

    saved_var = tk.StringVar(value="Saved file: --")
    saved_label = ttk.Label(result_section, textvariable=saved_var, style="Hint.TLabel")
    saved_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=FIELD_PAD_X, pady=(0, FIELD_PAD_Y))

    last_extracted = {"path": None}

    def handle_extract_file():
        image_path = _get_path(stego_entry)
        password = password_entry.get().strip()

        if not _validate_png_path(image_path, "stego"):
            return
        if not _validate_password(password):
            return

        try:
            result = extract_encrypted_file(image_path, password, extracted_dir)
            output_path = result["output_path"]
            last_extracted["path"] = output_path
            _clear_text(result_output)
            result_output.insert(
                tk.END,
                "File extracted successfully.\n"
                "Saved to:\n"
                f"{output_path.as_posix()}",
            )
            saved_var.set(f"Saved file: {output_path.as_posix()}")
            open_file_button.config(state="normal")
            open_folder_button.config(state="normal")
            _set_status(status_var, "Extraction completed")
            messagebox.showinfo("Success", "Encrypted file extracted successfully.")
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            _set_status(status_var, "Extraction failed")
        except Exception:
            messagebox.showerror("Error", "Something went wrong while extracting the file.")
            _set_status(status_var, "Extraction failed")

    def handle_clear():
        last_extracted["path"] = None
        _clear_entry(stego_entry)
        _clear_entry(password_entry)
        _clear_text(result_output)
        saved_var.set("Saved file: --")
        open_file_button.config(state="disabled")
        open_folder_button.config(state="disabled")
        _set_status(status_var, "Ready")

    def handle_open_file():
        extracted_path = last_extracted["path"]
        if extracted_path is None:
            messagebox.showwarning(
                "No Extracted File", "No extracted file is available yet."
            )
            return

        try:
            open_file_with_default_app(extracted_path)
            _set_status(status_var, "Opened extracted file")
            messagebox.showinfo("Opened", "Extracted file opened successfully.")
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            _set_status(status_var, "Unable to open extracted file")

    def handle_open_folder():
        extracted_path = last_extracted["path"]
        if extracted_path is None:
            messagebox.showwarning(
                "No Extracted File", "No extracted file is available yet."
            )
            return

        try:
            open_folder(extracted_dir)
            _set_status(status_var, "Opened extracted folder")
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            _set_status(status_var, "Unable to open extracted folder")

    action_frame = ttk.Frame(frame, style="App.TFrame")
    action_frame.grid(row=2, column=0, sticky="w")
    _primary_button(action_frame, "Extract File", handle_extract_file).grid(
        row=0, column=0, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )
    open_file_button = _secondary_button(
        action_frame,
        "Open Extracted File",
        handle_open_file,
        state="disabled",
    )
    open_file_button.grid(row=0, column=1, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y)
    open_folder_button = _secondary_button(
        action_frame,
        "Open Extracted Folder",
        handle_open_folder,
        state="disabled",
    )
    open_folder_button.grid(row=0, column=2, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y)
    _secondary_button(action_frame, "Clear", handle_clear).grid(
        row=0, column=3, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )

    return frame


def _build_analyze_tab(notebook, status_var):
    frame = ttk.Frame(notebook, padding=PAGE_PAD, style="App.TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    input_section = _create_section(frame, "Input")
    input_section.grid(row=0, column=0, sticky="ew", pady=(0, SECTION_GAP))
    input_section.columnconfigure(1, weight=1)

    analyze_label = _card_label(input_section, "Image to analyze:")
    analyze_label.grid(row=0, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    analyze_entry = ttk.Entry(input_section)
    analyze_entry.grid(row=0, column=1, sticky="ew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    analyze_button = _secondary_button(
        input_section,
        "Browse",
        command=lambda: _select_file_path(
            analyze_entry, [("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")]
        ),
    )
    analyze_button.grid(row=0, column=2, padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    report_section = _create_section(frame, "Report")
    report_section.grid(row=1, column=0, sticky="nsew", pady=(0, SECTION_GAP))
    report_section.columnconfigure(1, weight=1)
    report_section.rowconfigure(0, weight=1)

    report_label = _card_label(report_section, "Analysis report:")
    report_label.grid(row=0, column=0, sticky="nw", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    report_output = scrolledtext.ScrolledText(report_section, height=12, wrap="word")
    report_output.grid(
        row=0, column=1, columnspan=2, sticky="nsew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y
    )
    _style_text_widget(report_output)

    def handle_analyze():
        image_path = _get_path(analyze_entry)
        if image_path is None:
            messagebox.showwarning("Missing Image", "Please select an image to analyze.")
            return
        if not image_path.exists():
            messagebox.showerror("Missing Image", "The image file does not exist.")
            return

        try:
            report = analyze_image(image_path)
            _clear_text(report_output)
            report_output.insert(tk.END, format_analysis_report(report))
            _set_status(status_var, "Analysis completed")
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            _set_status(status_var, "Analysis failed")
        except Exception:
            messagebox.showerror("Error", "Something went wrong while analyzing the image.")
            _set_status(status_var, "Analysis failed")

    def handle_clear():
        _clear_entry(analyze_entry)
        _clear_text(report_output)
        _set_status(status_var, "Ready")

    action_frame = ttk.Frame(frame, style="App.TFrame")
    action_frame.grid(row=2, column=0, sticky="w")
    _primary_button(action_frame, "Analyze", handle_analyze).grid(
        row=0, column=0, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )
    _secondary_button(action_frame, "Clear", handle_clear).grid(
        row=0, column=1, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )

    return frame


def _build_compare_tab(notebook, status_var):
    frame = ttk.Frame(notebook, padding=PAGE_PAD, style="App.TFrame")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    input_section = _create_section(frame, "Input")
    input_section.grid(row=0, column=0, sticky="ew", pady=(0, SECTION_GAP))
    input_section.columnconfigure(1, weight=1)

    original_label = _card_label(input_section, "Original image:")
    original_label.grid(row=0, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    original_entry = ttk.Entry(input_section)
    original_entry.grid(row=0, column=1, sticky="ew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    original_button = _secondary_button(
        input_section,
        "Browse",
        command=lambda: _select_file_path(
            original_entry, [("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")]
        ),
    )
    original_button.grid(row=0, column=2, padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    stego_label = _card_label(input_section, "Stego image:")
    stego_label.grid(row=1, column=0, sticky="w", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    stego_entry = ttk.Entry(input_section)
    stego_entry.grid(row=1, column=1, sticky="ew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    stego_button = _secondary_button(
        input_section,
        "Browse",
        command=lambda: _select_file_path(
            stego_entry, [("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")]
        ),
    )
    stego_button.grid(row=1, column=2, padx=FIELD_PAD_X, pady=FIELD_PAD_Y)

    report_section = _create_section(frame, "Report")
    report_section.grid(row=1, column=0, sticky="nsew", pady=(0, SECTION_GAP))
    report_section.columnconfigure(1, weight=1)
    report_section.rowconfigure(0, weight=1)

    report_label = _card_label(report_section, "Comparison report:")
    report_label.grid(row=0, column=0, sticky="nw", padx=FIELD_PAD_X, pady=FIELD_PAD_Y)
    report_output = scrolledtext.ScrolledText(report_section, height=12, wrap="word")
    report_output.grid(
        row=0, column=1, columnspan=2, sticky="nsew", padx=FIELD_PAD_X, pady=FIELD_PAD_Y
    )
    _style_text_widget(report_output)

    def handle_compare():
        original_path = _get_path(original_entry)
        stego_path = _get_path(stego_entry)

        if original_path is None or stego_path is None:
            messagebox.showwarning("Missing Image", "Please select both images to compare.")
            return
        if not original_path.exists() or not stego_path.exists():
            messagebox.showerror("Missing Image", "One or both image files do not exist.")
            return

        try:
            report = compare_images(original_path, stego_path)
            _clear_text(report_output)
            report_output.insert(tk.END, format_comparison_report(report))
            _set_status(status_var, "Comparison completed")
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            _set_status(status_var, "Comparison failed")
        except Exception:
            messagebox.showerror("Error", "Something went wrong while comparing the images.")
            _set_status(status_var, "Comparison failed")

    def handle_clear():
        _clear_entry(original_entry)
        _clear_entry(stego_entry)
        _clear_text(report_output)
        _set_status(status_var, "Ready")

    action_frame = ttk.Frame(frame, style="App.TFrame")
    action_frame.grid(row=2, column=0, sticky="w")
    _primary_button(action_frame, "Compare", handle_compare).grid(
        row=0, column=0, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )
    _secondary_button(action_frame, "Clear", handle_clear).grid(
        row=0, column=1, padx=BUTTON_PAD_X, pady=BUTTON_PAD_Y
    )

    return frame


def launch_gui():
    output_dir = BASE_DIR / "output"
    extracted_dir = BASE_DIR / "extracted"
    create_required_folders([output_dir, extracted_dir])

    root = tk.Tk()
    root.title("Secure Steganography Toolkit")
    root.geometry("1100x800")
    root.minsize(960, 680)
    root.configure(bg=BG_COLOR)
    _apply_theme(root)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=0)

    container = ttk.Frame(root, style="App.TFrame", padding=PAGE_PAD)
    container.grid(row=0, column=0, sticky="nsew")
    container.columnconfigure(0, weight=1)
    container.rowconfigure(2, weight=1)

    header = ttk.Frame(container, style="App.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    header.columnconfigure(0, weight=1)

    title = ttk.Label(header, text="Secure Steganography Toolkit", style="Title.TLabel")
    title.grid(row=0, column=0, sticky="w")
    subtitle = ttk.Label(
        header,
        text="Hide and extract encrypted messages and files inside PNG images",
        style="Subtitle.TLabel",
    )
    subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

    toolbar = ttk.Frame(container, style="App.TFrame")
    toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 10))
    toolbar.columnconfigure(1, weight=1)

    status_var = tk.StringVar(value="Ready")

    def handle_open_output():
        try:
            open_folder(output_dir)
            _set_status(status_var, "Output folder opened")
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            _set_status(status_var, "Unable to open output folder")

    _secondary_button(
        toolbar,
        "Open Output Folder",
        handle_open_output,
    ).grid(row=0, column=0, padx=(0, 8), pady=(0, 2))

    notebook = ttk.Notebook(container)
    notebook.grid(row=2, column=0, sticky="nsew")

    notebook.add(_build_hide_text_tab(notebook, output_dir, status_var), text="Hide Text")
    notebook.add(
        _build_extract_text_tab(notebook, extracted_dir, status_var), text="Extract Text"
    )
    notebook.add(_build_hide_file_tab(notebook, output_dir, status_var), text="Hide File")
    notebook.add(
        _build_extract_file_tab(notebook, extracted_dir, status_var), text="Extract File"
    )
    notebook.add(_build_analyze_tab(notebook, status_var), text="Analyze Image")
    notebook.add(_build_compare_tab(notebook, status_var), text="Compare Images")

    status_bar = ttk.Label(root, textvariable=status_var, style="Status.TLabel", anchor="w")
    status_bar.grid(row=1, column=0, sticky="ew")

    root.mainloop()


if __name__ == "__main__":
    launch_gui()

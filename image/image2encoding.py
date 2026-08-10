#!/usr/bin/env python3

"""
imagescript.py

Convert an image to a Base64 encoded text file and restore
the original image from that text file.

USAGE
-----

1. Image -> TXT

    python imagescript.py image.png

Creates:

    imageencod.txt


2. TXT -> Image

    python imagescript.py imageencod.txt --reverseimage

Creates:

    imageencod_restored.png


3. Image -> TXT explicitly

    python imagescript.py image.png --reverttostring

Creates:

    imageencod.txt


Supported image formats:
    PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP, ICO, etc.

No external Python packages are required.
"""

import argparse
import base64
import binascii
import sys
from pathlib import Path


# ============================================================
# IMAGE -> BASE64 STRING -> TXT
# ============================================================

def image_to_base64(image_path: Path, output_txt: Path) -> None:
    """
    Read an image as binary data, convert it to Base64,
    and save the Base64 string into a TXT file.
    """

    if not image_path.exists():
        raise FileNotFoundError(
            f"Input image does not exist: {image_path}"
        )

    if not image_path.is_file():
        raise ValueError(
            f"Input path is not a file: {image_path}"
        )

    # Read original image bytes
    image_bytes = image_path.read_bytes()

    if not image_bytes:
        raise ValueError(
            f"Image file is empty: {image_path}"
        )

    # Convert binary data to Base64
    encoded_bytes = base64.b64encode(image_bytes)

    # Convert Base64 bytes to normal string
    encoded_string = encoded_bytes.decode("ascii")

    # Save Base64 string to TXT
    output_txt.write_text(
        encoded_string,
        encoding="ascii"
    )

    print()
    print("=" * 70)
    print("IMAGE -> BASE64 STRING")
    print("=" * 70)
    print(f"Input Image : {image_path}")
    print(f"Output TXT  : {output_txt}")
    print(f"Image Size  : {len(image_bytes):,} bytes")
    print(f"String Size : {len(encoded_string):,} characters")
    print("=" * 70)
    print("Conversion completed successfully.")
    print()


# ============================================================
# BASE64 STRING -> IMAGE
# ============================================================

def base64_to_image(
    txt_path: Path,
    output_image: Path
) -> None:
    """
    Read Base64 text from a TXT file and recreate
    the original image.
    """

    if not txt_path.exists():
        raise FileNotFoundError(
            f"TXT file does not exist: {txt_path}"
        )

    if not txt_path.is_file():
        raise ValueError(
            f"Input path is not a file: {txt_path}"
        )

    # Read Base64 string
    encoded_string = txt_path.read_text(
        encoding="ascii"
    ).strip()

    if not encoded_string:
        raise ValueError(
            f"TXT file is empty: {txt_path}"
        )

    # Remove accidental whitespace/newlines
    encoded_string = "".join(
        encoded_string.split()
    )

    try:
        # Convert Base64 string back to binary
        image_bytes = base64.b64decode(
            encoded_string,
            validate=True
        )

    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            "The TXT file does not contain valid Base64 data."
        ) from exc

    if not image_bytes:
        raise ValueError(
            "Decoded image data is empty."
        )

    # Save original binary image
    output_image.write_bytes(image_bytes)

    print()
    print("=" * 70)
    print("BASE64 STRING -> IMAGE")
    print("=" * 70)
    print(f"Input TXT   : {txt_path}")
    print(f"Output Image: {output_image}")
    print(f"Image Size  : {len(image_bytes):,} bytes")
    print("=" * 70)
    print("Image restored successfully.")
    print()


# ============================================================
# FIND OUTPUT IMAGE EXTENSION
# ============================================================

def detect_image_extension(image_bytes: bytes) -> str:
    """
    Detect the original image format from its binary signature.

    This is useful when restoring an image from a TXT file
    without knowing the original extension.
    """

    # PNG
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"

    # JPEG
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"

    # GIF
    if image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return ".gif"

    # BMP
    if image_bytes.startswith(b"BM"):
        return ".bmp"

    # TIFF - little endian
    if image_bytes.startswith(b"II*\x00"):
        return ".tiff"

    # TIFF - big endian
    if image_bytes.startswith(b"MM\x00*"):
        return ".tiff"

    # WEBP
    if (
        image_bytes.startswith(b"RIFF")
        and len(image_bytes) >= 12
        and image_bytes[8:12] == b"WEBP"
    ):
        return ".webp"

    # ICO
    if image_bytes.startswith(b"\x00\x00\x01\x00"):
        return ".ico"

    # Unknown format
    return ".bin"


# ============================================================
# RESTORE IMAGE WITH AUTOMATIC EXTENSION
# ============================================================

def restore_image_auto(txt_path: Path) -> None:
    """
    Restore image from TXT and automatically detect
    the image extension.
    """

    encoded_string = txt_path.read_text(
        encoding="ascii"
    ).strip()

    encoded_string = "".join(
        encoded_string.split()
    )

    try:
        image_bytes = base64.b64decode(
            encoded_string,
            validate=True
        )
    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            "The TXT file does not contain valid Base64 data."
        ) from exc

    extension = detect_image_extension(image_bytes)

    output_image = (
        txt_path.parent
        / f"{txt_path.stem}_restored{extension}"
    )

    output_image.write_bytes(image_bytes)

    print()
    print("=" * 70)
    print("BASE64 STRING -> ORIGINAL IMAGE")
    print("=" * 70)
    print(f"Input TXT   : {txt_path}")
    print(f"Output Image: {output_image}")
    print(f"Detected    : {extension}")
    print(f"Image Size  : {len(image_bytes):,} bytes")
    print("=" * 70)
    print("Image restored successfully.")
    print()


# ============================================================
# COMMAND LINE
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert images to Base64 TXT and restore "
            "images from Base64 TXT."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "input",
        help=(
            "Input image or Base64 TXT file.\n"
            "Example: image.png\n"
            "Example: imageencod.txt"
        )
    )

    parser.add_argument(
        "--reverseimage",
        "--reverimage",
        "--reverse-image",
        dest="reverse_image",
        action="store_true",
        help=(
            "Convert Base64 TXT back to the original image."
        )
    )

    parser.add_argument(
        "--reverttostring",
        "--reverse-string",
        "--revertstring",
        dest="revert_to_string",
        action="store_true",
        help=(
            "Convert image to Base64 TXT."
        )
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    try:

        # ----------------------------------------------------
        # TXT -> IMAGE
        # ----------------------------------------------------

        if args.reverse_image:

            if input_path.suffix.lower() != ".txt":
                print(
                    "WARNING: Reverse image mode normally "
                    "expects a .txt file."
                )

            restore_image_auto(input_path)

        # ----------------------------------------------------
        # IMAGE -> TXT
        # ----------------------------------------------------

        else:

            # Both normal mode and --reverttostring
            # perform image -> Base64 TXT.
            output_txt = (
                input_path.parent
                / f"{input_path.stem}encod.txt"
            )

            image_to_base64(
                input_path,
                output_txt
            )

    except FileNotFoundError as exc:
        print()
        print(f"ERROR: {exc}")
        print()
        sys.exit(1)

    except ValueError as exc:
        print()
        print(f"ERROR: {exc}")
        print()
        sys.exit(1)

    except PermissionError as exc:
        print()
        print(f"ERROR: Permission denied: {exc}")
        print()
        sys.exit(1)

    except Exception as exc:
        print()
        print(f"UNEXPECTED ERROR: {exc}")
        print()
        sys.exit(1)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
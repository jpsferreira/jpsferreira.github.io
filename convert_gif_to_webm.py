#!/usr/bin/env python3
"""
Convert GIF files to WebM video format for web optimization.
WebM typically provides better compression and smaller file sizes than GIF.

Usage:
    python convert_gif_to_webm.py input.gif output.webm
    python convert_gif_to_webm.py input.gif  # outputs input.webm
    python convert_gif_to_webm.py images/    # converts all GIFs in directory
"""

import subprocess
import sys
import os
from pathlib import Path


def convert_gif_to_webm(input_path, output_path=None, quality=30, fps=None):
    """
    Convert a GIF file to WebM format using ffmpeg.

    Args:
        input_path: Path to input GIF file
        output_path: Path to output WebM file (optional, defaults to input name with .webm)
        quality: CRF quality value (0-63, lower is better quality, default: 30)
        fps: Frame rate (optional, maintains original if not specified)

    Returns:
        True if successful, False otherwise
    """
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist")
        return False

    if not input_path.suffix.lower() == ".gif":
        print(f"Error: Input file '{input_path}' is not a GIF")
        return False

    # Set output path if not provided
    if output_path is None:
        output_path = input_path.with_suffix(".webm")
    else:
        output_path = Path(output_path)

    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-c:v",
        "libvpx-vp9",  # VP9 codec
        "-crf",
        str(quality),  # Quality setting
        "-b:v",
        "0",  # Variable bitrate
    ]

    # Add fps if specified
    if fps:
        cmd.extend(["-r", str(fps)])

    # Add output file and overwrite flag
    cmd.extend(["-y", str(output_path)])

    try:
        print(f"Converting {input_path.name} to {output_path.name}...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Get file sizes
        input_size = input_path.stat().st_size
        output_size = output_path.stat().st_size
        reduction = (1 - output_size / input_size) * 100

        print(f"✓ Conversion successful!")
        print(f"  Input:  {input_size:,} bytes ({input_size / 1024:.1f} KB)")
        print(f"  Output: {output_size:,} bytes ({output_size / 1024:.1f} KB)")
        print(f"  Size reduction: {reduction:.1f}%")

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def convert_directory(directory, quality=30, fps=None):
    """Convert all GIF files in a directory to WebM."""
    directory = Path(directory)

    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory")
        return

    gif_files = list(directory.glob("*.gif"))

    if not gif_files:
        print(f"No GIF files found in '{directory}'")
        return

    print(f"Found {len(gif_files)} GIF file(s) in '{directory}'")

    successful = 0
    for gif_file in gif_files:
        if convert_gif_to_webm(gif_file, quality=quality, fps=fps):
            successful += 1
        print()  # Empty line between conversions

    print(f"Converted {successful}/{len(gif_files)} files successfully")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nError: No input file or directory specified")
        sys.exit(1)

    input_arg = sys.argv[1]

    # Check if ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg is not installed or not in PATH")
        print(
            "Install ffmpeg: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
        )
        sys.exit(1)

    # Handle directory
    if Path(input_arg).is_dir():
        convert_directory(input_arg)
        sys.exit(0)

    # Handle single file
    output_arg = sys.argv[2] if len(sys.argv) > 2 else None

    success = convert_gif_to_webm(input_arg, output_arg)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

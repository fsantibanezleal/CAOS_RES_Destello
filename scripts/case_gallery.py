#!/usr/bin/env python3
"""Render one panorama per case (the scene around the fly: the middle stimulus of each case at half its duration,
central rays only) as
greyscale PNGs for the wiki: 360 x 180 pixels, straight ahead at the centre and the fly's left on the left, as the
fly sees it from inside the sphere.

Usage: python scripts/case_gallery.py OUT_DIR
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))

from cases import CASES, FPS  # noqa: E402
from scene import render  # noqa: E402


def png(path: Path, image: np.ndarray) -> None:
    """A minimal greyscale PNG writer (8-bit), so the figure needs no imaging library."""
    h, w = image.shape
    raw = b"".join(b"\x00" + image[y].tobytes() for y in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def panorama(scene, t: float, width: int = 360, height: int = 180) -> np.ndarray:
    lon = np.deg2rad(180.0 - (np.arange(width) + 0.5) * 360.0 / width)      # left of the image: the fly's left
    lat = np.deg2rad(90.0 - (np.arange(height) + 0.5) * 180.0 / height)
    lo, la = np.meshgrid(lon, lat)
    dirs = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1).reshape(-1, 3)
    single = (dirs[:, None, :], np.ones(1))                                   # the central ray only
    frame = render(scene, dirs, t, 1 / FPS, single)
    return np.round(np.clip(frame.luminance, 0, 1) * 255).astype(np.uint8).reshape(height, width)


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for case, make in CASES.items():
        stimuli = make()
        stim = stimuli[len(stimuli) // 2]
        png(out / f"case-{case.lower()}.png", panorama(stim.scene(), stim.duration_s / 2))
        print(case, stim.variant)


if __name__ == "__main__":
    main()

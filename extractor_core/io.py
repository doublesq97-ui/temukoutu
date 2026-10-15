"""Bounded input decoding and atomic local writes. No network or model downloads."""
import io
import os
import uuid
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 16_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def read_image(data: bytes) -> Image.Image:
    if len(data) > MAX_BYTES:
        raise ValueError("文件超过 25MB 限制")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("仅支持实际格式为 JPG、PNG、WebP 的图片")
                if probe.width * probe.height > MAX_PIXELS or min(probe.size) < 8:
                    raise ValueError("图片需至少 8×8，且不超过 1600 万像素")
                probe.verify()
            with Image.open(io.BytesIO(data)) as source:
                source.load()
                return ImageOps.exif_transpose(source).convert("RGBA")
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ValueError("图片损坏、格式无效或解码尺寸过大") from exc


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temp.write_bytes(data)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def png_bytes(image):
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def save_png(path, image):
    atomic_bytes(path, png_bytes(image))

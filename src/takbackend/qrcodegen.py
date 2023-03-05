"""Wrap qrcode library so we always generate things in standard way

FIXME: turn into a microservice and use qrcode-styled
"""
import logging
import io
import base64

import qrcode
from libadvian.binpackers import ensure_str

LOGGER = logging.getLogger(__name__)


def create_qrcode(data: str) -> bytes:
    """Return the image as bytes"""
    qrgen = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qrgen.add_data(data)
    qrgen.make(fit=True)
    img = qrgen.make_image()
    buffer = io.BytesIO()
    img.save(buffer, "WEBP")
    buffer.seek(0)
    return buffer.read()


def create_qrcode_b64(data: str) -> str:
    """Return the qrcode as b64 string"""
    return ensure_str(base64.b64encode(create_qrcode(data)))

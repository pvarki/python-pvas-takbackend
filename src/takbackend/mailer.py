"""Initialize email handling backend (fastapi-mail)"""
from typing import Optional
import logging

from fastapi_mail import FastMail, ConnectionConfig

from .config import TEMPLATES_PATH

# FIXME: Should probably be part of some common arkiapihelpers package
LOGGER = logging.getLogger(__name__)
MAILER: Optional[FastMail] = None


def singleton() -> FastMail:
    """Get singleton configured mailer instance"""
    global MAILER  # pylint: disable=W0603
    if MAILER is None:
        MAILER = FastMail(
            ConnectionConfig(TEMPLATE_FOLDER=TEMPLATES_PATH, _env_file=".env", _env_file_encoding="utf-8")
        )
    return MAILER

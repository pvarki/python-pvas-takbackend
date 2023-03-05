"""Views for Client objects"""
import logging

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette import status
from arkia11napi.helpers import get_or_404


from ..config import TEMPLATES_PATH
from ..models import ClientSequence


LOGGER = logging.getLogger(__name__)
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_PATH))
CLIENTS_ROUTER = APIRouter()

# FIXME: semantically GETs should be idempotent, but can we solve it in any reasonable way ??
@CLIENTS_ROUTER.get(
    "/api/v1/sequences/nextclient/{pkstr}", tags=["clients"], response_class=RedirectResponse, name="get_next_client"
)
async def get_next_client(pkstr: str, request: Request) -> RedirectResponse:
    """Get next client in sequence"""
    sequence = await get_or_404(ClientSequence, pkstr)

    client = await sequence.next_client()
    destination = request.url_for("get_client_instructions", pkstr=str(client.pk))

    resp = RedirectResponse(str(destination), status_code=status.HTTP_302_FOUND)
    return resp

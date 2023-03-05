"""Instruction views"""
import logging
from pathlib import Path
import base64

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from arkia11napi.helpers import get_or_404


from ..config import TEMPLATES_PATH
from ..models import TAKInstance, Client
from .. import config

LOGGER = logging.getLogger(__name__)
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_PATH))
INSTRUCTIONS_ROUTER = APIRouter()


@INSTRUCTIONS_ROUTER.get(
    "/api/v1/tak/instances/{pkstr}/instructions",
    tags=["tak-instances"],
    response_class=HTMLResponse,
    name="owner_instructions",
)
async def get_owner_instructions(request: Request, pkstr: str) -> Response:
    """Show instructions for the owner"""
    instance = await get_or_404(TAKInstance, pkstr)
    if not instance.tfoutputs:
        if instance.tfcompleted:
            raise HTTPException(status_code=409, detail="Terraform information not available but pipeline completed")
        raise HTTPException(status_code=501, detail="Terraform information not received yet")
    return TEMPLATES.TemplateResponse(
        "owner_instructions.html",
        {
            "request": request,
            "instructions_pdf": config.INSTRUCTIONS_URL,
            "taisteluajatus_pdf": config.TAKORTTI_URL,
            "templates_zip": config.DOCTEMPLATE_URL,
        },
    )


async def get_or_create_client_zip(instance: TAKInstance, name: str) -> Path:
    """Get the given client to a temporary directory"""
    raise NotImplementedError()


@INSTRUCTIONS_ROUTER.get(
    "/api/v1/clients/{pkstr}/instructions",
    tags=["clients"],
    response_class=HTMLResponse,
    name="get_client_instructions",
)
async def get_client_instructions(request: Request, pkstr: str) -> Response:
    """Get next client in sequence"""
    client = await get_or_404(Client, pkstr)
    instance = await TAKInstance.get(client.server)
    if not instance.tfoutputs:
        if instance.tfcompleted:
            raise HTTPException(status_code=409, detail="Terraform information not available but pipeline completed")
        raise HTTPException(status_code=501, detail="Terraform information not received yet")

    zipfile = await get_or_create_client_zip(instance, client.name)
    with open(zipfile, "rb") as fpntr:
        client_zip_b64 = base64.urlsafe_b64encode(fpntr.read())

    return TEMPLATES.TemplateResponse(
        "client_instructions.html",
        {
            "request": request,
            "instructions_pdf": config.INSTRUCTIONS_URL,
            "taisteluajatus_pdf": config.TAKORTTI_URL,
            "client_zip_b64": client_zip_b64,
            "client_name": client.name,
        },
    )

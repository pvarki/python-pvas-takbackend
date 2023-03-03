"""Instruction views"""
import logging

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from arkia11napi.helpers import get_or_404


from ..config import TEMPLATES_PATH
from ..models import TAKInstance
from .. import config

LOGGER = logging.getLogger(__name__)
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_PATH))
INSTRUCTIONS_ROUTER = APIRouter()


@INSTRUCTIONS_ROUTER.get(
    "/api/v1/tak/instances/{pkstr}/instructions",
    tags=["tak-instances"],
    response_class=HTMLResponse,
    name="enduser_instructions",
)
async def get_instructions(request: Request, pkstr: str) -> Response:
    """Show instructions HTML with server address etc"""
    instance = await get_or_404(TAKInstance, pkstr)
    if not instance.tfoutputs:
        if instance.tfcompleted:
            raise HTTPException(status_code=409, detail="Terraform information not available but pipeline completed")
        raise HTTPException(status_code=501, detail="Terraform information not received yet")
    return TEMPLATES.TemplateResponse(
        "instructions.html",
        {
            "request": request,
            "instructions_pdf": config.INSTRUCTIONS_URL,
            "taisteluajatus_pdf": config.TAKORTTI_URL,
            "templates_zip": config.DOCTEMPLATE_URL,
            "dns_name": instance.tfoutputs["dns_name"]["value"],
        },
    )

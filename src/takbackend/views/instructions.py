"""Instruction views"""
from typing import Dict, Any, Tuple, cast
import logging
from pathlib import Path
import base64
import tempfile

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from arkia11napi.helpers import get_or_404
from libadvian.binpackers import ensure_str


from ..config import TEMPLATES_PATH
from ..models import TAKInstance, Client, ClientSequence
from .. import config
from ..qrcodegen import create_qrcode_b64
from ..certsapihelpers import ping_certsapi, get_or_create_client_zip

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
    retry_headers = {"Retry-After": "120"}
    if not instance.tfoutputs:
        if instance.tfcompleted:
            raise HTTPException(status_code=409, detail="Terraform information not available but pipeline completed")
        raise HTTPException(status_code=501, detail="Terraform information not received yet", headers=retry_headers)
    if not await ping_certsapi(instance):
        raise HTTPException(
            status_code=501, detail="TAK server is not yet fully up, try again in a few minutes", headers=retry_headers
        )

    sequences = [
        {"prefix": seq.prefix, "url": request.url_for("get_next_client", pkstr=seq.pk)}
        for seq in await ClientSequence.list_instance_sequences(instance)
    ]

    instance.tfoutputs = cast(Dict[str, Any], instance.tfoutputs)
    instance.tfinputs = cast(Dict[str, Any], instance.tfinputs)
    return TEMPLATES.TemplateResponse(
        "owner_instructions.html",
        {
            "request": request,
            "instructions_pdf": config.INSTRUCTIONS_URL,
            "taisteluajatus_pdf": config.TAKORTTI_URL,
            "templates_zip": config.DOCTEMPLATE_URL,
            "client_sequences_urls": sequences,
            "create_qrcode_b64": create_qrcode_b64,
            "friendly_name": instance.tfinputs.get("server_name", "undefined"),
        },
    )


async def client_instructions_common(pkstr: str) -> Tuple[Client, TAKInstance]:
    """Dont' Repeat Yourself, the common stuff"""
    client = await get_or_404(Client, pkstr)
    instance = await TAKInstance.get(client.server)
    retry_headers = {"Retry-After": "120"}
    if not instance.tfoutputs:
        if instance.tfcompleted:
            raise HTTPException(status_code=409, detail="Terraform information not available but pipeline completed")
        raise HTTPException(status_code=501, detail="Terraform information not received yet", headers=retry_headers)
    if not await ping_certsapi(instance):
        raise HTTPException(
            status_code=501, detail="TAK server is not yet fully up, try again in a few minutes", headers=retry_headers
        )

    return client, instance


@INSTRUCTIONS_ROUTER.get(
    "/api/v1/tak/clients/{pkstr}/instructions",
    tags=["tak-clients"],
    response_class=HTMLResponse,
    name="get_client_instructions",
)
async def get_client_instructions(request: Request, pkstr: str) -> Response:
    """Get instructions etc for this unique client"""
    client, instance = await client_instructions_common(pkstr)

    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        if not await get_or_create_client_zip(instance, client.name, Path(tmp.name)):
            raise RuntimeError("Could not get client zip")
        with open(tmp.name, "rb") as fpntr:
            client_zip_b64 = base64.b64encode(fpntr.read())

    instance.tfoutputs = cast(Dict[str, Any], instance.tfoutputs)
    instance.tfinputs = cast(Dict[str, Any], instance.tfinputs)
    return TEMPLATES.TemplateResponse(
        "client_instructions.html",
        {
            "request": request,
            "instructions_pdf": config.INSTRUCTIONS_URL,
            "taisteluajatus_pdf": config.TAKORTTI_URL,
            "client_zip_b64": ensure_str(client_zip_b64),
            "client_name": client.name,
            "friendly_name": instance.tfinputs.get("server_name", "undefined"),
        },
    )


@INSTRUCTIONS_ROUTER.get(
    "/api/v1/tak/clients/{pkstr}/instructions/zip",
    tags=["tak-clients"],
    name="get_client_zipfile",
    responses={200: {"content": {"application/zip": {}}}},
)
async def get_client_zipfile(pkstr: str) -> Response:
    """URL endpoint for getting the client zip file in case the data url is a problem"""
    client, instance = await client_instructions_common(pkstr)

    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        if not await get_or_create_client_zip(instance, client.name, Path(tmp.name)):
            raise RuntimeError("Could not get client zip")

        return Response(
            content=tmp.read(),
            media_type="application/zip",
            headers={"Content-Disposition": f"""attachment;filename="{client.name}.zip"""},
        )

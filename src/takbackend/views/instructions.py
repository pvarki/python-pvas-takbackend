"""Instruction views"""
from typing import Optional, Dict, Any, cast
import logging
from pathlib import Path
import base64
import tempfile

import aiohttp
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from arkia11napi.helpers import get_or_404
from libadvian.binpackers import ensure_str


from ..config import TEMPLATES_PATH
from ..models import TAKInstance, Client, ClientSequence
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

    sequences = [
        {"prefix": seq.prefix, "url": request.url_for("get_next_client", pkstr=seq.pk)}
        for seq in await ClientSequence.list_instance_sequences(instance)
    ]

    return TEMPLATES.TemplateResponse(
        "owner_instructions.html",
        {
            "request": request,
            "instructions_pdf": config.INSTRUCTIONS_URL,
            "taisteluajatus_pdf": config.TAKORTTI_URL,
            "templates_zip": config.DOCTEMPLATE_URL,
            "client_sequences_urls": sequences,
        },
    )


async def get_or_create_client_zip(instance: TAKInstance, name: str, filepath: Path) -> bool:
    """Get the given client to a temporary directory"""
    instance.tfoutputs = cast(Dict[str, Any], instance.tfoutputs)
    bearer_token = instance.tfoutputs["cert_api_token"]["value"]
    dns_name = instance.tfoutputs["dns_name"]["value"]
    api_base = f"https://{dns_name}/api"
    headers = {"Authorization": f"Bearer {bearer_token}"}

    async def get_client_zip(session: aiohttp.ClientSession) -> Optional[bytes]:
        """do the get, DRY"""
        nonlocal api_base, name
        url = f"{api_base}/v1/clients/{name}"
        LOGGER.debug("Trying to get {}".format(url))
        async with session.get(url) as resp:
            LOGGER.debug("Got response {}".format(resp))
            if resp.status != 200:
                return None
            return await resp.read()

    async with aiohttp.ClientSession(headers=headers) as session:
        content = await get_client_zip(session)
        if content is None:
            url = f"{api_base}/v1/clients"
            data = {"name": name}
            LOGGER.debug("POSTing {} to {}".format(data, url))
            async with session.post(url, json=data) as resp:
                resp.raise_for_status()
                content = await resp.read()
        if not content:
            raise ValueError("Could not get zip content")

        with filepath.open("wb") as fpntr:
            fpntr.write(content)

    return True


@INSTRUCTIONS_ROUTER.get(
    "/api/v1/tak/clients/{pkstr}/instructions",
    tags=["tak-clients"],
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

    with tempfile.NamedTemporaryFile() as tmp:
        if not await get_or_create_client_zip(instance, client.name, Path(tmp.name)):
            raise RuntimeError("Could not get client zip")
        with open(tmp.name, "rb") as fpntr:
            client_zip_b64 = base64.b64encode(fpntr.read())

    return TEMPLATES.TemplateResponse(
        "client_instructions.html",
        {
            "request": request,
            "instructions_pdf": config.INSTRUCTIONS_URL,
            "taisteluajatus_pdf": config.TAKORTTI_URL,
            "client_zip_b64": ensure_str(client_zip_b64),
            "client_name": client.name,
        },
    )

"""callbacks for TF etc"""
from typing import Dict, Any, List, cast
import asyncio
import logging

import pendulum
import aiohttp
from fastapi import APIRouter, HTTPException, Request
from starlette import status
from arkia11napi.helpers import get_or_404
from fastapi_mail import MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader

from ..models import TAKInstance
from ..mailer import singleton as getmailer
from ..config import TEMPLATES_PATH, ORDER_READY_SUBJECT
from ..schemas.instance import TAKDBInstance

LOGGER = logging.getLogger(__name__)
CALLBACKS_ROUTER = APIRouter()


async def send_ready_email(instance: TAKInstance, request: Request) -> None:
    """Send the ready email"""
    template = Environment(loader=FileSystemLoader(TEMPLATES_PATH), autoescape=True).get_template(
        "order_ready_email.txt"
    )
    mailer = getmailer()
    msg = MessageSchema(
        subject=ORDER_READY_SUBJECT,
        recipients=[instance.ready_email],
        subtype=MessageType.plain,
        body=template.render(url=request.url_for("owner_instructions", pkstr=str(instance.pk))),
    )
    try:
        await mailer.send_message(msg, template_name="order_ready_email.txt")
    except Exception as exc:  # pylint: disable=W0703
        LOGGER.exception("mail delivery failure {}".format(exc))


async def do_ready_callback(instance: TAKInstance, request: Request) -> None:
    """Do the ready callback"""
    instance.tfinputs = cast(Dict[str, Any], instance.tfinputs)
    pdinstsrc = instance.to_dict()
    pdinstsrc["server_name"] = instance.tfinputs.get("server_name", "undefined")
    pdinst = TAKDBInstance.parse_obj(pdinstsrc)
    pdinst.tfoutputs = None
    pdinst.tfinputs = None
    pdinst.owner_instructions = request.url_for("owner_instructions", pkstr=str(instance.pk))
    data_str = pdinst.json()

    async with aiohttp.ClientSession() as session:
        url = instance.ready_callback_url
        LOGGER.debug("POSTing {} to {}".format(data_str, url))
        async with session.post(url, data=data_str) as resp:
            LOGGER.debug("Got response {}".format(resp))
            if resp.status >= 400:
                LOGGER.error("Got error from callback {}".format(resp))


@CALLBACKS_ROUTER.post(
    "/api/v1/tak/callbacks/{pkstr}", tags=["tak-instances"], status_code=status.HTTP_204_NO_CONTENT, name="tf_callback"
)
async def terraform_callback(request: Request, pkstr: str, tfoutputs: Dict[str, Any]) -> None:
    """one-use callback for pipeline to update instance with TF outputs"""
    instance = await get_or_404(TAKInstance, pkstr)
    if instance.tfcompleted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="May only be called once per instance")
    LOGGER.debug("called for {}, tfoutputs={}".format(pkstr, tfoutputs))
    await instance.update(tfcompleted=pendulum.now("UTC"), tfoutputs=tfoutputs).apply()

    tasks: List[asyncio.Task[Any]] = []
    if instance.ready_email:
        tasks.append(asyncio.create_task(send_ready_email(instance, request), name="send_ready_email"))
    if instance.ready_callback_url:
        tasks.append(asyncio.create_task(do_ready_callback(instance, request), name="do_ready_callback"))

    await asyncio.gather(*tasks)

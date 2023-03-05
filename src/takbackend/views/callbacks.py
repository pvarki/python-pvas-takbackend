"""callbacks for TF etc"""
from typing import Dict, Any
import logging

import pendulum
from fastapi import APIRouter, HTTPException, Request
from starlette import status
from arkia11napi.helpers import get_or_404


from ..models import TAKInstance

from ..mailer import singleton as getmailer
from fastapi_mail import MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader

from ..config import (
    TEMPLATES_PATH,
)

LOGGER = logging.getLogger(__name__)
CALLBACKS_ROUTER = APIRouter()


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

    template = Environment(loader=FileSystemLoader(TEMPLATES_PATH), autoescape=True).get_template("order_ready_email.txt")
    mailer = getmailer()
    msg = MessageSchema(
        subject="Order ready",
        recipients=["paavo.pokkinen@hallatek.com"],
        subtype=MessageType.plain,
        body=template.render(url=request.url_for("enduser_instructions", pkstr=str(instance.pk))),
    )
    try:
        await mailer.send_message(msg, template_name="order_ready_email.txt")
    except Exception as exc:  # pylint: disable=W0703
        LOGGER.exception("mail delivery failure {}".format(exc))

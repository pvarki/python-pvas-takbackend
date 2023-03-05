"""TAKInstance related endpoints"""
from typing import List
import logging
import uuid

import pendulum
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from starlette import status
from arkia11napi.helpers import get_or_404
from arkia11napi.security import JWTBearer, check_acl


from ..config import TEMPLATES_PATH
from ..schemas.instance import TAKDBInstance, TAKInstanceCreate, TAKInstancePager
from ..models import TAKInstance, ClientSequence
from ..pipelineclient import PipeLineClient


LOGGER = logging.getLogger(__name__)
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_PATH))
INSTANCE_ROUTER = APIRouter(dependencies=[Depends(JWTBearer(auto_error=True))])


@INSTANCE_ROUTER.post(
    "/api/v1/tak/instances", tags=["tak-instances"], response_model=TAKDBInstance, status_code=status.HTTP_201_CREATED
)
async def create_instance(request: Request, pdinstance: TAKInstanceCreate) -> TAKDBInstance:
    """Create a new TAKInstance"""
    check_acl(request.state.jwt, "fi.pvarki.takbackend.instance:create")
    data = pdinstance.dict()
    server_name = data.pop("server_name")
    takinstance = TAKInstance(**data)
    takinstance.tfinputs = {
        "server_name": server_name,
    }
    # pylint: disable=invalid-name
    if not takinstance.pk:
        takinstance.pk = uuid.uuid4()  # type: ignore
    # pylint: enable=invalid-name
    callback_url = request.url_for("tf_callback", pkstr=str(takinstance.pk))
    await takinstance.create()
    refresh = await TAKInstance.get(takinstance.pk)
    client = PipeLineClient()
    try:
        await client.create(takinstance, callback_url)
    except Exception as exc:
        LOGGER.exception("Could not trigger pipeline {}".format(exc))
        # Do not leave stuff laying around
        await refresh.delete()
        raise

    if pdinstance.sequence_prefix and pdinstance.sequence_max:
        await ClientSequence.create_for(
            instance=refresh, prefix=pdinstance.sequence_prefix, max_clients=pdinstance.sequence_max
        )

    retsrc = refresh.to_dict()
    retsrc["server_name"] = refresh.tfinputs.get("server_name", "unresolved")
    ret = TAKDBInstance.parse_obj(retsrc)
    if not check_acl(request.state.jwt, "fi.pvarki.takbackend.tfdata:read", auto_error=False):
        ret.tfinputs = None
        ret.tfoutputs = None
    return ret


@INSTANCE_ROUTER.get("/api/v1/tak/instances", tags=["tak-instances"], response_model=TAKInstancePager)
async def list_instances(request: Request) -> TAKInstancePager:
    """List TAKInstance"""
    query = TAKInstance.query.where(
        TAKInstance.deleted == None  # pylint: disable=C0121 ; # "is None" will create invalid query
    )
    if not check_acl(request.state.jwt, "fi.pvarki.takbackend.instance:read", auto_error=False):
        query = query.where(TAKInstance.ownerid == request.state.jwt["userid"])

    instances = await query.gino.all()
    if not instances:
        return TAKInstancePager(items=[], count=0)

    pdinstances: List[TAKDBInstance] = []
    for instance in instances:
        pdinstsrc = instance.to_dict()
        pdinstsrc["server_name"] = instance.tfinputs.get("server_name", None)
        pdinst = TAKDBInstance.parse_obj(pdinstsrc)
        pdinst.tfoutputs = None
        pdinst.tfinputs = None
        if instance.tfcompleted or instance.tfoutputs:
            pdinst.owner_instructions = request.url_for("owner_instructions", pkstr=str(instance.pk))
        pdinstances.append(pdinst)

    return TAKInstancePager(
        count=len(pdinstances),
        items=pdinstances,
    )


@INSTANCE_ROUTER.get("/api/v1/tak/instances/{pkstr}", tags=["tak-instances"], response_model=TAKDBInstance)
async def get_instance(request: Request, pkstr: str) -> TAKDBInstance:
    """Get a single instance"""
    instance = await get_or_404(TAKInstance, pkstr)
    if not check_acl(request.state.jwt, "fi.pvarki.takbackend.instance:read", auto_error=False):
        if instance.ownerid != request.state.jwt["userid"]:
            raise HTTPException(status_code=403, detail="Required privilege not granted.")

    retsrc = instance.to_dict()
    retsrc["server_name"] = instance.tfinputs.get("server_name", "unresolved")
    ret = TAKDBInstance.parse_obj(retsrc)
    if not check_acl(request.state.jwt, "fi.pvarki.takbackend.tfdata:read", auto_error=False):
        ret.tfinputs = None
        ret.tfoutputs = None
    if instance.tfcompleted or instance.tfoutputs:
        ret.owner_instructions = request.url_for("owner_instructions", pkstr=str(instance.pk))

    return ret


@INSTANCE_ROUTER.delete("/api/v1/tak/instances/{pkstr}", tags=["tak-instances"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(request: Request, pkstr: str) -> None:
    """Delete a single instance"""
    instance = await get_or_404(TAKInstance, pkstr)
    if not check_acl(request.state.jwt, "fi.pvarki.takbackend.instance:read", auto_error=False):
        if instance.ownerid != request.state.jwt["userid"]:
            raise HTTPException(status_code=403, detail="Required privilege not granted.")
    client = PipeLineClient()
    try:
        await client.delete(instance)
    except Exception as exc:
        LOGGER.exception("Could not trigger pipeline {}".format(exc))
        raise
    await instance.update(deleted=pendulum.now("UTC")).apply()

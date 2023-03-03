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
from ..schemas.instance import DBInstance, InstanceCreate, InstancePager
from ..models import TAKInstance
from ..pipelineclient import PipeLineClient


LOGGER = logging.getLogger(__name__)
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_PATH))
INSTANCE_ROUTER = APIRouter(dependencies=[Depends(JWTBearer(auto_error=True))])


@INSTANCE_ROUTER.post(
    "/api/v1/tak/instances", tags=["tak-instances"], response_model=DBInstance, status_code=status.HTTP_201_CREATED
)
async def create_instance(request: Request, pdinstance: InstanceCreate) -> DBInstance:
    """Create a new TAKInstance"""
    check_acl(request.state.jwt, "fi.pvarki.takbackend.instance:create")
    data = pdinstance.dict()
    friendly_name = data.pop("friendly_name")
    takinstance = TAKInstance(**data)
    takinstance.tfinputs = {
        "friendly_name": friendly_name,
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
    if not check_acl(request.state.jwt, "fi.pvarki.takbackend.tfdata:read", auto_error=False):
        refresh.tfinputs = None
        refresh.tfoutputs = None
    return DBInstance.parse_obj(refresh.to_dict())


@INSTANCE_ROUTER.get("/api/v1/tak/instances", tags=["tak-instances"], response_model=InstancePager)
async def list_instances(request: Request) -> InstancePager:
    """List TAKInstance"""
    query = TAKInstance.query.where(
        TAKInstance.deleted == None  # pylint: disable=C0121 ; # "is None" will create invalid query
    )
    if not check_acl(request.state.jwt, "fi.pvarki.takbackend.instance:read", auto_error=False):
        query = query.where(TAKInstance.ownerid == request.state.jwt["userid"])

    instances = await query.gino.all()
    if not instances:
        return InstancePager(items=[], count=0)

    pdinstances: List[DBInstance] = []
    for instance in instances:
        pdinst = DBInstance.parse_obj(instance.to_dict())
        pdinst.tfoutputs = None
        pdinst.tfinputs = None
        pdinst.friendly_name = instance.tfinputs.get("friendly_name", None)
        if instance.tfcompleted or instance.tfoutputs:
            pdinst.enduser_instructions = request.url_for("enduser_instructions", pkstr=str(instance.pk))
        pdinstances.append(pdinst)

    return InstancePager(
        count=len(pdinstances),
        items=pdinstances,
    )


@INSTANCE_ROUTER.get("/api/v1/tak/instances/{pkstr}", tags=["tak-instances"], response_model=DBInstance)
async def get_instance(request: Request, pkstr: str) -> DBInstance:
    """Get a single instance"""
    instance = await get_or_404(TAKInstance, pkstr)
    if not check_acl(request.state.jwt, "fi.pvarki.takbackend.instance:read", auto_error=False):
        if instance.ownerid != request.state.jwt["userid"]:
            raise HTTPException(status_code=403, detail="Required privilege not granted.")

    ret = DBInstance.parse_obj(instance.to_dict())
    if not check_acl(request.state.jwt, "fi.pvarki.takbackend.tfdata:read", auto_error=False):
        ret.tfinputs = None
        ret.tfoutputs = None
    ret.friendly_name = instance.tfinputs.get("friendly_name", None)
    if instance.tfcompleted or instance.tfoutputs:
        ret.enduser_instructions = request.url_for("enduser_instructions", pkstr=str(instance.pk))

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

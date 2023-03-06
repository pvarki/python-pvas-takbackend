"""helpers for dealing with the certs api on the actual takserver instance"""
from typing import Optional, Any, Tuple, Dict, cast
import logging
from pathlib import Path

import aiohttp
from aiohttp.client_exceptions import ClientError

from .models import TAKInstance

LOGGER = logging.getLogger(__name__)


def get_http_options(instance: TAKInstance) -> Tuple[str, Dict[str, str]]:
    """get the api base and auth (etc headers"""
    instance.tfoutputs = cast(Dict[str, Any], instance.tfoutputs)
    bearer_token = instance.tfoutputs["cert_api_token"]["value"]
    dns_name = instance.tfoutputs["dns_name"]["value"]
    api_base = f"https://{dns_name}/api"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    return api_base, headers


async def ping_certsapi(instance: TAKInstance) -> bool:
    """Check that certsapi is up"""
    api_base, headers = get_http_options(instance)
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            url = f"{api_base}/v1"
            LOGGER.debug("GETting {}".format(url))
            async with session.get(url) as resp:
                if resp.status == 200:
                    return True
                LOGGER.info("Non 200 response {}".format(resp))
    except ClientError as exc:
        LOGGER.info("exception {} while GETting {}".format(exc, url))

    return False


async def get_or_create_client_zip(instance: TAKInstance, name: str, filepath: Path) -> bool:
    """Get the given client to a temporary directory"""
    api_base, headers = get_http_options(instance)

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

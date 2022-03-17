from pathlib import Path
from typing import Any

from fastapi import APIRouter, UploadFile

from services.pulp import get_pulp_client

router = APIRouter()


RPM_PACKAGES_PATH = "/content/rpm/packages/"
DEB_PACKAGES_PATH = "/content/deb/packages/"


@router.get("/packages/")
async def list_packages() -> Any:
    # TODO: figure out how to combine these requests
    packages = []

    async with get_pulp_client() as pulp_client:
        yum_resp = await pulp_client.get(RPM_PACKAGES_PATH)
        packages.append(yum_resp.json())
        apt_resp = await pulp_client.get(DEB_PACKAGES_PATH)
        packages.append(apt_resp.json())
        return packages


@router.post("/packages/")
async def create_package(file: UploadFile) -> Any:
    files = {"file": file.file}
    data = {"relative_path": file.filename}

    async with get_pulp_client() as pulp_client:
        if Path(file.filename).suffix == ".rpm":
            resp = await pulp_client.post(RPM_PACKAGES_PATH, files=files, data=data)
        if Path(file.filename).suffix == ".deb":
            resp = await pulp_client.post(DEB_PACKAGES_PATH, files=files, data=data)

        return resp.json()

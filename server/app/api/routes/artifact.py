from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import AnyHttpUrl

from app.api.auth import requires_package_admin_or_publisher
from app.core.schemas import ArtifactResponse
from app.services.pulp.api import ArtifactApi

router = APIRouter()


@router.post("/artifacts/", dependencies=[Depends(requires_package_admin_or_publisher)])
async def create_artifact(
    file: Optional[UploadFile] = None,
    url: Optional[AnyHttpUrl] = None,
) -> ArtifactResponse:

    if not file and not url:
        raise HTTPException(status_code=422, detail="Must upload a file or specify url.")

    if url:
        resp = httpx.get(url)
        file = UploadFile(Path(resp.url.path).name)
        await file.write(resp.content)
        await file.seek(0)
    assert file is not None

    data = {"file": file}

    return await ArtifactApi.find_or_create(data)

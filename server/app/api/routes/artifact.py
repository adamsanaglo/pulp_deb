from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import AnyHttpUrl

from app.api.auth import requires_package_admin_or_publisher
from app.core.schemas import ArtifactResponse
from app.services.pulp.api import ArtifactApi

router = APIRouter()


@router.post(
    "/artifacts/",
    dependencies=[Depends(requires_package_admin_or_publisher)],
    response_model=ArtifactResponse,
)
async def create_artifact(
    file: Optional[UploadFile] = None,
    url: Optional[AnyHttpUrl] = None,
) -> Any:
    if not file and not url:
        raise HTTPException(status_code=422, detail="Must upload a file or specify url.")

    if url:
        resp = httpx.get(url)
        file = UploadFile(BytesIO(resp.content), filename=Path(resp.url.path).name)
    assert file is not None

    data = {"file": file}

    return await ArtifactApi.find_or_create(data)

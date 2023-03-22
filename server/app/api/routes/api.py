from fastapi import APIRouter, Depends

from app.api import auth
from app.api.routes import (
    access,
    account,
    artifact,
    distribution,
    orphan,
    package,
    publication,
    release,
    remote,
    repo_version,
    repository,
    task,
)

# get_active_account ensures the request is at least authenticated with an active Account.
# For some routes that's all we care about, but that's the minimum.
router = APIRouter(dependencies=[Depends(auth.get_active_account)])
router.include_router(distribution.router, tags=["distributions"])
router.include_router(remote.router, tags=["remotes"])
router.include_router(package.router, tags=["packages"])
router.include_router(artifact.router, tags=["artifacts"])
router.include_router(repository.router, tags=["repositories"])
router.include_router(
    repo_version.router,
    tags=["repository_versions"],
    dependencies=[Depends(auth.requires_repo_admin)],
)
router.include_router(
    publication.router, tags=["publications"], dependencies=[Depends(auth.requires_repo_admin)]
)
router.include_router(task.router, tags=["tasks"])
router.include_router(
    account.router, tags=["accounts"], dependencies=[Depends(auth.requires_account_admin)]
)
router.include_router(
    access.router, tags=["access"], dependencies=[Depends(auth.requires_account_admin)]
)
router.include_router(
    orphan.router, tags=["orphans"], dependencies=[Depends(auth.requires_package_admin)]
)
router.include_router(release.router, tags=["releases"])

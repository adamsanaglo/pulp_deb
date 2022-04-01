from fastapi import APIRouter

from api.routes import distribution, package, repository, task

router = APIRouter()
router.include_router(distribution.router, tags=["distributions"])
router.include_router(package.router, tags=["packages"])
router.include_router(repository.router, tags=["repositories"])
router.include_router(task.router, tags=["tasks"])

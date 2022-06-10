from fastapi import APIRouter

from api.routes import distribution, orphan, package, publisher, repository, task

router = APIRouter()
router.include_router(distribution.router, tags=["distributions"])
router.include_router(package.router, tags=["packages"])
router.include_router(repository.router, tags=["repositories"])
router.include_router(task.router, tags=["tasks"])
router.include_router(publisher.router, tags=["publishers"])
router.include_router(orphan.router, tags=["orphans"])

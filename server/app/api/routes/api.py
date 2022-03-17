from fastapi import APIRouter

from api.routes import package, repository

router = APIRouter()
router.include_router(repository.router, tags=["repositories"])
router.include_router(package.router, tags=["packages"])

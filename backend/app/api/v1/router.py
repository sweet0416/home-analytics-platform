from fastapi import APIRouter

from app.api.v1 import plugins, system
from app.plugins.fund.interfaces.router import router as fund_router
from app.plugins.lottery.interfaces.router import router as lottery_router
from app.plugins.pve.interfaces.router import router as pve_router

api_router = APIRouter()
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(plugins.router, prefix="/plugins", tags=["plugins"])
api_router.include_router(fund_router, tags=["fund"])
api_router.include_router(lottery_router, prefix="/lottery", tags=["lottery"])
api_router.include_router(pve_router, tags=["pve"])

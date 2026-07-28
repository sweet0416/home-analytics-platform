from fastapi import APIRouter

from app.plugins.fund.domain.constants import FUND_MODULES, FUND_PLUGIN_CODE
from app.plugins.fund.interfaces.schemas import FundStatusRead
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter(prefix="/fund")


@router.get("/status", response_model=ApiResponse[FundStatusRead])
def get_fund_status() -> ApiResponse[FundStatusRead]:
    return ok(
        FundStatusRead(
            plugin=FUND_PLUGIN_CODE,
            display_name="Fund",
            version="0.1.0",
            status="scaffolded",
            description="基金分析插件已接入 HAP 插件体系，等待数据源与数据库模型落地。",
            modules=FUND_MODULES,
            data_source_status="not_configured",
            storage_status="not_created",
            next_step="确认基金数据源、基金主数据表、净值历史表和持仓/观察池模型。",
        )
    )

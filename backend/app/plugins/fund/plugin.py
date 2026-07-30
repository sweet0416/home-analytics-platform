from app.core.plugins.contracts import PluginManifest
from app.plugins.fund.interfaces.router import router
from app.plugins.fund.jobs.scheduler import start_fund_scheduler, stop_fund_scheduler

fund_plugin = PluginManifest(
    name="fund",
    display_name="Fund",
    version="0.2.0",
    description="Fund portfolio, NAV, allocation, risk, automation, and report analytics.",
    routes=[router],
    menu_items=[
        {"name": "fund-overview", "label": "基金分析", "path": "/fund"},
    ],
    startup_hooks=[start_fund_scheduler],
    shutdown_hooks=[stop_fund_scheduler],
)

from app.core.plugins.contracts import PluginManifest
from app.plugins.fund.interfaces.router import router


fund_plugin = PluginManifest(
    name="fund",
    display_name="Fund",
    version="0.1.0",
    description="Fund analytics plugin scaffold for ETF, QDII, allocation, NAV, and reports.",
    routes=[router],
    menu_items=[
        {"name": "fund-overview", "label": "基金分析", "path": "/fund"},
    ],
)

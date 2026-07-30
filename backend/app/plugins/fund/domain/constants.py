FUND_PLUGIN_CODE = "fund"

FUND_MODULES = [
    {
        "code": "watchlist",
        "name": "基金观察池",
        "description": "管理 ETF、QDII 和主动基金的基础档案与关注列表。",
        "status": "completed",
    },
    {
        "code": "nav",
        "name": "净值与走势",
        "description": "同步历史净值、估算收益曲线，并展示阶段涨跌幅。",
        "status": "completed",
    },
    {
        "code": "risk",
        "name": "组合风险",
        "description": "分析波动、回撤、相关性、组合走势和持仓风险贡献。",
        "status": "completed",
    },
    {
        "code": "allocation",
        "name": "资产配置",
        "description": "已支持持仓、账户配置和季度股票披露穿透，后续补充目标 ETF 二级穿透。",
        "status": "in_progress",
    },
    {
        "code": "report",
        "name": "基金日报",
        "description": "已支持数据汇总和 Bark 推送，后续接入 AI 总结。",
        "status": "in_progress",
    },
]

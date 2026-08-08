# 天天基金流水同步

HAP 不保存天天基金登录态。Windows 端使用已登录的 `ttskill` 查询流水，再把列表和详情通过受保护接口发送到 Docker 中的 HAP。

## 首次运行

在 PowerShell 中进入仓库目录，设置同步令牌后运行：

```powershell
$env:HAP_TTSKILL_SYNC_TOKEN = '填写 HAP 设置中的同步令牌'
.\scripts\sync-ttskill-trades.ps1 -PreviewOnly
```

预览会显示新增、更新、跳过和错误。确认无误后运行：

```powershell
.\scripts\sync-ttskill-trades.ps1
```

脚本会再次显示预览，输入 `Y` 才会写入数据库。

## 导入规则

- 只有详情确认状态为 `confirmed` 的交易才进入现金流流水。
- 买入和定投导入为 `buy`，卖出导入为 `sell`，分红导入为 `dividend`。
- 撤单、失败、在途和未知业务只进入预览的跳过/错误结果，不影响现金流收益。
- 使用 `ttfund_skills + tradeId` 幂等，重复同步不会产生重复流水。
- 手动录入流水不受影响。

## 注意

同步令牌只通过环境变量传入，不要提交到 Git，也不要写入脚本或配置文件。

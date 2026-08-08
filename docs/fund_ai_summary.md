# 基金 AI 日报摘要

HAP 默认关闭 AI 摘要。启用后，系统只会发送结构化的基金日报输入，不会自动上传账户密码或其他未进入日报契约的数据。

## OpenAI 兼容 API

在 Portainer 的 HAP Stack 环境变量中配置：

```dotenv
FUND_AI_SUMMARY_ENABLED=true
FUND_AI_SUMMARY_PROVIDER=openai_compatible
FUND_AI_SUMMARY_API_URL=https://api.openai.com/v1/chat/completions
FUND_AI_SUMMARY_API_KEY=替换为你的密钥
FUND_AI_SUMMARY_MODEL=替换为你的模型名
FUND_AI_SUMMARY_TIMEOUT_SECONDS=60
```

`FUND_AI_SUMMARY_API_URL` 必须是完整的 chat completions 地址。任何支持 OpenAI 兼容协议的服务都可以使用同一套配置；API 密钥只放在 Docker 环境变量中，不写入 SQLite、不回显到页面。

## Webhook

保留原有 Webhook 方式：

```dotenv
FUND_AI_SUMMARY_ENABLED=true
FUND_AI_SUMMARY_PROVIDER=webhook
FUND_AI_SUMMARY_WEBHOOK_URL=https://你的服务.example/hap-summary
FUND_AI_SUMMARY_BEARER_TOKEN=可选
```

Webhook 必须返回 JSON：

```json
{"summary":"这里是摘要文本"}
```

## 数据边界

- AI 只整理 HAP 提供的历史事实和统计结果。
- AI 摘要不代表收益预测，也不构成投资建议。
- 生成成功后，摘要会绑定当次日报快照。
- 历史详情不会使用其他日期生成的摘要。

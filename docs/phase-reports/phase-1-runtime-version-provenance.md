# Phase 1: Runtime Version Provenance

## 修改原因

HAP 原先只能展示人工配置的应用版本，无法从运行中的 Backend 或 Frontend 确认其对应的 Git Commit 和构建时间。本阶段补充最小运行版本溯源能力，不改变业务逻辑、数据库结构或部署架构。

## 修改内容

- Backend 健康接口增加 Git SHA、Git Commit、构建时间、镜像标识和部署环境。
- Backend 新增 `/api/v1/system/build-info` 版本信息接口。
- Backend Dockerfile 增加 `GIT_SHA`、`BUILD_TIME` 构建参数、OCI revision/created/source 标签和运行时环境变量。
- Frontend Dockerfile 增加相同构建参数、OCI revision/created/source 标签，并生成 `/build-info.json`。
- Frontend 顶部副标题显示当前 Frontend Commit；Backend 版本仍由健康接口提供。
- Compose 为 Backend、Frontend 和可选 ttskill-agent 传入统一构建参数。
- `.env.example` 增加构建 Commit、构建时间和部署环境配置示例。
- Backend 测试 fixture 改用 pytest 临时目录，避免测试数据库跨运行复用造成 `table already exists`。

## 文件列表

- `backend/Dockerfile`
- `backend/app/api/v1/system.py`
- `backend/app/core/config/settings.py`
- `backend/tests/conftest.py`
- `backend/tests/test_api_contracts.py`
- `frontend/Dockerfile`
- `frontend/src/layouts/TopBar.vue`
- `deploy/ttskill-agent/Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `docs/phase-reports/phase-1-runtime-version-provenance.md`

## 使用方式

部署前设置：

```bash
export HAP_GIT_SHA="$(git rev-parse HEAD)"
export HAP_BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
docker compose build --pull
docker compose up -d
```

验证：

```bash
curl http://127.0.0.1:8088/api/v1/system/build-info
curl http://127.0.0.1:8088/build-info.json
```

两个结果中的 Commit 应与构建时的 `HAP_GIT_SHA` 一致。

## 测试结果

本地验证结果：

- Backend：`pytest -q` 全部通过；测试数据库使用 pytest 临时目录，连续运行不会复用生产或固定测试数据库。仅有既有 Starlette/httpx deprecation warning。
- Frontend：在 `CI=true` 下执行 `vue-tsc --noEmit`，通过。
- Compose：`docker compose config --quiet` 通过，退出码 0；仅有沙箱无法读取 Docker 凭据文件的 warning。
- Docker：使用 `GIT_SHA=f5c05dc513576ad0fbf35f35cb1bc4b95169fea6`、`BUILD_TIME=2026-08-20T00:00:00Z` 构建 Backend、Frontend 和 ttskill-agent，全部成功。
- Docker provenance：Backend、Frontend、ttskill-agent 的 OCI revision/created 标签均已验证；Frontend `/build-info.json` 也已验证包含相同 commit/build time。
- 生产 Portainer 未操作，生产容器未重建，生产数据未修改。

## 已知风险

- 未提供构建参数时，版本字段显示 `unknown`，不会阻止服务启动。
- 当前仍是本地 Compose Build 模式，Git Pull 本身不等于镜像重建。
- 运行中的镜像 Digest 仍需在目标 Docker 主机上通过 `docker inspect` 验证。
- `frontend/pnpm-workspace.yaml` 是工作区原有未跟踪文件，本阶段未修改。
- Frontend 现有 Dockerfile 仍使用 `npm install`，本阶段没有引入 pnpm workspace 或修改依赖流程。
- 当前构建仍可能出现前端依赖审计 warning 和大 bundle warning；它们不影响本阶段 provenance 验证，留待独立性能/依赖阶段处理。

## 后续建议

后续部署验收时记录：Git Commit、镜像 ID、OCI revision、容器启动时间和两个版本接口的返回值，确认它们属于同一次构建。

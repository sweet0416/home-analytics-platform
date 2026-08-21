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
- 生产环境启动时校验构建 SHA 和构建时间；缺失或为 `unknown` 时拒绝启动，开发环境仍允许未知值。
- Compose 为三个构建服务显式注入镜像引用，并将 Backend 的实际引用写入运行时版本信息和 OCI `ref.name` 标签。
- 新增 `scripts/compose-provenance.ps1` 与 `scripts/compose-provenance.sh`，从当前 Git HEAD 自动生成构建参数后调用 Compose。

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
- `scripts/compose-provenance.ps1`
- `scripts/compose-provenance.sh`

## 使用方式

部署前推荐使用包装脚本自动注入当前 Git 版本：

```bash
./scripts/compose-provenance.sh build --pull
./scripts/compose-provenance.sh up -d
```

Windows PowerShell 使用 `./scripts/compose-provenance.ps1 build --pull` 和 `./scripts/compose-provenance.ps1 up -d`。
Portainer 继续使用原有 Stack 部署时，需要在 Stack 环境变量中显式提供 `HAP_GIT_SHA`、`HAP_BUILD_TIME` 和镜像引用；生产环境不会接受未知版本启动。

验证：

```bash
curl http://127.0.0.1:8088/api/v1/system/build-info
curl http://127.0.0.1:8088/build-info.json
```

两个结果中的 Commit 应与构建时的 `HAP_GIT_SHA` 一致。

## 测试结果

本轮最终验证结果：

- Git baseline：`9c9ab33dafd0e9f1ba495f5761d7554f9634053d`。
- Backend：全量 `pytest -q --basetemp=.pytest-tmp-codex-final-20260821` 通过；首次直接运行因 Windows 临时目录权限拒绝失败，未发现业务断言失败。仅有既有 Starlette/httpx deprecation warning。
- Frontend：直接执行 `node_modules/.bin/vue-tsc --noEmit` 通过。
- Compose：`docker compose config --quiet` 通过。
- Diff：`git diff --check` 通过。
- Provenance：生产环境缺失/未知 SHA 或构建时间会被启动校验拒绝；非生产环境允许 `unknown`；契约测试通过。
- Docker：本地完整构建未全部通过，详见下方 `LOCAL_DOCKER_BUILD_VALIDATION`。
- 生产 Portainer 未操作，生产容器未重建，生产数据未修改。

## Phase 1 Review Fix 验证

- Backend：全量 pytest 通过；生产环境未知 SHA/构建时间会被启动校验拒绝，开发环境仍可使用 `unknown`。
- Frontend：`node_modules/.bin/vue-tsc --noEmit` 通过；未修改依赖。
- Compose：`docker compose config --quiet` 通过。
- 镜像引用：Backend、Frontend、ttskill-agent 均支持显式镜像名和 OCI `ref.name`，Backend 运行时 `APP_IMAGE_REFERENCE` 与 Compose 镜像名保持一致。

## LOCAL_DOCKER_BUILD_VALIDATION

- `ttskill-agent`：PASS。基础镜像、Debian 依赖和 ttskill 包下载及镜像导出均完成。
- `backend`：BLOCKED。基础镜像和构建上下文正常，卡在 PyPI 的 Pillow、cryptography 等大 wheel 下载，速度极低。
- `frontend`：BLOCKED。基础镜像元数据正常，卡在 `npm install`，长时间无输出。
- 根因判断：外部依赖下载网络性能异常；此前也出现过 Docker Hub TLS timeout。本轮未发现 Dockerfile、Compose 或 Runtime Provenance 源码错误。
- 处理原则：没有修改 Dockerfile、依赖版本或生产部署配置来规避网络问题。

## 已知风险

- 开发环境未提供构建参数时，版本字段仍显示 `unknown`；生产环境缺少构建 SHA 或时间会在启动阶段失败。
- 当前仍是本地 Compose Build 模式，Git Pull 本身不等于镜像重建。
- 运行中的镜像 Digest 仍需在目标 Docker 主机上通过 `docker inspect` 验证。
- Portainer 不会自动执行仓库内包装脚本；使用 Portainer Stack 时仍需手动设置版本环境变量。
- 本次本地 Docker Build 未获得完整 PASS；阻塞来自外部依赖下载网络性能，不是已确认的源码或 Dockerfile 缺陷。
- `frontend/pnpm-workspace.yaml` 是工作区原有未跟踪文件，本阶段未修改。
- Frontend 现有 Dockerfile 仍使用 `npm install`，本阶段没有引入 pnpm workspace 或修改依赖流程。
- 当前构建仍可能出现前端依赖审计 warning 和大 bundle warning；它们不影响本阶段 provenance 验证，留待独立性能/依赖阶段处理。

## 后续建议

后续部署验收时记录：Git Commit、镜像 ID、OCI revision、容器启动时间和两个版本接口的返回值，确认它们属于同一次构建。

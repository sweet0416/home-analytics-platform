# Changelog

## 1.0.0 - 2026-07-14

### Added

- Modular Home Analytics Platform foundation with backend, frontend, and Docker Compose deployment.
- FastAPI backend with unified API responses, OpenAPI, plugin registry, logging, exception handling, and SQLite persistence.
- Vue 3 dashboard shell with dark theme, responsive layout, Element Plus, Pinia, Vue Router, Axios, and ECharts integration.
- Lottery plugin v1 with DLT rule seed data, current rule API, statistics surface, dashboard cards, and entertainment disclaimer.
- PVE Docker deployment scripts, smoke tests, SQLite backup helper, and performance operations documentation.

### Release Notes

- Initial v1.0 release is a maintainable platform baseline, not a finished lottery prediction product.
- Future modules should be added as plugins without changing the core platform contracts.
- Existing persistent Docker volumes must be backed up before every upgrade.

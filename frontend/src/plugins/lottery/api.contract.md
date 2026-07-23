# Lottery API Contract

Frontend Lottery pages depend on these backend endpoints:

```text
GET /api/v1/lottery/dlt/rules/current
GET /api/v1/lottery/dlt/draws
GET /api/v1/lottery/dlt/draws/coverage
GET /api/v1/lottery/dlt/draws/latest
GET /api/v1/lottery/dlt/statistics/basic
GET /api/v1/lottery/dlt/statistics/omissions
GET /api/v1/lottery/dlt/statistics/randomness
GET /api/v1/lottery/dlt/numbers/{area}/{number}/omission
GET /api/v1/lottery/dlt/analysis/same-period
GET /api/v1/lottery/dlt/analysis/co-occurrence?area&limit&top
GET /api/v1/lottery/dlt/analysis/recommendations?sets&same_period_count&sample_limit&same_period_weight&frequency_weight&missing_weight&structure_weight
GET /api/v1/lottery/dlt/analysis/simulation
POST /api/v1/lottery/dlt/analysis/dantuo
POST /api/v1/lottery/dlt/analysis/backtest
GET /api/v1/lottery/dlt/analysis/replay/context?target_issue_no&sample_limit
POST /api/v1/lottery/dlt/analysis/replay
POST /api/v1/lottery/dlt/analysis/replay/sensitivity
  body: target_issue_no, target_count, sample_windows, weight_profiles, baseline_simulations
POST /api/v1/lottery/dlt/sync
POST /api/v1/lottery/dlt/sync/backfill
POST /api/v1/lottery/dlt/sync/backfill/start
GET /api/v1/lottery/dlt/sync/latest
GET /api/v1/lottery/dlt/sync/status
GET /api/v1/lottery/dlt/sync/runs
GET /api/v1/lottery/dlt/disclaimer
```

All responses must use the shared backend envelope:

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "trace_id": "..."
}
```

The frontend treats missing draw data as a valid empty state, but rule loading failure is treated as
an integration failure.

The heatmap view composes the basic statistics and omission statistics endpoints instead of adding
a dedicated backend endpoint.

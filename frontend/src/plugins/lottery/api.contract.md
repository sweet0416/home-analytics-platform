# Lottery API Contract

Frontend Lottery pages depend on these backend endpoints:

```text
GET /api/v1/lottery/dlt/rules/current
GET /api/v1/lottery/dlt/draws
GET /api/v1/lottery/dlt/draws/coverage
GET /api/v1/lottery/dlt/draws/latest
GET /api/v1/lottery/dlt/data/stages
  response: stages[]
    fields: stage_code, stage_name, rule_code, effective_start_date, effective_end_date, earliest_issue_no, latest_issue_no, earliest_draw_date, latest_draw_date, draw_count, data_source, data_quality_level, description
  response: quality
    fields: level, label, description, sales_present_rate, pool_present_rate, rule_bound_rate
  note: stage report highlights rule/source/field-quality risks and does not affect recommendations or backtest scoring
POST /api/v1/lottery/dlt/data/stages/repair-rule-bindings
  response: repaired_count, rule_code, stage_report
  note: rebinds draws to the configured rule stage by issue range; it does not change draw numbers or source records
GET /api/v1/lottery/dlt/statistics/basic
GET /api/v1/lottery/dlt/statistics/omissions
GET /api/v1/lottery/dlt/statistics/randomness?limit&stage_code
  query: stage_code is optional; when present, diagnostics only use draws in that rule stage
  response: stage_code, stage_name
  response: sample_quality
    fields: level, label, description
  response: front_frequency/back_frequency
    fields: multiple_testing_tests, adjusted_alpha, significant_after_correction
  response: front_frequency/back_frequency.top_deviations[]
    fields: number, count, expected, deviation, confidence_low, confidence_high, z_score
  note: confidence range, z_score and multiple-testing correction are statistical diagnostics only, not prediction signals
GET /api/v1/lottery/dlt/numbers/{area}/{number}/omission
GET /api/v1/lottery/dlt/analysis/same-period
GET /api/v1/lottery/dlt/analysis/co-occurrence?area&limit&top
GET /api/v1/lottery/dlt/analysis/decay?limit&half_life&top&stage_code
  query: stage_code is optional; when present, analysis only uses draws in that rule stage
  response: stage_code, stage_name
  response: front/back
    fields: total_weight, numbers[], rising_numbers[]
  response: front/back.numbers[]
    fields: number, raw_count, weighted_count, weighted_share, raw_rank, weighted_rank, rank_delta
  note: exponential decay weights recent historical draws more heavily; it is a sample diagnostic, not a prediction signal
GET /api/v1/lottery/dlt/analysis/recommendations?sets&same_period_count&sample_limit&same_period_weight&frequency_weight&missing_weight&structure_weight&co_occurrence_weight&coverage_weight
GET /api/v1/lottery/dlt/analysis/simulation
POST /api/v1/lottery/dlt/analysis/coverage
  body: combinations[{front_numbers, back_numbers}]
POST /api/v1/lottery/dlt/analysis/dantuo
POST /api/v1/lottery/dlt/analysis/backtest
GET /api/v1/lottery/dlt/analysis/replay/context?target_issue_no&sample_limit
GET /api/v1/lottery/dlt/analysis/replay/runs?limit
GET /api/v1/lottery/dlt/analysis/replay/runs/{run_id}
POST /api/v1/lottery/dlt/analysis/replay
  body: target_issue_no, sets, sample_limit, same_period_count, baseline_simulations, seed, strategy{same_period_weight, frequency_weight, missing_weight, structure_weight, coverage_weight}
POST /api/v1/lottery/dlt/analysis/replay/sensitivity
  body: target_issue_no, target_count, sample_windows, weight_profiles, baseline_simulations
POST /api/v1/lottery/dlt/analysis/replay/sensitivity/start
GET /api/v1/lottery/dlt/analysis/replay/sensitivity/jobs/{job_id}
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

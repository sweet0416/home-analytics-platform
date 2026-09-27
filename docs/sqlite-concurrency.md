# SQLite concurrency evidence and candidate

Audit baseline: `a7339b26f54988f60f4edb4da0c1953a1b98189f` (PR #9).
Experiments: 2026-09-27, Windows, Python 3.12, SQLAlchemy 2.0.51, SQLite 3.53.1, disposable local files.
This is **not production performance, data-integrity acceptance, or a deployment record**.
No production database, credentials, PRAGMAs, Portainer or volume was accessed.

## Decision

Keep the existing connection configuration: DELETE on newly created databases, FULL synchronous,
5-second connection timeout / 5000 ms busy handler, and existing FK behavior (OFF in this runtime).
Do not force journal mode on an existing file. Do not add a global write mutex or enable WAL.
Instead, finish fund-profile provider reads **before** flushing the first fund update. This removes
a reproduced network-held writer lock while preserving the existing single batch commit and
per-fund provider-failure results. No calculation, schema, API, dependency or restore protocol changes.

This is task option 4: shorten a demonstrated transaction lock window without changing PRAGMAs.
It does not solve every application-level race or promise unlimited SQLite concurrency.

## Connection reality

`backend/app/core/database/session.py` creates a SQLAlchemy engine with `check_same_thread=False`;
file-backed SQLite uses QueuePool in the tested environment. There is no explicit PRAGMA or connect
event hook. `SessionLocal` has `autocommit=False`, `autoflush=False`; individual repositories/services
flush and commit. The request dependency closes, but does not automatically commit, its session.
Independent requests must not share a Session; `check_same_thread=False` does not make Session safe
for concurrent use. Pool defaults are size 5 / overflow 10 / acquisition timeout 30 s, distinct from
the SQLite busy timeout.

The DBAPI connection uses `isolation_level=''` (legacy DEFERRED) and
`autocommit=LEGACY_TRANSACTION_CONTROL` (-1), not a fully autocommit SQL connection. In this mode
a SELECT alone does not establish the same persistent snapshot as an explicit `BEGIN`.
The 5000 ms busy handler comes from Python sqlite3's default `timeout=5.0`, not HAP tuning.
There is no guarantee that a five-second threshold is an exact wall-clock deadline.

Backup uses separate raw sqlite3 connections and the Online Backup API, not filesystem copying of
an actively written database. Restore validation uses read-only connections; restore migrations use
the explicit application-engine connection. Standalone Alembic can construct a NullPool engine.
Bootstrap/create_all and migrations run outside ordinary request admission, before serving traffic;
never run a standalone migration alongside live writers.

Journal mode persists in the database; `foreign_keys`, busy handler and synchronous settings belong
to connections. No new initialization hook is necessary for the selected unchanged configuration.

## Writer inventory

22 logical writer families below, not 22 threads/endpoints. H = HTTP maintenance lease, including
background tasks and machine-token requests; J = guarded scheduler; R = exclusive restore.
Every H/J family can overlap other ordinary H/J writers; restore waits for those leases to drain.
Repository/direct script calls themselves are not guarded. Frequencies are source defaults, not
current production observations. Sources are repository-relative.

| Family | Transaction scope / source | Trigger and overlap | Guard |
|---|---|---|---|
| Fund master/profile | `fund/.../repositories.py:upsert_fund`; profile batch commit | CRUD, profile/NAV/disclosure sync, imports; shared fund row | H/J |
| Positions | `FundService.create/update/delete_position`; commit per action; NAV propagation shares row | User operations and NAV updates | H/J |
| Watchlist | `FundService.create/update/delete_watchlist_item`; per action | User operations and fund sync | H |
| Transactions | `create_transaction`, trade import batch, delete | User and machine imports; preview read-only | H |
| NAV | `create_nav_record`, `_persist_latest_nav`, `_persist_nav_history`; commit per fund | Manual/import and fund scheduler, default weekday 19:00–22:00 hourly | H/J |
| Account snapshots | `create_account_snapshot`; parent/children together | Machine holdings import | H |
| Target links | `upsert_target_link`, disable; per action | User-persisted configuration-like data | H |
| Disclosures | `upsert_disclosure`; replace children, commit per fund | Manual holding sync | H |
| Report snapshots | `save_daily_report_snapshot`; date-keyed upsert + commit | Manual, AI, scheduled and machine sync-complete | H/J |
| AI archives | `save_daily_ai_summary`; separate archive commit | Manual and automated summaries | H/J |
| AI automation | `claim_ai_automation_run`; unique savepoint then outer commit; later states separate | Scheduled/machine completion; manual push | H/J |
| Fund sync history | `fund/jobs/scheduler.py:_save_run`; separate commit including skipped runs | Fund scheduler | J |
| Lottery seeds | `LotteryRepository.ensure_dlt_seed_data`; one commit | Each plugin startup; exclude simultaneous external writers | Startup |
| Lottery draws/sync runs | `LotteryService.sync_draws`; claim commit, fetch, batch/final commit; failure rollback then failure record | Manual/background/backfill and daily 22:30 scheduler | H/J |
| Lottery stage repair | `repair_data_stage_bindings`; batch commit | Manual request versus sync | H |
| Saved combinations | `save_combination`, `update_saved_combination`, `delete_saved_combination`; per action | Concurrent user requests | H |
| Replay | `LotteryReplayService`; parent/children commit after analysis | Manual request | H |
| Random-ticket save | `analyze_random_ticket_sample` → `create_random_ticket_run`; flush but no commit found | `save=true`; existing persistence caveat below | H |
| Notification history | `NotificationService._record_delivery_runs`; fresh session/batch commit, rollback on failure | User, fund/lottery, infrastructure checks (default every 5 min when enabled) | H/J |
| Backup files/history | Online Backup API, then separate `DatabaseBackupRunRepository` commit | User, daily 03:10 job, restore safety copy | H/J/R |
| Restore/history | Replace, migrate, validate, then `DatabaseRestoreRunRepository` commit | Explicit restore only | R |
| Schema/migrations | `create_database_schema`, `run_database_migrations`; DDL/version/data migration | Startup, offline CLI, restore | Startup/R |

Fund/lottery repository paths are under `backend/app/plugins/<plugin>/infrastructure/persistence/`;
services under `application/`; backup/notification/database under `backend/app/core/`.
Auth sessions and login counters are memory-only. Settings read environment/dotenv, not SQLite.
Docker/PVE health has no direct database write; notification history is its writing side effect.
Machine routes write fund/NAV/positions, account snapshots, trades and conditional summary/push
state. Machine authentication bypasses browser sessions, **not** restore maintenance admission.

## Experiments and limits

The same test matrix runs against fresh DELETE and WAL databases. Real ORM/repository writes,
an actual authenticated NAV HTTP request, guarded fund scheduled-history and lottery sync paths,
notification-history inserts and the real backup service are exercised. External lottery fetch is
an empty synthetic page; fund's already-completed-day scheduler branch writes real history without
network calls. Provider performance, large production datasets and physical power loss are not tested.

Representative observations (seconds; repeated runs vary, not a statistical benchmark):

| Workload | DELETE | WAL |
|---|---|---|
| 32 independent writes, eight threads, maximum operation time | 0.308–0.407, no lock errors | 0.190–2.395, no lock errors |
| Same burst, experimental reentrant mutex | 0.061–0.097 max | 0.037–0.038 max |
| Writer held 0.25 s | Commits after ~0.27 | Commits after ~0.27; one run ~0.77 |
| Writer near threshold, nominal 4.8 s | Success ~4.9; an earlier run timed out ~5.7 | Success ~4.9 in observed runs |
| Lock held until contender times out, at least 7.5 s | Fails ~5.5, explicit rollback | Fails ~5.5, explicit rollback |
| Four readers + backup during uncommitted write | Readers see committed row; backup excludes pending row | Same correctness |
| Explicit long read transaction | Writer commit waits for reader (~0.26) | Commit completes with reader open (~0.002) |
| HTTP + two scheduler/history writers + notification history | All four durable results; ~0.117 max | All four durable results; ~0.047 max |
| Profile fetch after first update, **before fix** | Concurrent write times out 5.514 | Concurrent write times out 5.525 |
| Same profile fetch, **after fix** | Concurrent write commits 0.008–0.014 | Commits 0.014–0.018 |

The first 26-case baseline passed. The subsequently added real profile contention regression failed
in both modes on unmodified application code, then passed after the small ordering fix.
This is a reproduced **isolated risk**, not evidence of a production `database is locked` incident.
The near-limit case deliberately records both possible outcomes; definite timeout keeps the blocker
until failure is observed. Assertions check durable row counts, no partial failed insert, session
rollback/reuse and quick_check, rather than claiming a fragile millisecond SLA.

WAL improves explicit read-snapshot/write overlap, but does not cure the demonstrated writer/writer
failure. Burst timing also contains a WAL outlier, so no universal throughput superiority is claimed.
An experimental RLock reduces contention in a tiny burst, but would require all business reads and
writes to enter in a consistent order, not merely locking commit/flush. It can shift busy errors into
unbounded queues, retain slow provider work and complicate restore draining. Nested RLock passes
in this bounded experiment; it is not a proof of a general coordinator's deadlock freedom. Not selected.

WAL/SHM files were observed; an explicit PASSIVE checkpoint after readers ended returned busy=0 and
all frames checkpointed. Abrupt child-process exit left a DELETE journal or WAL/SHM, preserved the
preceding commit, discarded the uncommitted update on reopen, and passed quick_check. No sidecar was
manually deleted. These checks are not a power-loss simulation or production restart rehearsal.

## Foreign keys: demonstrated gap, separate activation decision

The fresh physical schema and ORM metadata both have 13 FK constraints, affecting
`fund_watchlist_items`, `fund_nav_records`, `fund_positions`, `fund_transactions`, `fund_disclosures`,
`fund_disclosure_holdings`, `fund_account_holding_snapshots`, `fund_daily_ai_summaries`,
`fund_ai_automation_runs`, `lottery_prize_tiers`, `lottery_draws`, `lottery_draw_prize_results`,
and `lottery_replay_generated_sets`.

With FK OFF, both ORM and raw SQL can insert an orphan NAV row. `foreign_key_check` reports it;
quick_check is not referential-integrity validation. FK ON rejects both paths. On the baseline code,
an experiment enabling FK for every SQLAlchemy SQLite connection passed all 290 original backend
tests (including existing migration/restore tests). Raw backup handles were unchanged; this is not
proof of a complete production FK rollout or every historical schema/data combination.

No inspected forward migration intentionally requires FK OFF. However, legacy create_all/stamp
does not retrofit missing physical constraints; existing production or old backup violations are
unknown. PR #9 currently validates structure/quick_check, not `foreign_key_check`. For this narrowly
targeted lock-window fix, keep FK unchanged. A separate enforcement candidate must connect all
relevant engines consistently, validate restored/safety databases and rollback behavior for orphan
data, and gate deployment on the preflight below. Never automatically repair/delete orphan rows.

## Restore compatibility and outstanding application risks

PR #9 is unchanged: one worker, in-process writers only, maintenance blocks new requests/jobs,
drains admitted work, and rejects WAL mode or any WAL/SHM/journal at restore source/target.
Normal backup during an uncommitted write produces a consistent committed snapshot in the tests;
this does not mean the WAL backup can pass the current restore gate. Enabling WAL would require
a separate fully tested checkpoint/restore protocol. That complexity is not justified here.

Source audit also found independent follow-ups, **not fixed by this candidate**: random-ticket
`save=true` flushes without a commit; lottery running-sync admission is check-then-insert; several
upserts can race on unique keys; stale updates have no version predicate; notification send/history
are not one atomic operation. The random-ticket observation was confirmed by source inspection,
not a new end-to-end runtime reproduction. No claim is made that all business races are eliminated.

## Reproduce safely

Use Python 3.12+ with `backend/requirements-dev.txt` installed in the chosen virtual environment.
From a clean checkout, with that environment active:

```powershell
python backend/scripts/check_sqlite_concurrency.py
python backend/scripts/check_sqlite_concurrency.py --full
python backend/scripts/check_sqlite_concurrency.py --fk-experiment
python -m ruff check backend/app backend/scripts backend/tests
python -m compileall -q backend/app backend/scripts backend/tests
git diff --check
```

The launcher strips case-insensitive Settings keys, replaces database/scheduler settings, changes
to a newly created temporary directory (no caller dotenv), and runs pytest in a child process.
Inherited pytest options/plugins and Python optimization controls cannot skip the intended checks;
there is no CLI child-mode bypass. The four launcher regressions cover those isolation boundaries.
No real DB path is accepted. `--fk-experiment` uses a test-process-only connection listener and
excludes the matrix whose purpose is to assert the unchanged FK-OFF baseline. `SQLITE_EVIDENCE`
lines contain only synthetic case names, counts, versions and timings. Docker is not required.

Local candidate validation: 326 backend tests passed (36 new cases); restore + migration subset
36 passed; fund scheduler subset 6 passed; Ruff, compileall and diff whitespace checks passed.
The separate baseline FK-ON experiment passed 290 original tests. Existing Starlette/Alembic
deprecation warnings remain. No container startup or production runtime acceptance is claimed;
the changed service remains covered by the existing Dockerfile `COPY app ./app`.

## Future production preflight (design only; not executed)

Use a separately authorized read-only connection to the verified live DB path, with `mode=ro`
(not `immutable=1` against a live file). If sidecars/hot-journal state would require recovery, stop;
do not force open, checkpoint or remove files. Record only aggregate diagnostics:

```sql
SELECT sqlite_version();
PRAGMA journal_mode;
PRAGMA quick_check;
SELECT count(*) AS fk_violations FROM pragma_foreign_key_check;
```

Also inventory actual `pragma_foreign_key_list` for all application tables against the 13 declared
edges, check single backend worker and absence of external SQLite writers, and check backup/recovery
readiness. A new read-only sqlite3 connection's busy_timeout/FK/synchronous values do **not** prove
the running SQLAlchemy connection values; inspect them via a separately authorized application
connection if needed. No production PRAGMA assignment is part of this plan.

This candidate does not require an FK enablement gate because it does not enable FK. Any future
enforcement rollout **must stop** if FK violations or missing expected constraints are found.
Any future WAL proposal also needs verified local-filesystem/volume suitability and restore
compatibility. No automatic rollout, restart, orphan cleanup or mode switch is authorized here.

References: [Python sqlite3 timeout/transaction control](https://docs.python.org/3.12/library/sqlite3.html),
[SQLite PRAGMAs](https://www.sqlite.org/pragma.html), [WAL concurrency](https://www.sqlite.org/wal.html).

# NOVAA — Financial Analytics Workspace

> **Your money, in full resolution.**  
> Net-worth Observability via Verified Account Aggregation.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)

---

## What is NOVAA?

NOVAA turns your bank transactions into a monthly close: where the money came
from, what was committed before the month started, what was genuinely
discretionary, and how long the balance lasts at the current rate.

Transactions arrive from two sources behind a single ingestion interface:

- **Bank statement upload** — PDF, CSV or XLS from HDFC, ICICI, SBI, Axis or
  Kotak, with a generic fallback for anything else. Works today.
- **RBI Account Aggregator** (Setu) — activates on licence, no rewrite needed.

Both collapse into the same deduplicated transaction table, so a statement you
upload today and the same transaction arriving later from AA become one row.

## Why the analysis is different

- **Self-transfers are detected and excluded.** Moving ₹25,000 between your own
  accounts is not ₹25,000 of spending. This is the single biggest source of
  wrong numbers in a multi-account tracker.
- **Merchants are extracted properly.** `UPI/512345678901/swiggy@icici/Payment`
  resolves to Swiggy, not to `UPI`. IFSC codes, UTRs and masked card numbers are
  stripped before matching.
- **Anomalies use median and MAD per merchant**, so rent and EMI are not flagged
  every month simply for being large.
- **Recurring detection measures intervals**, requires three occurrences and a
  stable amount, and predicts the next due date.
- **Forecasts start from committed recurring flows**, not a flat average of the
  last three months.

## Quick start

### With Docker (Postgres and Redis included)

```bash
cp backend/.env.example .env
docker compose up
```

The API is on `http://localhost:8001`, migrations run before it starts, and the
background worker comes up alongside it.

### Locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head          # migrations are the only schema path
uvicorn app.main:app --reload --port 8001
```

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

Redis is optional in development: without it, rate limiting falls back to
per-process memory and statement parsing runs inline instead of on the worker.

### Background worker

```bash
cd backend
arq app.workers.settings.WorkerSettings
```

It handles statement parsing, the twice-daily AA refresh, nightly enrichment,
and the retention purge.

Run the worker whenever Redis is running. The API only falls back to inline
parsing when there is no queue at all, so Redis up with no worker leaves every
statement upload sitting at `pending`.

## Architecture

```
Statement upload (PDF/CSV/XLS) ─┐
                                ├─▶ Normalizer ─▶ Idempotent upsert (txn_hash)
Setu AA adapter ────────────────┘                          │
                                                           ▼
                            Enrichment (merchants, transfers, recurring)
                                                           │
                                                           ▼
                                 Monthly close engine ─▶ /api/v1
```

| Layer | Package |
| --- | --- |
| Ingestion sources and dedupe | `backend/app/ingestion/` |
| Bank statement parsers | `backend/app/ingestion/parsers/` |
| Merchants, transfers, recurring | `backend/app/enrichment/` |
| Monthly close, anomalies, forecast | `backend/app/analytics/` |
| Background jobs and cron | `backend/app/workers/` |

## Security

- PII encrypted at rest with AES-256-GCM; emails are looked up by an indexed
  SHA-256 hash so login stays O(1) without decrypting anything.
- Refresh tokens rotate, and replaying a revoked token revokes the whole family.
- Every query is scoped by `user_id`, not by a resource identifier alone.
- Logs are scrubbed of tokens, secrets, OTPs, account numbers and emails.
- The application **refuses to start in production** with a placeholder
  `JWT_SECRET`, a missing `ENCRYPTION_KEY`, demo routes enabled, or SQLite.

## Tests

```bash
cd backend
pytest -q          # 151 tests
ruff check .
mypy app
```

Coverage includes every statement parser against fixture files, deduplication,
tenant isolation on the consent endpoints, the enrichment pipeline, and the
analytics math.

## Account Aggregator status

AA production access requires an RBI/SEBI/IRDAI/PFRDA licence; the Setu sandbox
returns dummy data only. The architecture treats AA as one adapter rather than
the foundation, so statement upload delivers real data now. See
[docs/aa-go-live.md](docs/aa-go-live.md) for the licence routes, the Setu Bridge
checklist, and the DPDP Act 2023 posture.

## License

MIT © 2026 NOVAA

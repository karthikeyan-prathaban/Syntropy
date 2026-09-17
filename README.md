# NOVAA — Financial Analytics Workspace

> **Your money, in full resolution.**  
> Net-worth Observability via Verified Account Aggregation — built on India's RBI Account Aggregator framework.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)

---

## What is NOVAA?

NOVAA is a **premium financial analytics workspace** that connects to Indian bank accounts via the [RBI Account Aggregator framework](https://sahamati.org.in) (Setu AA). It turns consented bank data into actionable analytics, AI insights, and natural-language recall.

- **Consent-first** — zero SMS scraping, zero email reading
- **Analytical workspace** — cashflow, spending, runway, anomalies
- **AI Recall** — ask your finances anything in plain English
- **RBI AA compliant** — cryptographically signed data via Setu

---

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  NOVAA Web   │────▶│  FastAPI /api/v1 │────▶│  Setu AA Gateway │
│ React + Vite │     │  Async SQLAlchemy│     │  40+ Indian Banks│
└──────────────┘     └─────────────────┘     └──────────────────┘
```

---

## License

MIT © 2026 NOVAA

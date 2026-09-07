# Syntropy — Open Finance Dashboard

> **AI-powered personal finance. Built on India's Account Aggregator framework.**

[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)

---

## What is Syntropy?

Syntropy is a **consent-based personal finance SaaS** platform that connects to your Indian bank accounts via the [RBI Account Aggregator framework](https://sahamati.org.in) (Setu AA) and gives you:

- 📊 **Live spend analytics** — category breakdowns, monthly trends, cashflow
- 🤖 **AI-powered advisor** — personalized money-saving recommendations (Gemini AI)
- 🔐 **Privacy-first** — no credentials stored, consent-based data only
- ⚡ **Financial Health Score** — your money at a glance

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Syntropy Platform                │
├─────────────┬──────────────┬───────────────────────┤
│  React SPA  │  FastAPI API │   Setu AA Gateway     │
│  Vite + TS  │  Python 3.13 │   126+ Indian Banks   │
│  port:5173  │  port:8001   │   sandbox/production  │
└─────────────┴──────────────┴───────────────────────┘
```

---

## Quick Start

### 1. Clone & Setup Backend
```bash
git clone https://github.com/karthikeyan-ui/Syntropy.git
cd Syntropy/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your Setu credentials
uvicorn app.main:app --reload --port 8001
```

### 2. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## Environment Variables

```env
SETU_CLIENT_ID=your_client_id
SETU_CLIENT_SECRET=your_client_secret
SETU_ORG_ID=your_org_id
SETU_PRODUCT_INSTANCE_ID=your_product_instance_id
SETU_FIU_BASE_URL=https://fiu-sandbox.setu.co
JWT_SECRET=your-secret-key-min-32-chars
DATABASE_URL=sqlite:///./syntropy.db
GEMINI_API_KEY=optional_for_ai_advice
REDIRECT_URL=https://yourdomain.com/consent/callback
CORS_ORIGINS=https://yourdomain.com,http://localhost:5173
```

---

## Features

| Feature | Status |
|---------|--------|
| JWT Auth (signup/login) | ✅ |
| Setu AA Consent Flow | ✅ |
| Transaction Categorization | ✅ |
| Spend Analytics Dashboard | ✅ |
| AI Financial Advisor | ✅ (Gemini) |
| Financial Health Score | ✅ |
| 6-month Trend Charts | ✅ |
| Transaction Search/Filter | ✅ |
| PostgreSQL support | ✅ |
| Render.com Deploy Config | ✅ |

---

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

The `render.yaml` at root configures everything automatically:
- FastAPI backend (Python)
- React static site
- PostgreSQL managed database

---

## Tech Stack

**Backend:** FastAPI · SQLAlchemy · Pydantic · JWT · bcrypt · httpx · Google Gemini AI

**Frontend:** React 18 · TypeScript · Vite · Recharts · Axios · React Router

**Infrastructure:** Render.com · PostgreSQL · Setu AA Framework

---

## Setu Account Aggregator Integration

Syntropy uses [Setu's FIU APIs](https://docs.setu.co/data/account-aggregator/overview) to:

1. Create consent requests for users
2. Redirect to Setu's AA consent interface
3. Fetch Financial Information (FI) via sessions
4. Parse and store transaction data from 126+ banks

Supported data types: `DEPOSIT` accounts (savings, current, FD)

---

## Contributing

PRs welcome. Please open an issue first to discuss what you'd like to change.

---

## License

MIT © 2026 Syntropy / Karthikeyan Prathaban

---

*Built with ❤️ in Chennai, India — on the idea that every Indian deserves to understand their money.*

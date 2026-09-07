# Syntropy — Open Finance Platform

> **AI-powered personal finance intelligence. Built on India's RBI Account Aggregator framework.**
> **Zero SMS scraping. Zero email reading. Real-time cross-bank intelligence.**

[![Live Production](https://img.shields.io/badge/Production-Live-emerald.svg)](https://syntropy-k5fj.onrender.com)
[![API Status](https://img.shields.io/badge/API-v2.0.0--Active-cyan.svg)](https://syntropy-api.onrender.com/api/health)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)

---

## 🌐 Live Deployments

- **Web Application & Interactive Landing Page:** [https://syntropy-k5fj.onrender.com](https://syntropy-k5fj.onrender.com)
- **Production API:** [https://syntropy-api.onrender.com](https://syntropy-api.onrender.com)
- **API Health Check:** [https://syntropy-api.onrender.com/api/health](https://syntropy-api.onrender.com/api/health)
- **Setu Webhook Endpoint:** `https://syntropy-api.onrender.com/api/webhooks/setu`

---

## What is Syntropy?

Syntropy is a **consent-based financial intelligence platform** that connects to Indian bank accounts, fixed deposits, and mutual funds via the [RBI Account Aggregator framework](https://sahamati.org.in) (Setu AA).

### Why Syntropy vs Legacy PFM Apps?
- 🚫 **Zero SMS Scraping:** No reading personal SMS, OTPs, or messages.
- 🚫 **Zero Email Reading:** No Google OAuth inbox access.
- 🔐 **Cryptographically Signed:** Data delivered via 256-bit encrypted bank pipes.
- ⚡ **Interactive Terminal:** Live simulation of cross-bank cashflows in browser.
- 📄 **Bank Statement Normalizer:** Converts cryptic raw UPI strings (`UPI/4291039401/...`) into clean merchant names with 1-click tax CSV/PDF exports.
- 🤖 **Autonomous AI Co-Pilot:** Actionable recommendations powered by Gemini AI.
- 📈 **Growth & Marketing Engine:** Built-in UTM attribution, anonymous profiling, and viral waitlist ranking.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Syntropy Open Finance                         │
├─────────────────────┬──────────────────────────┬───────────────────────┤
│    Frontend SPA     │       FastAPI API        │    Setu AA Gateway    │
│ React 18 + TS + Vite│  Python 3.11 + Uvicorn   │   40+ Indian Banks    │
│  syntropy-k5fj      │       syntropy-api       │  OneMoney / Anumati   │
└─────────────────────┴──────────────────────────┴───────────────────────┘
```

---

## Quick Start

### 1. Setup Backend
```bash
git clone https://github.com/karthikeyan-ui/Syntropy.git
cd Syntropy/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001
```

### 2. Setup Frontend
```bash
cd Syntropy/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## Setu Account Aggregator Integration & Bridge Mapping

To connect Syntropy to your Setu AA instance:

1. In [Setu Bridge](https://bridge.setu.co), navigate to **Account Aggregator → Settings**.
2. **Whitelist Callback / Redirect URL:**
   ```text
   https://syntropy-k5fj.onrender.com/consent/callback
   ```
3. **Configure Webhook Endpoint:**
   ```text
   https://syntropy-api.onrender.com/api/webhooks/setu
   ```
4. **Environment Variables:**
   ```env
   SETU_CLIENT_ID=your_client_id
   SETU_CLIENT_SECRET=your_client_secret
   SETU_ORG_ID=8890f2ec-f6af-4180-8062-e05f5ae0eb73
   SETU_PRODUCT_INSTANCE_ID=796f9c0e-e9d7-437c-8148-9423228909b7
   SETU_FIU_BASE_URL=https://fiu-sandbox.setu.co   # or https://fiu.setu.co
   FRONTEND_URL=https://syntropy-k5fj.onrender.com
   REDIRECT_URL=https://syntropy-k5fj.onrender.com/consent/callback
   CORS_ORIGINS=https://syntropy-k5fj.onrender.com,https://syntropy.onrender.com,http://localhost:5173
   ```

---

## License

MIT © 2026 Syntropy / Karthikeyan Prathaban

*Built with ❤️ in Chennai, India — on the idea that every Indian deserves to understand their money with complete privacy.*


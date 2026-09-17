# Working Capital Control Tower — App Summary

## What it is

**Working Capital Control Tower** is a merged finance demo that unifies three products into one application for working capital / cash management:

| Product | Role |
|---------|------|
| **Cash Calendar** (spine) | Dated AR inflows vs AP obligated/pipeline/held outflows + WC ratios (DSO/DPO/CCC), cash alerts, ranked actions |
| **AR Sensei** | Receivables analytics: aging, partner risk, forecast, chatbot |
| **AP Document Intelligence** | Invoice intake, OCR, matching, exceptions, role-based approvals |

Domain focus: balancing customer collections (AR) against vendor payments (AP), with scenario planning (payment delays, recession, defer AP).

Original source apps (`cashflow-web`, `cashflow-api`, Archive AP) are left untouched outside this merge.

---

## Product surfaces

| Path | Screen | Purpose |
|------|--------|---------|
| `/login` | Demo login | Shared auth entry |
| `/` | **Cash Calendar** | Product home — cash events, KPIs, DSO/DPO/CCC, alerts, ranked actions |
| `/hub` | Module picker (`Home.jsx`) | Optional launcher for Calendar / AR / AP |
| `/ar/dashboard` | AR CFO dashboard | Aggregate AR exposure |
| `/ar/partners` | Partner aging list | Partner-level aging summaries |
| `/ar/partners/:code/details` | Partner deep-dive | Risk detail for one partner |
| `/ar/insights` | Risk insights | LLM-backed partner insights |
| `/ar/invoices` | AR invoices | Invoice list + history |
| `/ar/forecast` | Cashflow forecast | Forecast + what-if scenarios |
| `/ar/pipeline` | Data pipeline | CSV upload + AR settings |
| `/ar/chatbot` | AI assistant | NL queries over AR data |
| `/ap/*` | AP Control Tower | Intake, match, exceptions, approvals |
| `/liquidity` | Redirect | Redirects to `/` (Cash Calendar) |

### AP internal views

- Control Tower dashboard
- Document Intake
- Invoice Approval (workflow, exceptions)
- Regulations
- PO / Contracts records

Legacy AR paths (`/dashboard`, `/partners`, …) redirect into `/ar/*`.  
Note: `frontend/src/pages/NetLiquidity.jsx` still exists but is **not routed** (orphaned; `/liquidity` redirects to Cash Calendar).

---

## Cash Calendar intelligence

| Capability | What it shows |
|------------|---------------|
| **DSO / DPO / CCC** | Rolling working-capital ratios (`DIO` N/A without inventory; `CCC = DSO − DPO`) |
| **Cash alerts** | Negative net days, elevated AR risk, aged holds, outflow clusters, CCC deterioration, scenario stress |
| **Ranked actions** | Hold pay / prioritize collect / review holds ordered by cash-impact score (amount × timing × certainty) |

Implemented in:

- `backend/wc/metrics.py` — DSO / DPO / CCC (+ prior period + drivers)
- `backend/wc/alerts.py` — alert generation
- `backend/wc/alert_config.py` — env-tunable thresholds
- `backend/wc/action_ranking.py` — ranked suggested actions
- `frontend/src/pages/CashCalendar.jsx` — ratio tiles, alerts panel, suggested actions

**Alert IDs:** `NEG_NET_DAY`, `NET_WC_NEGATIVE`, `CASH_AT_RISK`, `HOLD_AGING`, `LARGE_OUTFLOW_CLUSTER`, `CCC_DETERIORATION`, `SCENARIO_STRESS`

**Action types:** `hold`, `collect`, `review_holds`

Alert thresholds (env): `WC_ALERT_CASH_AT_RISK`, `WC_ALERT_HOLD_AGING_DAYS`, `WC_ALERT_CLUSTER_DAYS`, `WC_ALERT_CLUSTER_RATIO`, `WC_ALERT_CCC_DAYS`, `WC_ALERT_SCENARIO_DROP`.

---

## Tech stack

| Layer | Stack |
|-------|--------|
| **Frontend** | React 19, CRA + CRACO, React Router 7, Tailwind, Radix UI, Recharts, Axios, react-hook-form, Zod, Yarn (`finance-control-tower-web`) |
| **Backend** | FastAPI + Uvicorn, Pydantic v2, python-dotenv, httpx, python-multipart, pytest |
| **AR data** | DuckDB (`backend/payment_allocation.duckdb`), pandas, openpyxl |
| **AP data** | In-memory Python dicts (`ap/store.py`) — no real DB |
| **OCR** | Pillow, pytesseract, PyMuPDF |
| **LLM (optional)** | Ollama (default), OpenAI, Gemini |
| **Infra** | Local demo — no Dockerfile / docker-compose / CI configs in-repo |

Also used on the frontend: `sonner`, `lucide-react`, `xlsx`, `file-saver`, `jspdf`, `html2canvas`, `react-markdown`.

- Frontend port: **3000**
- Backend port: **8000**

---

## Project structure

```text
working-capital-control-tower/
  README.md
  docs/
    APP_SUMMARY.md          # this file
  frontend/                 # CRA React app (port 3000)
    src/
      App.js                # Top-level routes
      config.js             # AR/AP/WC API bases
      auth/AuthContext.jsx  # Shared login (AP auth API)
      pages/                # Cash Calendar, AR screens, Login, Hub (Home.jsx)
      ap/                   # Embedded AP Control Tower UI
      components/           # Layout, ModuleSwitcher, shadcn-style UI
    public/
    plugins/                # visual-edits, health-check (CRA plugins)
  backend/                  # FastAPI (port 8000)
    main.py                 # Single entrypoint mounting AR/AP/WC
    ar/                     # AR Sensei → /api/ar/*
      endpoints/routes.py
      services/             # forecast, chatbot, LLM, pipeline
      repositories/
      models/
      db/                   # DuckDB migrations + seed
    ap/                     # AP Document Intelligence → /api/ap/*
      routers/              # auth, documents, invoices, POs, contracts, etc.
      services/             # OCR, document_intelligence, approval, feed
      store.py              # In-memory demo data + users
      demo_dataset.py
    wc/                     # Working Capital spine → /api/wc/*
      router.py
      calendar_service.py
      cash_events.py
      store.py              # COLLECT_PRIORITIES (in-memory)
      metrics.py            # DSO / DPO / CCC
      alerts.py             # Cash alerts
      alert_config.py       # Alert threshold env config
      action_ranking.py     # Ranked suggested actions
    samples/                # Sample txt invoices/POs/contracts for OCR demos
    data/app.log
    tests/
      test_wc_intelligence.py
      integration/
```

---

## Architecture

```text
Login (AP demo auth)
    → Cash Calendar (/)  ←── GET /api/wc/calendar (AR DuckDB forecast + AP memory
                            + metrics + alerts + ranked actions)
    → AR Sensei (/ar/*)  ←── /api/ar/*
    → AP Tower (/ap/*)   ←── /api/ap/*
         holds / planned pay / collect priority update WC calendar
```

### Patterns

- **Modular monolith**: one FastAPI app mounts three namespaces (`ar`, `ap`, `wc`) from `backend/main.py`.
- **Dual persistence**: DuckDB (AR) vs in-memory dicts (AP / WC actions).
- **WC as composition layer**: `calendar_service` pulls AR forecast + AP invoices into one calendar, then attaches `wc_metrics`, `alerts`, and ranked `actions_suggested`.
- **Repository + service** layering in AR; **router → service → store** in AP.
- **Migration runner** with file lock for DuckDB init.
- **Role-based approval state machine** for AP.
- **Frontend**: shared auth shell; AR uses React Router layout; AP uses internal view state under `/ap/*`.
- **UI kit**: Tailwind + Radix (shadcn-style) under `frontend/src/components/ui/`.
- **Feature flags**: AR settings (e.g. CFO dashboard) via `/api/ar/settings`.

### Startup behavior (`main.py`)

- Applies AP demo dataset via `apply_demo_dataset()`
- Enrichment for WC demo (e.g. forces selected invoices Payment Ready / planned pay dates)
- Root `GET /` returns service map: `{service, status, docs, ar, ap, wc}`

---

## Main features

### Cash Calendar

- Horizon: **7 / 30 / 90** days
- UI scenarios: `baseline`, `payment_delay_7`, `payment_delay_14`, `recession`, `defer_ap_7`, `defer_ap_14`
  - Scenario aliases on API: `ar_delay_7|14|30` → `payment_delay_*`; `defer_ap_7|14` → baseline + `defer_ap_days`
  - AR forecast API also supports `growth`, `payment_delay_30`, and other what-ifs not exposed in the Calendar UI
- **DSO / DPO / CCC** ratio tiles (rolling period; DIO N/A)
- **Cash alerts** panel
- **Ranked suggested actions** (hold / collect / review holds)
- Actions: **Hold pay**, **Prioritize collect**, set planned pay date
- Charts: inflows vs obligated / pipeline / held outflows
- KPIs: inflows, obligated/pipeline outflows, held, net, cash at risk, nested `wc_metrics`

### AR Sensei

- CFO dashboard and partner aging
- Partner deep-dive and risk insights (LLM-backed)
- Invoice list + payment audit trail
- Cashflow forecast with what-if scenarios
- CSV upload pipeline into DuckDB
- Natural-language chatbot over AR data

### AP Document Intelligence

- Document intake + OCR / AI extract
- Invoice–PO–contract matching
- Exception handling
- Role-based approval: AP Analyst → Finance Manager → Tax Reviewer → Controller
- Regulations, PO/contract records, demo reset

---

## API overview

Base: `http://localhost:8000` — OpenAPI at `/docs`. Health: `/api/health`.

### Working Capital — `/api/wc`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/calendar` | Cash events + KPIs (incl. `wc_metrics`) + series + `alerts` + ranked `actions_suggested` |
| GET | `/metrics` | DSO / DPO / CCC for a rolling period (+ prior + drivers) |
| GET | `/alerts` | Cash alerts for the current calendar snapshot |
| POST | `/ap/{invoice_id}/hold` | Set/clear `cashHold` (body: `{hold, note?}`) |
| PATCH | `/ap/{invoice_id}/planned-pay-date` | Set planned pay date (body: `{plannedPayDate}`) |
| POST | `/collect-priority` | Flag AR collect priority |
| GET | `/collect-priority` | List active collect priorities |

**Calendar query params:** `days` (1–365, default 30), `scenario`, `defer_ap_days` (0–90), `period_days` (7–365, default 90 for WC ratios).

**Calendar payload highlights:** `kpis.wc_metrics`, `alerts[]`, `actions_suggested[]` (with cash-impact scores/labels), `ar_forecast_meta`, `defer_ap_days`, `as_of`.

**Alerts query:** same scenario params as calendar; returns `{as_of, horizon_days, scenario, alerts}`.

Note: `/api/health` `modules.wc` may still list only legacy WC actions (`calendar`, `hold`, `planned_pay_date`, `collect_priority`) and not yet advertise `metrics` / `alerts`.

### AR — `/api/ar`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | AR service status (`Cashflow API`) |
| GET | `/summary` | Aggregate AR exposure KPIs |
| GET | `/partners` | Partner aging summaries |
| GET | `/partners/{partner_code}/details` | Partner risk detail |
| GET | `/partners/export` | Export partners (excel/csv) |
| GET | `/invoices` | Invoice list |
| GET | `/invoices/{invoice_number}/history` | Payment audit trail |
| GET | `/invoices/export` | Export invoices |
| GET | `/insights` | Partner-level risk insights (LLM-backed) |
| GET | `/forecast` | Cashflow forecast + what-if scenarios |
| GET | `/exceptions` | Anomalies (severity/type/age filters) |
| POST | `/pipeline/upload` | CSV upload into DuckDB |
| GET | `/settings` | Feature flags |
| PUT | `/settings/cfo_dashboard_enabled` | Toggle CFO dashboard |
| PUT | `/settings/llm_provider` | Switch LLM provider |
| PUT | `/settings/gemini_api_key` | Persist Gemini key to `.env` |
| POST | `/chatbot/query` | NL chatbot over AR data |

### AP — `/api/ap`

| Prefix | Endpoints |
|--------|-----------|
| `/auth` | `POST /login`, `GET /me`, `POST /logout`, `GET /demo-users` |
| `/dashboard` | `GET /summary` |
| `/documents` & `/intake` | `GET ""`, `POST /extract`, `POST /{id}/ai-extract`, `GET /{id}`, `POST /{id}/approve` |
| `/invoices` | `GET /feed/events`, `POST /simulate-new`, `POST /simulate-batch`, `GET ""`, `GET /{id}`, `POST /{id}/workflow/advance`, `POST /{id}/match`, `POST /{id}/approve`, `POST /{id}/exception/resolve` |
| `/purchase-orders` | `GET ""`, `GET /{po_number}`, `POST ""`, `POST /{po_number}/rematch-invoices` |
| `/contracts` | `GET ""`, `GET /{contract_id}`, `POST ""`, `POST /{contract_id}/rematch-invoices` |
| `/regulations` | `GET ""`, `GET /{id}`, `POST /{id}/apply` (no create) |
| `/demo` | `POST /reset`, `GET /state` |

---

## Domain model

### Cash events (`backend/wc/cash_events.py`)

Canonical event shape:

- `direction`: `inflow` | `outflow`
- `certainty`: AR `forecast`; AP `obligated` | `pipeline` | `held`
- `amount`, `cash_date`, `counterparty_*`, `source_system` (`ar` / `ap`), UI links

AP status → certainty:

| AP status | Certainty |
|-----------|-----------|
| Payment Ready / Approved | **obligated** |
| Pending Approval / Regulation Review | **pipeline** |
| Exception / `cashHold` | **held** |

Unresolved exceptions also force `cashHold`.

Calendar KPIs: inflows, obligated/pipeline outflows, held, net, cash at risk, plus nested `wc_metrics` (DSO/DPO/CCC).

### AR (DuckDB)

Tables: `partners`, `invoices`, `cashflow_entries`, `payment_allocations`, `partner_llm_insights`  
Plus views from `002_create_views.py` and `schema_migrations`.  
DB path: `backend/payment_allocation.duckdb` (via `ar/server.py` `DUCKDB_PATH`).  
Seeded on first init via `ar/db/seed_data.py` (demo partners × invoices into allocations).

Forecast scenarios include: `baseline`, `payment_delay_N`, partner increase/decrease, invoice/payment coverage variants, `recession`, `growth`.

### AP (in-memory)

Entities: `INVOICES`, `PURCHASE_ORDERS`, `CONTRACTS`, `REGULATIONS`, `DOCUMENTS`, feed events.

Invoice fields include vendor, amount, PO/contract refs, risk, exception, approval trail, `aiRecommendation`, plus WC fields `cashHold` / `plannedPayDate`.

WC collect priorities live in `wc/store.py` (`COLLECT_PRIORITIES`, in-memory).

Currency: AR/WC UI formats **INR**; some AP demo invoices use **USD**.

---

## Auth / security

- **Demo auth only** — shared across the SPA via `AuthContext` calling AP login.
- Tokens: `demo-token-…` in memory (`ACTIVE_TOKENS`) + `localStorage` (`ap_auth_token`, `ap_auth_user`).
- Passwords are plaintext in `DEMO_USERS` (`Demo@123`).
- Frontend `RequireAuth` gates all routes except `/login`.
- AP approve/advance/exception endpoints check `Authorization: Bearer` and **approvalRole**.
- AR and WC APIs are **not** token-protected at the router level.
- CORS from `CORS_ORIGINS` (default localhost:3000).
- **Not production-grade security.**

### Demo users

| Email | Name | Role |
|-------|------|------|
| `ap.analyst@demo.com` | Anita Rao | AP Analyst |
| `finance.manager@demo.com` | Ravi Menon | Finance Manager |
| `tax.reviewer@demo.com` | Priya Nair | Tax Reviewer |
| `controller@demo.com` | Karan Shah | Controller |

Password for all: `Demo@123`

---

## How to run

### Backend

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt   # if needed
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://localhost:8000/api/health
- WC calendar: http://localhost:8000/api/wc/calendar?days=30
- WC metrics: http://localhost:8000/api/wc/metrics?period_days=90
- WC alerts: http://localhost:8000/api/wc/alerts?days=30
- Docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
yarn install
yarn start
```

```text
REACT_APP_AR_API_BASE=http://localhost:8000/api/ar
REACT_APP_AP_API_BASE=http://localhost:8000/api/ap
REACT_APP_WC_API_BASE=http://localhost:8000/api/wc
```

### Demo walkthrough

1. Login: `ap.analyst@demo.com` / `Demo@123`
2. Land on **Cash Calendar** — review DSO/DPO/CCC, alerts, and ranked actions
3. Change horizon / scenario; Hold pay or Prioritize collect
4. Drill into AR or AP modules; calendar updates when holds change

### Optional dependencies

- System **Tesseract** for image OCR
- **Ollama** for local LLM insights / chat enrichment

---

## AI / agent features

1. **AR Chatbot** (`POST /api/ar/chatbot/query`) — pattern-matched NL queries for outstanding, overdue, forecast, what-ifs, partner insights; can use LLM service.
2. **AR LLM partner insights** — Ollama / OpenAI / Gemini; insights cached in `partner_llm_insights`.
3. **AP Document Intelligence** — deterministic “LLM-style” structured extraction (schema, confidence, evidence); can run without a live model.
4. **AP OCR + AI extract** — classify invoice/PO/contract/regulation and extract fields.
5. **AI recommendations** on AP invoices (`aiRecommendation`).

No autonomous multi-agent orchestration — feature-level AI assists inside AR/AP modules.

---

## Configuration

### Backend env (see `backend/.env.example`)

| Variable | Role | Default / notes |
|----------|------|-----------------|
| `LLM_PROVIDER` | LLM backend | `ollama` |
| `OLLAMA_MODEL` | Local model name | e.g. `llama3.2:latest` |
| `OLLAMA_BASE_URL` | Ollama server | `http://localhost:11434` (often commented in `.env.example`) |
| `LLM_TIMEOUT`, `LLM_TEMPERATURE` | LLM behavior | — |
| `GEMINI_API_KEY`, `OPENAI_API_KEY` | Cloud LLMs | OpenAI often commented |
| `CORS_ORIGINS` | Frontend origins | localhost:3000 |
| `WC_ALERT_CASH_AT_RISK` | Cash-at-risk alert threshold | `1000000` |
| `WC_ALERT_HOLD_AGING_DAYS` | Aged-hold alert | `7` |
| `WC_ALERT_CLUSTER_DAYS` | Outflow cluster window | `7` |
| `WC_ALERT_CLUSTER_RATIO` | Cluster size vs baseline | `1.2` |
| `WC_ALERT_CCC_DAYS` | CCC deterioration delta | `5.0` |
| `WC_ALERT_SCENARIO_DROP` | Scenario stress drop ratio | `0.15` |

Note: `WC_ALERT_*` defaults live in `backend/wc/alert_config.py` and may not yet appear in `.env.example` even though README / runtime support them.

### Caveats

- Local demo app — no container / K8s / cloud deploy configs in-repo
- Dual persistence: DuckDB (AR) vs in-memory (AP/WC actions) — AP/WC action state resets on backend restart unless demo seed reloads
- Sample docs for intake demos: `backend/samples/*.txt`
- Frontend package name remains `finance-control-tower-web`

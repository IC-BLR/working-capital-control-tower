# Working Capital Control Tower

Merged product: **Cash Calendar** (spine) + **AR Sensei** + **AP Document Intelligence**.

Original source apps (`cashflow-web`, `cashflow-api`, Archive AP) are untouched.

## Product model (Level B)

| Surface | Role |
|---------|------|
| `/` Cash Calendar | Dated AR inflows vs AP obligated/pipeline/held outflows + WC ratios, alerts, ranked actions |
| `/ar/*` | AR ops module (aging, risk, forecast, chatbot) |
| `/ap/*` | AP ops module (intake, match, exceptions, approvals) |
| `/hub` | Optional module picker |

## Cash Calendar intelligence

| Capability | What it shows |
|------------|---------------|
| **DSO / DPO / CCC** | Rolling working-capital ratios (DIO N/A without inventory; CCC = DSO − DPO) |
| **Cash alerts** | Negative net days, elevated AR risk, aged holds, outflow clusters, CCC deterioration, scenario stress |
| **Ranked actions** | Hold pay / prioritize collect ordered by cash-impact score (amount × timing × certainty) |

Alert thresholds can be tuned via env: `WC_ALERT_CASH_AT_RISK`, `WC_ALERT_HOLD_AGING_DAYS`, `WC_ALERT_CLUSTER_DAYS`, `WC_ALERT_CLUSTER_RATIO`, `WC_ALERT_CCC_DAYS`, `WC_ALERT_SCENARIO_DROP`.

## Structure

```text
working-capital-control-tower/
  frontend/     # CRA (port 3064)
  backend/      # FastAPI (port 8064)
    ar/         → /api/ar/*
    ap/         → /api/ap/*
    wc/         → /api/wc/*   (cash spine)
    main.py
```

## Run backend

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt   # if needed
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8064
```

- Health: http://localhost:8064/api/health
- WC calendar: http://localhost:8064/api/wc/calendar?days=30
- WC metrics: http://localhost:8064/api/wc/metrics?period_days=90
- WC alerts: http://localhost:8064/api/wc/alerts?days=30
- Docs: http://localhost:8064/docs

## Run frontend

```bash
cd frontend
yarn install
yarn start
```

Open http://localhost:3064/cct/ in your browser.

```text
REACT_APP_AR_API_BASE=http://localhost:8064/api/ar
REACT_APP_AP_API_BASE=http://localhost:8064/api/ap
REACT_APP_WC_API_BASE=http://localhost:8064/api/wc
```

## Demo

1. Login: `ap.analyst@demo.com` / `Demo@123`
2. Land on **Cash Calendar** — review DSO/DPO/CCC, alerts, and ranked actions
3. Change horizon / scenario; Hold pay or Prioritize collect
4. Drill into AR or AP modules; calendar updates when holds change

## WC API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/wc/calendar` | Cash events + KPIs (incl. DSO/DPO/CCC) + series + alerts + ranked actions |
| GET | `/api/wc/metrics` | DSO / DPO / CCC for a rolling period |
| GET | `/api/wc/alerts` | Cash alerts for the current calendar snapshot |
| POST | `/api/wc/ap/{id}/hold` | Set/clear cash hold |
| PATCH | `/api/wc/ap/{id}/planned-pay-date` | Set planned pay date |
| POST | `/api/wc/collect-priority` | Flag AR collect priority |
| GET | `/api/wc/collect-priority` | List active collect priorities |

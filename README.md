# Working Capital Control Tower

Merged product: **Cash Calendar** (spine) + **AR Sensei** + **AP Document Intelligence**.

Original source apps (`cashflow-web`, `cashflow-api`, Archive AP) are untouched.

## Product model (Level B)

| Surface | Role |
|---------|------|
| `/` Cash Calendar | Dated AR inflows vs AP obligated/pipeline/held outflows + actions |
| `/ar/*` | AR ops module (aging, risk, forecast, chatbot) |
| `/ap/*` | AP ops module (intake, match, exceptions, approvals) |
| `/hub` | Optional module picker |

## Structure

```text
working-capital-control-tower/
  frontend/     # CRA (port 3000)
  backend/      # FastAPI (port 8000)
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
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://localhost:8000/api/health  
- WC calendar: http://localhost:8000/api/wc/calendar?days=30  
- Docs: http://localhost:8000/docs  

## Run frontend

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

## Demo

1. Login: `ap.analyst@demo.com` / `Demo@123`
2. Land on **Cash Calendar** — change horizon / scenario, Hold pay, Prioritize collect
3. Drill into AR or AP modules; calendar updates when holds change

## WC API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/wc/calendar` | Cash events + KPIs + series |
| POST | `/api/wc/ap/{id}/hold` | Set/clear cash hold |
| PATCH | `/api/wc/ap/{id}/planned-pay-date` | Set planned pay date |
| POST | `/api/wc/collect-priority` | Flag AR collect priority |

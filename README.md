# Samanvaya v2 — Fixed

Government Interoperability Layer — Bidirectional Sync between SWS and FDS.

## What was fixed

| # | Issue | Fix |
|---|-------|-----|
| 1 | Fake/seeded data in API responses | Removed — APIs return only DB records |
| 2 | UBID normalization broken | `normalize_id()` strips spaces, `_`, `-`, lowercases before every lookup |
| 3 | Change detection missing | Snapshot-based diff; skips write if payload unchanged |
| 4 | SWS→FDS propagation only updated, never created | Now CREATES FDS record if none exists (and vice versa) |
| 5 | Schema translation scattered | Consolidated in `services/schema_mapper.py` |
| 6 | Frontend not parsing JSON | Pure `fetch()` + `async/await` throughout |
| 7 | UI didn't auto-refresh | Dashboard polls every 5 s; manual refresh buttons on all pages |
| 8 | Duplicate UBIDs possible | `UNIQUE(system_name, normalized_system_id)` constraint in DB |
| 9 | Audit log missing `changed_fields` | Added column + populated on every propagation |
| 10 | Stats hardcoded | All stat cards driven from `/stats` API |
| 11 | Compare UI no colours | Green = match, Red = mismatch on every field |
| 12 | CORS blocked file:// frontend | `allow_origins=["*"]` in development |

---

## Quick Start (Docker — recommended)

```bash
# 1. Clone / unzip into a folder
cd samanvaya_fixed

# 2. Start everything
docker compose up --build

# 3. Open the dashboard
open http://localhost:3000          # Frontend (nginx)
open http://localhost:8000/docs     # Swagger UI
```

---

## Quick Start (Local — no Docker)

### Prerequisites
- Python 3.11+
- PostgreSQL 15 running locally

### 1. Create the database

```sql
-- Run in psql
CREATE DATABASE samanvaya;
CREATE USER samanvaya_user WITH PASSWORD '1234';
GRANT ALL PRIVILEGES ON DATABASE samanvaya TO samanvaya_user;
```

### 2. Install dependencies & run backend

```bash
cd backend
pip install -r requirements.txt

# Tables are auto-created on startup
uvicorn app.main:app --reload --port 8000
```

### 3. Open the frontend

Simply open `frontend/index.html` in your browser:

```bash
open frontend/index.html
# or on Linux:
xdg-open frontend/index.html
```

The frontend calls `http://localhost:8000` directly via `fetch()`.

---

## Test the full flow

### 1. Create a SWS record (auto-propagates to FDS)

```bash
curl -X POST http://localhost:8000/sws/update \
  -H "Content-Type: application/json" \
  -d '{
    "sws_application_id": "SWS-2024-001",
    "business_legal_name": "Tata Steel Limited",
    "registered_address": "Bombay House, Mumbai 400001",
    "authorized_signatory_name": "N. Chandrasekaran",
    "business_type": "Manufacturing"
  }'
```

→ Check FDS: `curl http://localhost:8000/fds/all`

### 2. Test UBID normalization — all three should return the SAME ubid

```bash
curl -X POST http://localhost:8000/ubid/resolve \
  -H "Content-Type: application/json" \
  -d '{"system_name": "sws", "system_id": "SWS_2024_001"}'

curl -X POST http://localhost:8000/ubid/resolve \
  -H "Content-Type: application/json" \
  -d '{"system_name": "sws", "system_id": "sws-2024-001"}'

curl -X POST http://localhost:8000/ubid/resolve \
  -H "Content-Type: application/json" \
  -d '{"system_name": "SWS", "system_id": " SWS 2024 001 "}'
```

### 3. Check audit trail

```bash
curl http://localhost:8000/audit
```

### 4. Side-by-side comparison

```bash
curl http://localhost:8000/compare
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sws/update` | Create/update SWS record → propagate to FDS |
| POST | `/fds/update` | Create/update FDS record → propagate to SWS |
| GET | `/sws/all` | All SWS records (DB only) |
| GET | `/fds/all` | All FDS records (DB only) |
| POST | `/ubid/resolve` | Resolve normalized UBID |
| GET | `/compare` | All side-by-side comparisons |
| GET | `/compare/{ubid}` | Single UBID comparison |
| GET | `/audit` | Full audit timeline |
| GET | `/conflicts` | All conflict records |
| GET | `/stats` | Dashboard stats |
| GET | `/docs` | Swagger UI |

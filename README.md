# Maminho

Multi-sport online club management simulation. Real players act as Club
Owners or Managers in a KunaCoins (KC) economy. Full design context lives
in project notes shared with the dev (not committed here -- see chat history).

**Stack:** Django + DRF (backend/), React + Vite + Tailwind v4 (frontend/), PostgreSQL.

## Phase 1 (current)

Foundation slice, football only, no live match simulation yet:
- Auth (club_owner / manager roles)
- Club facilities (build/upgrade) + sport licenses
- KC ledger (every currency movement logged)
- Free-agent generation + scouting
- 24h async bidding for free agents (resolved by a scheduled job, not real-time --
  see `backend/README.md` for the cron setup)

## Quick start

```
git clone https://github.com/antebustruc-cloud/maminho.git
cd maminho
cp backend/.env.example backend/.env   # edit DB creds etc.
docker compose up --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py generate_players 200

cd frontend
npm install
npm run dev
```

Backend API: `http://localhost:8000/api/` (see `backend/README.md` for endpoints).
Frontend dev server: `http://localhost:5173`.

**Important:** `resolve_expired_bids` must run on a schedule (cron) for
free-agent claims to ever resolve -- see `backend/README.md`.

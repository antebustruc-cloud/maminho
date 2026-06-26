# Maminho backend

Django + DRF API. See `/maminho` repo root for the full project context.

## Local dev (Docker)

```
cp backend/.env.example backend/.env   # edit values
docker compose up --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py generate_players 200
```

API will be at `http://localhost:8000/api/`, admin at `/admin/`.

## Scheduled jobs

Phase 1 ships one job that MUST run on a schedule for free-agent claiming
and contract-expiry re-claiming to actually resolve. There's no Celery yet
(deliberately, to keep Phase 1 simple) -- just cron calling a management
command:

```
# crontab -e  (on the droplet, inside or outside the container)
*/5 * * * * docker compose -f /path/to/maminho/docker-compose.yml exec -T backend python manage.py resolve_expired_bids >> /var/log/maminho/resolve_bids.log 2>&1
```

Every 5 minutes is a reasonable starting interval -- it means a window can
close up to 5 minutes "late" in the worst case, which is fine for a 24h
window. Tighten it later if needed.

## API overview (Phase 1)

| Endpoint | Method | Who | What |
|---|---|---|---|
| `/api/auth/register/` | POST | anyone | Create club_owner or manager account |
| `/api/auth/login/` | POST | anyone | Get auth token |
| `/api/auth/me/` | GET | authenticated | Current user info |
| `/api/clubs/me/` | GET | club_owner | Own club + facilities + licenses |
| `/api/clubs/facilities/build/` | POST | club_owner | Build a new facility |
| `/api/clubs/facilities/<id>/upgrade/` | POST | club_owner | Upgrade a facility one level |
| `/api/clubs/licenses/purchase/` | POST | club_owner | Buy a sport license |
| `/api/players/free-agents/` | GET | authenticated | Browse free-agent pool |
| `/api/players/mine/` | GET | manager | Own roster |
| `/api/players/<id>/bid/` | POST | manager | Place/raise a bid (opens or joins a 24h window) |
| `/api/players/club-deals/` | POST | manager | Record an agreed club-deal (loan player to a club) |

Auth: `Authorization: Token <token>` header (DRF TokenAuthentication).

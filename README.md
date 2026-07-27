# PulseSchedule – Social Media Scheduling SaaS

Multi-tenant SaaS platform to **connect social accounts**, **schedule posts**, **auto-publish via background workers**, and **view engagement analytics**.

Built for the Advanced Full-Stack SaaS assignment.

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, JWT |
| Frontend | React (Vite), Tailwind CSS, React Router, Axios |
| Infra (local) | Docker Compose (PostgreSQL + Redis) |

## Project structure

```text
SocialMedia_Scheduling/
├── docker-compose.yml          # PostgreSQL + Redis
├── README.md
├── backend/
│   ├── .env.example
│   ├── alembic/                # DB migrations
│   ├── app/
│   │   ├── auth/               # JWT + role dependencies
│   │   ├── models/             # Organization, User, SocialAccount, Post, PostLog, Analytics
│   │   ├── routers/            # API endpoints
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic + mock publisher
│   │   ├── workers/            # Celery app + publish tasks
│   │   ├── utils/              # Redis cache helpers
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   └── tests/                  # Scheduling, workers, roles, tenant isolation
└── frontend/
    ├── .env.example
    └── src/                    # Login, register, dashboard, posts, accounts
```

## Quick start

### 1) Start PostgreSQL + Redis

```bash
docker compose up -d
```

### 2) Backend setup

> Use **Python 3.11–3.13** (3.14 may lack wheels for some packages).

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 3) Background worker + scheduler (separate terminals)

From `backend/` with the same virtualenv and `.env`:

```bash
# Worker process (executes publish jobs)
celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=solo

# Beat process (periodically finds due posts)
celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

> On Windows use `--pool=solo` for the worker.

### 4) Frontend setup

```bash
cd frontend
npm install
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
npm run dev
```

App: [http://localhost:5173](http://localhost:5173)

## Scheduling architecture

```text
User schedules post (status=scheduled, future scheduled_time)
        │
        ▼
Celery Beat (every 30s by default)
  → task: publish_due_posts
  → finds posts where scheduled_time <= now AND status=scheduled
        │
        ▼
Celery Worker
  → task: publish_post(post_id)
  → locks post: scheduled → publishing   (prevents duplicate publish)
  → mock platform API call (Twitter / Instagram / LinkedIn)
  → writes PostLog response
  → on success: status=published + Analytics (views/likes/shares)
  → on failure: retry (optional) or status=failed
```

### Critical backend rules implemented

- `scheduled_time` must be in the future when creating/updating posts
- Duplicate publishing prevented via `publishing` lock status + skip if already published
- Failed posts logged in `PostLog`
- Retry mechanism: up to `MAX_PUBLISH_RETRIES` (default 3), then mark `failed`
- Multi-tenant isolation: every query is scoped by `organization_id` from JWT
- Role-based access: only **admin** can connect/delete social accounts and add members

## Core data models

- **Organization** – tenant
- **User** – `admin | member`, belongs to one organization
- **SocialAccount** – `twitter | instagram | linkedin` + mock `access_token`
- **Post** – content, `scheduled_time`, status (`scheduled | publishing | published | failed`)
- **PostLog** – execution status + API response
- **Analytics** – views, likes, shares per published post

## API overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create org + admin user |
| POST | `/api/auth/login` | JWT login |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/members` | Admin adds member |
| GET/POST/DELETE | `/api/social-accounts` | Manage connected accounts |
| GET/POST/PATCH/DELETE | `/api/posts` | Schedule & manage posts |
| GET | `/api/posts/{id}/logs` | Publish logs |
| GET | `/api/analytics/dashboard` | Totals + trends (Redis cached) |
| GET | `/api/analytics/posts/{id}` | Per-post analytics |

## Testing

```bash
cd backend
.\.venv\Scripts\Activate.ps1   # if needed
pytest -v
```

Required coverage included:

- Scheduling logic (`scheduled_time` validation, create scheduled posts)
- Background job execution (inline worker helpers, publish + retry + duplicate guard)
- Role-based access (member cannot connect accounts)
- Data isolation (org A cannot read org B posts/accounts/analytics)

## Demo flow (beginner)

1. Start Docker, backend, Celery worker, Celery beat, frontend
2. Register at `/register` (creates your organization)
3. Go to **Accounts** → connect Twitter with token `mock-token-demo`
4. Go to **Posts** → schedule a post a few minutes ahead
5. Wait for Celery Beat/Worker (or temporarily set an earlier time in DB for demos)
6. Refresh **Dashboard** for engagement stats
7. Open post **Logs** to see mock API responses

Tip: use access token `invalid` to force publish failures and see retries.

## Environment variables

See:

- `backend/.env.example`
- `frontend/.env.example`

## Notes

- External social APIs are **mocked** in `app/services/publisher.py` (allowed by assignment)
- Redis is used for Celery broker/backend and short-lived analytics caching
- JWT carries `user_id`, `organization_id`, and `role` for tenant + RBAC checks

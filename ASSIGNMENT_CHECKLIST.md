# Assignment coverage checklist

Use this to verify every required item is present.

## Tech stack
- [x] FastAPI backend
- [x] PostgreSQL + SQLAlchemy + Alembic
- [x] Redis (Celery queues + analytics cache)
- [x] Celery worker + beat scheduler
- [x] JWT authentication
- [x] React (Vite) + Tailwind + React Router + Axios

## Data models
- [x] Organization
- [x] User (admin | member)
- [x] SocialAccount (twitter | instagram | linkedin)
- [x] Post (scheduled | published | failed + temporary publishing lock)
- [x] PostLog
- [x] Analytics

## Features
- [x] Multi-tenant organization isolation
- [x] Connect social accounts
- [x] Schedule future posts (validated)
- [x] Background auto-publish (mock API)
- [x] Duplicate publish prevention
- [x] Failed posts + retry
- [x] Analytics dashboard (totals + trends)
- [x] Role-based access (admin vs member)

## Tests
- [x] Scheduling logic
- [x] Background job execution
- [x] Role-based access
- [x] Data isolation
- [x] PostLog + stuck publishing reclaim

## Docs / submission
- [x] backend/.env.example + frontend/.env.example
- [x] README setup + scheduling architecture + worker setup
- [x] Clean architecture (services / workers / routers)
- [x] GitHub repository with commit history

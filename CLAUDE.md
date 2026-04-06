# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`website_aicut` is a video task processing platform MVP. It has a Next.js frontend, a FastAPI backend, and a PostgreSQL database, orchestrated with Docker Compose.

## Common Commands

### Full stack (Docker Compose)

```bash
docker compose up --build
```

Services: web (Next.js, port 3000), api (FastAPI, port 8000), db (PostgreSQL, port 5432).
Default admin: `admin` / value of `ADMIN_PASSWORD` in `.env`.

### Frontend (apps/web)

```bash
cd apps/web
npm install
npm run dev          # Requires API running at http://127.0.0.1:8000
npm run build
npm run test:e2e     # Playwright tests
```

Playwright auto-starts the dev server unless `PLAYWRIGHT_SKIP_WEBSERVER` is set.

### Backend (apps/api)

```bash
cd apps/api
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
pytest               # Run API tests
```

If `DATABASE_URL` is unset, the API falls back to a local SQLite file (`website_aicut.db`).

## High-Level Architecture

### Frontend-to-Backend Communication

The web app does not call the API directly from the browser. All requests go through a Next.js catch-all Route Handler at `apps/web/app/api/proxy/[...path]/route.ts`, which forwards them to `INTERNAL_API_BASE_URL` (the FastAPI service). This keeps auth cookies scoped to the same origin and avoids CORS issues.

### Authentication Flow

- The API uses session-based auth with an HTTP-only `session_token` cookie.
- On startup, the API auto-creates an admin user from `ADMIN_USERNAME` and `ADMIN_PASSWORD` env vars.
- Routes under `/admin/*` require `role="admin"`; `/user/*` routes require any authenticated user.
- Frontend pages guard their own routes by fetching `/api/proxy/auth/me` and redirecting based on `role`.

### Database & Models

SQLAlchemy 2.0 with declarative mapped columns. Tables are auto-created on startup (`Base.metadata.create_all`).

Core models in `apps/api/app/models.py`:
- `Company` — has many `User`s and `Material`s
- `User` — belongs to an optional `Company`, has `role` (`admin` | `user`)
- `Material` — belongs to a `Company`, has `name` and `remark`
- `Session` — stores the `session_token` cookie value

Pydantic schemas live in `apps/api/app/schemas.py`. CRUD helpers live in `apps/api/app/crud.py`.

### User Workspace UI Pattern

Normal users land on `/welcome` and use `/tts`. Both pages wrap content in `UserWorkspaceShell` (`apps/web/components/user-workspace-shell.tsx`), which provides:
- A fixed left sidebar with primary navigation and a mock task list
- A top metrics bar
- Breadcrumbs / secondary tabs in the content header
- Consistent "slate" visual theme (rounded-[28px] cards, `#18364e` accent)

### TTS Integration

The `/tts` page lets users generate audio from Chinese copy. The API integrates with MiniMax (`apps/api/app/tts.py`) using the `speech-2.8-hd` model. Requires env vars:
- `MINIMAX_AUDIO_API_KEY`
- `MINIMAX_AUDIO_GROUP_ID` (optional)
- `MINIMAX_TTS_VOICE_ID`

### Design Preview

`/design-preview` is a non-functional style reference page showing three visual directions (warm, slate, ink). The actual user-facing pages adopt the "slate" direction.

### Project Documentation

Important product docs are in `doc/`:
- `prd.md` — Product requirements and scope
- `PROJECT_RULE.md` — Tech stack rules (Next.js, FastAPI, Tailwind, SQLAlchemy, etc.)
- `TASK_WORKFLOW.md` — Task state machine definitions for the video processing worker

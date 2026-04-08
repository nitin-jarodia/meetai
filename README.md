# MeetAI

Production-style foundation for an **AI Meeting Assistant**: **Next.js (App Router)** frontend, **FastAPI** backend, **SQLite** (default) or **PostgreSQL**, **WebSockets**, **Groq** for summaries, and a **Whisper-ready** transcription stub (no heavy GPU install by default).

## Prerequisites

- **Node.js** 20+ and **npm**
- **Python** 3.11+
- **Docker** (optional) for PostgreSQL — the default `DATABASE_URL` uses **SQLite** so you can run the backend without Docker
- **Groq API key** (free tier) from [Groq Console](https://console.groq.com) for real AI summaries (optional; API returns a clear message if the key is missing)

## Quick start (end-to-end)

You need **two terminals**: backend (port **8000**) and frontend (port **3000**). Default **SQLite** needs no Docker.

| Terminal | Commands |
|----------|----------|
| **1 — API** | `cd backend` → create `.venv`, `pip install -r requirements.txt`, `copy .env.example .env`, then **`python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`** (or run `.\run-api.ps1` on Windows) |
| **2 — UI** | `cd frontend` → `copy .env.example .env.local`, `npm install`, `npm run dev` |

Then open [http://localhost:3000](http://localhost:3000), **Register**, create a meeting, open the room. If registration fails with “Cannot reach …:8000”, the API is not running.

### 1. Database (optional)

By default, `backend/.env.example` uses **SQLite** (`meetai.db` created when you start the API). No container is required.

To use **PostgreSQL** instead, from the repo root:

```bash
docker compose up -d
```

Then set `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/meetai` in `backend/.env`.

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env: set JWT_SECRET_KEY and optionally GROQ_API_KEY
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Use **`python -m uvicorn`** (not the bare `uvicorn` command) so Windows always uses the venv’s Python. If you moved the project folder after creating `.venv`, run `pip install --force-reinstall "uvicorn[standard]==0.34.0"` inside the venv, or delete `.venv` and recreate it.

- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health: `GET /health`

### 3. Frontend

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Register, create a meeting from the dashboard, then open the meeting room.

### 4. WebSocket (scaffold)

The meeting page connects to:

`ws://localhost:8000/ws/meetings/{meeting_id}?token=<JWT>`

The server echoes messages and sends a small `connected` JSON event — replace with your own events for presence, signaling, or transcript chunks.

### 5. AI summary (optional)

With `GROQ_API_KEY` set, call:

`POST /api/v1/ai/summary` with header `Authorization: Bearer <token>` and body `{"text":"..."}`.

### 6. Transcription stub

```bash
cd backend
python -m scripts.demo_transcription
```

Install [OpenAI Whisper](https://github.com/openai/whisper) locally when you are ready for real STT; extend `app/services/transcription_service.py`.

## Monorepo layout

```
meetai/
├── backend/
│   ├── app/
│   │   ├── api/           # HTTP routes (v1) + WebSocket route
│   │   ├── core/          # Settings, JWT, DB engine
│   │   ├── models/        # SQLAlchemy: User, Meeting, Participant, Transcript
│   │   ├── schemas/       # Pydantic
│   │   ├── services/      # meeting_service, ai_service (Groq + provider abstraction), transcription_service
│   │   ├── repositories/  # Data access
│   │   ├── websocket/     # Connection manager
│   │   └── utils/
│   ├── scripts/           # e.g. transcription demo
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── (auth)/        # login, register
│   │   ├── (dashboard)/   # dashboard
│   │   └── meeting/[id]/  # meeting room skeleton
│   ├── components/
│   ├── hooks/
│   ├── services/          # API client
│   ├── store/             # Zustand (auth token)
│   └── package.json
├── shared/                # Optional shared TS types
├── docker-compose.yml
└── README.md
```

## API overview (v1)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | No | Sign up |
| POST | `/api/v1/auth/login` | No | JWT access token |
| POST | `/api/v1/meetings` | Bearer | Create meeting |
| POST | `/api/v1/meetings/{id}/join` | Bearer | Join meeting |
| GET | `/api/v1/meetings/{id}` | Bearer | Meeting details |
| POST | `/api/v1/ai/summary` | Bearer | Test Groq summary |

## Future-friendly hooks

- **Realtime transcription**: append `Transcript` rows from a background worker; notify clients via WebSocket rooms in `app/websocket/manager.py`.
- **Multi-user / WebRTC**: reuse meeting id + JWT; add signaling messages over the same WebSocket or a dedicated namespace.
- **Search**: PostgreSQL full-text or pgvector later; keep repositories thin.
- **Action items**: extend `AIService` / provider with structured JSON output.

## License

MIT (adjust as needed).

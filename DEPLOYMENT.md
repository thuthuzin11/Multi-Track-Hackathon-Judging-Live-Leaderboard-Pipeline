# Deploying so people on different WiFi networks can use it

Everything in `README.md` covers running the app **on one machine**
(`localhost`). That's fine for building/testing, but a judge on their
phone at a coffee shop, or a spectator at home, can't reach
`localhost` — it only means "this computer." To let people join from
their own devices on different networks, the app needs to live
somewhere with a real public address. No Docker needed for any of
these options.

You have two realistic paths: a **quick temporary tunnel** (good for
"the hackathon is today, get this live in 15 minutes") or a **proper
free-tier deployment** (good for "this needs to work reliably for the
whole event and I'll reuse it next time").

---

## Option 1 — Quick & temporary: ngrok

Good for same-day use. Keeps everything running on your laptop; ngrok
just gives it a public URL.

1. Run the backend and frontend locally as usual (see `README.md`,
   Option B — no Docker).
2. Install [ngrok](https://ngrok.com/download) and sign up for a free
   account.
3. In a new terminal, expose the backend:
   ```bash
   ngrok http 8000
   ```
   Copy the `https://xxxx.ngrok-free.app` URL it gives you — that's your
   **public backend URL**.
4. Add that URL to the backend's CORS allow-list (`backend/.env`):
   ```
   ALLOWED_ORIGINS=*
   ```
   (`*` is simplest for a same-day event; tighten it later if you turn
   this into something long-running.)
5. Point the frontend at that backend URL:
   ```bash
   cd frontend
   VITE_API_URL=https://xxxx.ngrok-free.app npm run dev -- --host 0.0.0.0
   ```
6. In a second ngrok terminal, expose the frontend too:
   ```bash
   ngrok http 5173
   ```
   Share **that** `https://yyyy.ngrok-free.app` URL with judges and
   spectators — that's the link they open on their own phone/laptop,
   on any WiFi, anywhere.

Downsides: free ngrok URLs change every time you restart it, and your
laptop has to stay on and connected the whole event.

---

## Option 2 — Proper deployment (free tiers, no Docker, no server management)

This is the "set it up once, share a stable link" path. All of these
platforms build Python/Node apps directly from source — none of them
require a Dockerfile.

### 2a. Database + cache (hosted, so your API isn't tied to your laptop)

- **PostgreSQL**: [Neon](https://neon.tech) or [Supabase](https://supabase.com) —
  both have a free tier and give you a `postgresql://...` connection
  string in under a minute.
- **Redis**: [Upstash](https://upstash.com) — free tier, gives you a
  `redis://...` connection string (they also support a REST API, but
  the standard connection string works with this project as-is).

### 2b. Backend (FastAPI + worker manager)

Deploy on [Render](https://render.com) (or Railway/Fly.io — steps are
similar):

1. Push this project to a GitHub repo.
2. On Render, create a **Web Service** from the repo, root directory
   `backend/`:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment variables: `DATABASE_URL`, `REDIS_HOST`, `REDIS_PORT`
     (from step 2a), `JWT_SECRET` (any long random string),
     `ALLOWED_ORIGINS` (your frontend's URL once you have it, comma-separated
     if you need more than one).
3. Create a second **Background Worker** service from the same repo,
   same root directory and same environment variables, but:
   - Start command: `python run_workers.py`

   This is the piece that has to stay a *separate* process — it's the
   whole point of the architecture (parallel workers processing track
   buffers independently of the API).
4. Once both are live, note the Web Service's public URL, e.g.
   `https://hackathon-api.onrender.com`.

### 2c. Frontend

Deploy on [Vercel](https://vercel.com) or [Netlify](https://netlify.com):

1. Import the same repo, root directory `frontend/`.
2. Build command: `npm run build`, output directory: `dist`.
3. Environment variable: `VITE_API_URL=https://hackathon-api.onrender.com`
   (your backend's URL from 2b).
4. Deploy. You get a stable public URL, e.g.
   `https://hackathon-leaderboard.vercel.app` — that's what you give to
   judges and spectators. It works from any device, any WiFi, anywhere.
5. Go back to the backend's `ALLOWED_ORIGINS` env var and set it to this
   exact frontend URL (tighter than `*`, recommended once you're not
   just testing).

### 2d. Create your admin login

Run once, from your own machine, pointed at the hosted database — this
creates your one and only admin account (there's no other way to get
the first one, since creating an admin normally requires already being
logged in as one):

```bash
cd backend
DATABASE_URL="<your Neon/Supabase URL>" REDIS_HOST="<your Upstash host>" \
  REDIS_PORT="<your Upstash port>" ADMIN_USERNAME="admin" \
  ADMIN_PASSWORD="something-only-you-know" python seed.py
```

Then log in on the Admin tab and create your event, tracks, teams, and
judge accounts from the Admin dashboard — `seed.py` doesn't create any
of that for you.

---

## Which option should I pick?

| | ngrok | Render/Vercel |
|---|---|---|
| Setup time | ~10 min | ~30–45 min |
| Needs your laptop running during the event | Yes | No |
| Link stays the same next time | No (free tier) | Yes |
| Good for | "we're judging today" | reusing this across multiple hackathons |

Either way: **no Docker, no server to SSH into, no manual OS setup** —
just a build command and a start command on a platform that runs it
for you.

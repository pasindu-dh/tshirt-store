# Deployment guide

FURZY is a React/Vite frontend and a FastAPI backend. The backend uses
SQLAlchemy and works with SQLite locally and PostgreSQL in production.
Uploaded product images are stored on the backend's local filesystem, so
production needs persistent storage for that directory (or an object-storage
adapter added in a later phase).

## Recommended production layout

| Part | Suggested host |
| --- | --- |
| Frontend (`frontend/`) | Vercel or Netlify |
| API (`backend/`) | Render or Railway (Docker or native Python) |
| Database | Neon, Supabase, or another managed PostgreSQL service |
| Images | A persistent disk on the API host; Cloudinary/S3 if the API runs multiple instances |

HTTPS is provided by these platforms. Never serve the API over plain HTTP in
production.

## 1. Prepare the database

Create a PostgreSQL database and copy its connection URL. Use the psycopg 3
driver prefix:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Run migrations from the backend directory during the release/deploy step:

```bash
cd backend
python -m alembic upgrade head
```

Do not run `python -m app.seed` in production; it is demo catalog data. Seed
your real catalog through the admin panel or with a data-import script.

## 2. Deploy the backend

### Render / Railway (native Python)

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Release command: `python -m alembic upgrade head`

### Docker

A `backend/Dockerfile` is included:

```bash
docker build -t furzy-api ./backend
docker run --env-file backend/.env -p 8000:8000 \
  -v furzy-uploads:/app/uploads furzy-api
```

Run `python -m alembic upgrade head` before starting a new release/container.

### Required environment variables

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | PostgreSQL URL with `postgresql+psycopg://` |
| `JWT_SECRET` | Long random value, for example `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `FRONTEND_ORIGINS` | Comma-separated production frontend origins, no trailing slash |
| `UPLOADS_DIR` | Directory on a persistent disk, for example `/var/data/uploads` |
| `SHIPPING_FEE_LKR` | Optional checkout shipping fee |
| `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Only needed for the one-time admin seed command |

Generate the admin account once, after migrations:

```bash
python -m app.seed_admin
```

`seed_admin` refuses missing, invalid, placeholder, or known-default values.
It never recreates the old development admin account. Remove the admin
password from the runtime environment after seeding if your host supports
separate release/run environments.

Do not commit `backend/.env`. It is ignored by Git and must be supplied through
the host's secret manager.

### Uploads and multiple instances

`UPLOADS_DIR` must be writable and persistent. On platforms with an ephemeral
filesystem (for example, many serverless deployments), mount a persistent disk
or add an object-storage adapter. If you run more than one API instance, local
disk uploads are not shared; use Cloudinary, S3, or another shared store.

### Rate limiting

Login rate limiting is in-memory and per process. It protects the common
single-instance deployment. For multiple API workers or instances, back the
limiter with Redis or an edge rate-limit service.

## 3. Deploy the frontend

### Vercel

1. Import the repository.
2. Set the project root to `frontend`.
3. Framework preset: Vite; build command `npm run build`; output `dist`.
4. Add `VITE_API_URL=https://your-api-host` (no trailing slash).
5. Deploy. `frontend/vercel.json` rewrites SPA routes such as `/orders/12` and
   `/admin/orders/3` to `index.html`.

### Netlify

1. Base directory: `frontend`.
2. Build command: `npm run build`; publish directory: `dist`.
3. Add `VITE_API_URL=https://your-api-host`.
4. `frontend/public/_redirects` handles SPA deep links.

After the frontend domain is known, set `FRONTEND_ORIGINS` on the backend to
that exact origin and redeploy the API.

## 4. CI

`.github/workflows/ci.yml` runs three jobs:

- Backend: installs `requirements-dev.txt` and runs pytest.
- Frontend: installs with `npm ci`, then lint, Vitest, and production build.
- End-to-end: creates a disposable SQLite database, seeds an admin, starts the
  API and Vite, installs Chromium, and runs the Playwright purchase journey.

No production secrets are needed in CI; the workflow uses disposable test
values.

## 5. Running the E2E suite locally

Use a disposable database so the test's order/customer records do not touch
your development data:

```bash
cd backend
# Set DATABASE_URL to a throwaway SQLite file and ADMIN_* to test values,
# then:
python -m alembic upgrade head
python -m app.seed
python -m app.seed_admin
uvicorn main:app --port 8005
```

In another terminal:

```bash
cd frontend
npx playwright install chromium   # once
E2E_DISPOSABLE_DB=1 E2E_ADMIN_EMAIL=... E2E_ADMIN_PASSWORD=... npm run test:e2e
```

The test skips itself unless `E2E_DISPOSABLE_DB=1` or `CI=true` is set,
because it leaves an order and customer account behind. It deletes the product
it creates.

If a Vite dev server is not already running, the Playwright config starts one
on port 5173 using the default API URL. Set `E2E_API_URL` and `E2E_BASE_URL` to
target another pair of servers. On Windows you can use the installed Chrome
instead of downloading Chromium:

```powershell
$env:E2E_DISPOSABLE_DB = "1"
$env:PLAYWRIGHT_CHANNEL = "chrome"
```

Alternatively, `backend/.env` is read for the admin email/password when the
`E2E_ADMIN_*` variables are not set. Never point the E2E test at the production
database.

## 6. Production security checklist

- [ ] Strong `JWT_SECRET` and a new admin password; no `.env` in Git.
- [ ] `FRONTEND_ORIGINS` limited to the real frontend origin(s).
- [ ] HTTPS enforced by the host; HSTS is sent for HTTPS requests.
- [ ] Database backups and SSL enabled.
- [ ] Uploads directory private to the app and backed up.
- [ ] Login rate limiting sized for your traffic or moved to Redis.
- [ ] Admin account verified with `python -m app.seed_admin` validation rules.
- [ ] Dependencies updated and `npm audit` / `pip-audit` reviewed.
- [ ] `python -m pytest` and `npm test` green before deployment.

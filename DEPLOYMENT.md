# Deployment guide

FURZY is a React/Vite frontend and a FastAPI backend. The backend uses
SQLAlchemy and works with SQLite locally and PostgreSQL in production.
Admin-uploaded product images are stored in PostgreSQL and served from
`/uploads`. The local uploads directory is a fallback for existing local files
and development; it is not required for durability.

## Recommended free-demo layout

| Part | Suggested host |
| --- | --- |
| Frontend (`frontend/`) | Vercel Hobby |
| API (`backend/`) | Render Free |
| Database | Neon Free PostgreSQL |
| Images | Neon PostgreSQL (`uploaded_images` table) |

HTTPS is provided by these platforms. Never serve the API over plain HTTP in
production. For a paid production deployment, a persistent disk or S3-style
object storage can replace database-backed image storage later.

## Free demo deployment: Vercel Hobby + Render Free + Neon Free

This is the supported path for a **non-commercial university/personal
demonstration**. The repository's `render.yaml` and `frontend/vercel.json` are
configured for this stack.

### Read the free-tier limits first

- **Render Free** sleeps after 15 minutes without traffic. The next request
  takes about a minute to wake it. Each workspace gets 750 instance hours per
  month. The filesystem is ephemeral and cannot attach a disk. Render Free has
  no shell and no pre-deploy commands, and it blocks outbound SMTP ports 25,
  465, and 587.
- **Neon Free** includes 1 GB of PostgreSQL storage and 100 CU-hours per
  project per month. Computes suspend after 5 minutes of inactivity and resume
  on the next connection. Uploaded images count toward the 1 GB.
- **Vercel Hobby** is free for personal, non-commercial projects. This demo
  qualifies; do not use it for a commercial store. Hobby includes 100 GB of
  fast data transfer and up to 100 deployments per day, which is ample for a
  small demo.
- **Email cannot be sent from Render Free.** The app is configured with email
  disabled for this demo: registration, login, cart, checkout, orders, returns,
  and admin pages work, but verification emails, password-reset emails, order
  emails, and admin alert emails are skipped. Never set
  `EMAIL_VERIFICATION_REQUIRED=true` on this deployment.
- **PayHere is sandbox-only.** Without sandbox credentials, online payments
  remain disabled and Cash on Delivery still works. Never set
  `PAYHERE_SANDBOX=false` for the free demo.

### Uploaded images on the free plan

Render Free has no persistent disk, so admin-uploaded product images are
stored in PostgreSQL in the `uploaded_images` table and served from
`/uploads/<filename>`. `UPLOADS_DIR` is only a local fallback/cache; on Render
it points to `/tmp/furzy-uploads`, which disappears on restart. Existing local
files in `backend/uploads` are still served.

Images count toward Neon's storage limit. The upload limit is 5 MB per image;
keep demo images small and remove unused uploads if storage grows.

### What render.yaml creates

- Free Python web service named `furzy-api`, root directory `backend`
- Python `3.13.16`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`
- Health check: `/health/ready`
- `UPLOADS_DIR=/tmp/furzy-uploads`
- No disk, no pre-deploy command
- `autoDeployTrigger: "off"`; creating the Blueprint triggers the first deploy

### Step 1: Create the Neon database

1. Create a Neon project and database. Choose the Neon region closest to
   your Render region (Render’s default is Oregon) to reduce latency.
2. Copy both connection strings:
   - **Pooled** URL for Render (`DATABASE_URL`)
   - **Direct** URL for migrations (`MIGRATION_DATABASE_URL`)
3. Replace the scheme in both with `postgresql+psycopg://` and keep
   `?sslmode=require`. For example:
   ```text
   postgresql+psycopg://USER:PASSWORD@HOST-pooler.REGION.aws.neon.tech/DB?sslmode=require
   postgresql+psycopg://USER:PASSWORD@HOST.REGION.aws.neon.tech/DB?sslmode=require
   ```
   Never commit these URLs.

### Step 2: Run migrations and seed the admin from your computer

Render Free has no shell or pre-deploy command, so run these **locally**. Use
temporary environment variables; do not overwrite your existing
`backend/.env`, so your local SQLite setup remains intact.

PowerShell example (activate the backend virtual environment first, for
example `.\venv\Scripts\Activate.ps1`):

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST-pooler.REGION.aws.neon.tech/DB?sslmode=require"
$env:MIGRATION_DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST.REGION.aws.neon.tech/DB?sslmode=require"
$env:ADMIN_NAME = "Store Admin"
$env:ADMIN_EMAIL = "you@example.com"
$env:ADMIN_PASSWORD = "use-a-strong-password"
python -m alembic upgrade head
python -m app.seed_admin
Remove-Item Env:ADMIN_PASSWORD
Remove-Item Env:DATABASE_URL
Remove-Item Env:MIGRATION_DATABASE_URL
```

Bash users can use `export ...` and `unset ...` instead.

- `DATABASE_URL` is the pooled URL used by the application.
- `MIGRATION_DATABASE_URL` is the direct URL used by Alembic.
- `python -m app.seed` is **never** run automatically and should not be run
  against this database. It is only the demo catalog seeder.
- `python -m app.seed_admin` can be rerun if you need to reset the admin
  password; it updates the existing admin account.

### Step 3: Create the Render Blueprint

1. In Render, create a new **Blueprint** from this repository. Render reads
   `render.yaml`.
2. Set the prompted values:
   - `DATABASE_URL` — the Neon **pooled** URL
   - `FRONTEND_ORIGINS` — use `https://your-project.vercel.app` for now if the
     Vercel URL is not known yet (no trailing slash)
   - `FRONTEND_BASE_URL` — same as `FRONTEND_ORIGINS`
   - `BACKEND_PUBLIC_URL` — the Render service URL, for example
     `https://furzy-api.onrender.com` (update it after Render shows the exact
     URL)
3. Render generates `JWT_SECRET`; the rest of the required values are already
   in `render.yaml`. PayHere sandbox credentials are optional and can be added
   later in the Render dashboard.
4. Creating the Blueprint triggers the first deploy. The free instance may
   take a minute to start, especially while Neon wakes up. `autoDeployTrigger`
   is `"off"`, so later pushes do not deploy until you trigger them manually.
   If the first deploy fails its health check while Neon is cold-starting,
   redeploy the service after the database is awake.

### Step 4: Deploy the frontend to Vercel

1. Import the repository into Vercel.
2. Set the project root to `frontend`; use the Vite framework and Node.js 22.
3. Add this environment variable for Production (and Preview only if you
   need preview builds):
   ```text
   VITE_API_URL=https://furzy-api.onrender.com
   ```
   Use the exact Render URL and no trailing slash. The Vite build deliberately
   fails if this value is missing or is not an `https://` URL.
4. Deploy and copy the resulting Vercel production URL.

### Step 5: Connect CORS and public URLs

In Render, update these environment variables and save; Render restarts the
API:

- `FRONTEND_ORIGINS=https://your-project.vercel.app` — the exact Vercel
  production origin, no trailing slash. Add custom domains as a
  comma-separated list. Vercel preview domains need their own exact origins;
  wildcard CORS is rejected.
- `FRONTEND_BASE_URL=https://your-project.vercel.app` — used in email links
  and PayHere return URLs.
- `BACKEND_PUBLIC_URL=https://furzy-api.onrender.com` — used for the PayHere
  notification URL.

If Render gave you a different service URL, use that exact URL.

### Step 6: Verify the demo

```bash
curl https://furzy-api.onrender.com/health/ready
```

Then open the Vercel site, sign in as the admin, and try the main flow:
browse, add to cart, place a Cash on Delivery order, and upload a product
image in the admin panel. Wait for Render to sleep (15+ minutes), reload the
product image, and confirm it still loads; this proves the image came from
Neon rather than the ephemeral filesystem. If the image is missing, check that
`alembic upgrade head` created the `uploaded_images` table.

Run the API smoke test from your computer:

```powershell
cd backend
$env:SMOKE_ADMIN_EMAIL = "you@example.com"
$env:SMOKE_ADMIN_PASSWORD = "your-admin-password"
python -m app.smoke_test --base-url https://furzy-api.onrender.com
Remove-Item Env:SMOKE_ADMIN_PASSWORD
Remove-Item Env:SMOKE_ADMIN_EMAIL
```

### Step 7: PayHere sandbox (optional)

If you have PayHere sandbox credentials, add them in the Render dashboard:

- `PAYHERE_MERCHANT_ID`
- `PAYHERE_MERCHANT_SECRET`
- optionally `PAYHERE_API_APP_ID` and `PAYHERE_API_APP_SECRET`

Keep `PAYHERE_SANDBOX=true` and `PAYMENT_MOCK_ENABLED=false`. Never set
`PAYHERE_SANDBOX=false` for this free demo. PayHere notifications go to:

```text
https://furzy-api.onrender.com/payments/payhere/notify
```

Render Free may be asleep when PayHere sends a notification; the request wakes
the service, so allow for a cold start and retry sandbox tests if needed.
Without sandbox credentials, checkout uses Cash on Delivery only.

### Environment variables to configure

#### Render (required)

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Neon **pooled** URL, `postgresql+psycopg://`, with `sslmode=require` |
| `FRONTEND_ORIGINS` | Exact Vercel origin(s), no trailing slash |
| `FRONTEND_BASE_URL` | Exact Vercel origin used in links |
| `BACKEND_PUBLIC_URL` | Render service HTTPS URL |
| `JWT_SECRET` | Generated by Render; keep it |
| `UPLOADS_DIR` | `/tmp/furzy-uploads` (local fallback only) |
| `APP_ENV` | `production` |

The committed `render.yaml` also sets these values for you:
`PAYMENT_PROVIDER=payhere`, `PAYMENT_MOCK_ENABLED=false`,
`PAYHERE_SANDBOX=true`, `EMAIL_VERIFICATION_REQUIRED=false`,
`REVIEW_MODERATION_ENABLED=false`, `ADMIN_EMAIL_ALERTS_ENABLED=false`,
`STOCK_RESERVATION_SWEEP_ENABLED=true`, and the shipping/return defaults.
Do not change `PAYHERE_SANDBOX` to `false` for this demo.

#### Render (optional)

| Variable | Notes |
| --- | --- |
| `PAYHERE_MERCHANT_ID`, `PAYHERE_MERCHANT_SECRET` | Sandbox credentials only |
| `PAYHERE_API_APP_ID`, `PAYHERE_API_APP_SECRET` | Optional Merchant API access |
| `PAYHERE_SANDBOX` | Must remain `true` |
| `ADMIN_ALERT_EMAILS` | No effect while `ADMIN_EMAIL_ALERTS_ENABLED=false` |
| `SMTP_*` | Not usable on Render Free; leave unset |

#### Vercel

| Variable | Value |
| --- | --- |
| `VITE_API_URL` | Render HTTPS URL, no trailing slash, set for Production |

#### Local computer only (not Render)

| Variable | Purpose |
| --- | --- |
| `MIGRATION_DATABASE_URL` | Neon **direct** URL for Alembic |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Used only by the one-time `seed_admin` run |

### Safe migrations and admin seeding

- Render Free has no pre-deploy command and no shell. Run
  `alembic upgrade head` from your computer against the direct Neon URL.
- Never run `python -m app.seed` automatically or against an existing database.
- Run `python -m app.seed_admin` once, then remove the admin password from
  your temporary shell environment. The admin account is stored in Neon.
- Neon Free keeps only a short restore history (6 hours) and one manual
  snapshot. Export important data before destructive changes.

### Free-tier warnings to plan for

- Render sleeps after 15 minutes; the first request may take about a minute.
- Render has 750 instance hours per month; sleeping does not consume hours.
- Render’s filesystem is temporary; do not store product images there.
- Neon suspends compute after 5 minutes; the first request may be slow.
- Neon Free has 1 GB storage and 100 CU-hours per project per month.
- Render Free blocks all outbound SMTP, so email features are unavailable.
- Vercel Hobby is for non-commercial personal projects.
- PayHere is sandbox-only; online payments require sandbox credentials.

### PostgreSQL compatibility notes

- Use the `postgresql+psycopg://` SQLAlchemy prefix; `postgres://` is not
  accepted by SQLAlchemy 2.
- Neon requires TLS; keep `sslmode=require`.
- The admin-notification boolean default uses the PostgreSQL boolean literal
  `false`, so fresh migrations work on PostgreSQL and SQLite.
- Existing SQLite databases are unaffected; this project does not migrate
  SQLite data into Neon. Start production from an empty Neon database and
  run `alembic upgrade head`.

## 1. Prepare the database

Create a PostgreSQL database and copy its connection URL. Use the psycopg 3
driver prefix:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Run migrations from the backend directory:

```bash
cd backend
python -m alembic upgrade head
```

Render Free has no pre-deploy command or shell, so run migrations from your
computer with the Neon **direct** URL in `MIGRATION_DATABASE_URL`. Paid Render
services can use `python -m alembic upgrade head` as the pre-deploy command.
Do not run `python -m app.seed` in production; it is demo catalog data. Seed
your real catalog through the admin panel or with a data-import script.

## 2. Deploy the backend

### Render / Railway (native Python)

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*`
- Health check path: `/health/ready`
- Release/pre-deploy: paid services only; Render **Free** has no pre-deploy
  command, so run `alembic upgrade head` locally against the Neon direct URL.

The proxy flags let Uvicorn read Render’s `X-Forwarded-Proto` header so
HTTPS detection and HSTS work correctly behind the platform proxy.

### Docker

A `backend/Dockerfile` is included:

```bash
docker build -t furzy-api ./backend
docker run --env-file backend/.env -p 8000:8000 furzy-api
```

Uploaded images are stored in PostgreSQL, so no uploads volume is required.
A volume is only useful if you rely on the local filesystem fallback. Run
`python -m alembic upgrade head` before starting a new release/container. The
image includes a `HEALTHCHECK` against `/health/ready`.

### Health checks and smoke tests

- `GET /health/live` is a process liveness check with no database access.
- `GET /health/ready` checks database connectivity and uploads-directory
  writability. It returns `503` when either check fails.
- Configure the hosting platform's health check path as `/health/ready`.
  The included `render.yaml` already sets this.
- After deployment, run:
  ```bash
  cd backend
  SMOKE_ADMIN_EMAIL=... SMOKE_ADMIN_PASSWORD=... \
    python -m app.smoke_test --base-url https://api.example.com
  ```
  The smoke test checks liveness, readiness, catalog, payment config, and admin
  login/identity/dashboard when credentials are available. It never prints
  credentials or tokens. Use `--skip-admin` for public checks only.
- `APP_ENV=production` rejects a weak/default `JWT_SECRET` and a wildcard
  `FRONTEND_ORIGINS` at startup.
- Validate the complete production configuration before deploying:
  ```bash
  cd backend
  APP_ENV=production python -m app.check_production
  ```
  The command fails on a SQLite database URL, unsafe secrets/CORS, missing
  PayHere checkout credentials, a missing SMTP sender, or an unwritable uploads
  directory. It warns about sandbox mode, missing Merchant API credentials, and
  a missing database SSL parameter. It never prints secret values.
- For the free demo, use `python -m app.check_production --free-demo`. Missing
  SMTP, admin-email, and PayHere checkout credentials are downgraded to
  warnings because email is unavailable on Render Free and online payments are
  optional.

### Required environment variables

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | PostgreSQL URL with `postgresql+psycopg://`; use the Neon pooled URL when available |
| `MIGRATION_DATABASE_URL` | Optional direct/non-pooled PostgreSQL URL used only by Alembic; recommended with Neon |
| `APP_ENV` | Set to `production` in production; mock payments, weak/default JWT secrets, and wildcard CORS origins are rejected at startup there |
| `JWT_SECRET` | Long random value, for example `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `FRONTEND_ORIGINS` | Comma-separated production frontend origins, no trailing slash |
| `UPLOADS_DIR` | Local fallback/cache directory; uploaded images are stored in PostgreSQL. On Render Free use `/tmp/furzy-uploads` |
| `SHIPPING_FEE_LKR` | Fallback flat checkout shipping fee when no active shipping method is configured |
| `RETURN_WINDOW_DAYS` | Days after delivery in which customers can request a return (default 30); `0` disables the deadline |
| `RETURN_POLICY_TEXT` | Customer-facing return-condition text returned by `/returns/policy` |
| `ONLINE_PAYMENT_RESERVATION_MINUTES` | Unpaid online order stock reservation window; `0` disables expiry |
| `STOCK_RESERVATION_SWEEP_ENABLED` | In-process reservation sweeper; set `false` if using the cron command |
| `STOCK_RESERVATION_SWEEP_SECONDS` | Sweeper interval, minimum 10 seconds |
| `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Only needed for the one-time admin seed command |
| `SMTP_HOST` | Optional SMTP server for order, return, account, and admin alert emails; leave blank to disable |
| `SMTP_PORT` | SMTP port, commonly `587` |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | SMTP credentials, supplied through the host's secret manager |
| `SMTP_FROM_EMAIL` | From address used for notifications |
| `SMTP_USE_TLS` | `true` for STARTTLS on port 587 |
| `ADMIN_EMAIL_ALERTS_ENABLED` | Email a copy of new-order, new-return, and low-stock alerts; defaults to `true` when SMTP is configured |
| `ADMIN_ALERT_EMAILS` | Optional comma-separated alert recipients; defaults to every active admin account |
| `EMAIL_VERIFICATION_REQUIRED` | Require customers to verify their email before signing in; default `false` |
| `EMAIL_VERIFICATION_TOKEN_HOURS` | Verification link lifetime in hours (default 48) |
| `PASSWORD_RESET_TOKEN_MINUTES` | Password reset link lifetime in minutes (default 60) |
| `REVIEW_MODERATION_ENABLED` | Hold new and edited reviews as pending until an admin publishes them; default `false` |
| `PAYMENT_PROVIDER` | `disabled`, `mock`, or `payhere`; use `payhere` in production |
| `PAYMENT_CURRENCY` | `LKR` |
| `PAYHERE_MERCHANT_ID`, `PAYHERE_MERCHANT_SECRET` | PayHere merchant credentials, kept in the secret manager |
| `PAYHERE_API_APP_ID`, `PAYHERE_API_APP_SECRET` | Optional PayHere Merchant API key for retrieval/refund automation |
| `PAYHERE_API_TIMEOUT_SECONDS` | Merchant API request timeout, default 10 |
| `PAYHERE_SANDBOX` | `true` for sandbox testing, `false` for live payments |
| `FRONTEND_BASE_URL` | Public frontend URL used for PayHere return/cancel redirects |
| `BACKEND_PUBLIC_URL` | Public HTTPS API URL used to build the PayHere notify URL |
| `PAYMENT_MOCK_ENABLED` | Must remain `false` in production |

Generate the admin account once, after migrations:

```bash
python -m app.seed_admin
```

`seed_admin` refuses missing, invalid, placeholder, or known-default values.
It never recreates the old development admin account. For the free demo, run
it locally with temporary environment variables so the admin password never
enters Render. On a paid host, remove the admin password from the runtime
environment after seeding.

Do not commit `backend/.env`. It is ignored by Git and must be supplied through
the host's secret manager.

Order confirmation and status emails are sent in the background after the
database transaction succeeds. If SMTP is not configured, sending is skipped
and logged; email failures never fail the order itself. Use an app-specific
SMTP password rather than a mailbox password where the provider supports it.

> **Render Free:** outbound SMTP ports 25, 465, and 587 are blocked. Leave
> `SMTP_*` unset for the free demo. Email-dependent features are skipped, and
> `EMAIL_VERIFICATION_REQUIRED` must remain `false`. Do not crash-test the
> deployment by enabling SMTP without a paid instance or an HTTPS email API.

When SMTP is configured, the same service sends:

- admin alert copies for new orders, new return requests, and low-stock
  crossings (to `ADMIN_ALERT_EMAILS`, or every active admin account);
- customer email verification links when `EMAIL_VERIFICATION_REQUIRED=true`
  (or optionally on registration when verification is not enforced);
- single-use password reset links from `/auth/password/forgot`.

Verification and reset links point at `FRONTEND_BASE_URL`. The API stores only
token hashes, and a successful password reset invalidates every access and
refresh token issued before it. `EMAIL_VERIFICATION_REQUIRED=true` without SMTP
configuration logs a startup warning and leaves customers unable to verify;
configure SMTP first.

Set `REVIEW_MODERATION_ENABLED=true` to make new and edited reviews pending by
default. Admins approve, reject, or delete them from the Reviews page; only
published reviews count toward storefront ratings and averages.

### Uploads and multiple instances

Admin-uploaded product images are stored in PostgreSQL and served from
`/uploads/<filename>`, so they survive Render restarts, redeploys, and free-tier
sleep. `UPLOADS_DIR` is only a local fallback/cache for legacy files and
development; on Render Free it points to `/tmp/furzy-uploads`, which is
ephemeral. Database-backed uploads are shared by multiple API instances, but
they count toward the Neon storage limit. For a large catalog, use S3,
Cloudinary, or another object store instead.

### Rate limiting

Login and password-reset rate limiting are in-memory and per process. They
protect the common single-instance deployment. For multiple API workers or
instances, back the limiters with Redis or an edge rate-limit service.

## 3. Deploy the frontend

### Vercel

1. Import the repository.
2. Set the project root to `frontend`.
3. Framework preset: Vite; install command `npm ci`; build command
   `npm run build`; output `dist`. These are also set in
   `frontend/vercel.json`.
4. Set Node.js to 22 (or newer); the project requires `>=22.12.0`.
5. Add `VITE_API_URL=https://your-api-host` (no trailing slash) to the
   Production environment, and to Preview if preview builds should call the
   API. Vite embeds this value at build time, so redeploy after changing it.
   The Vite config deliberately fails a Vercel build that is missing this
   variable rather than shipping a build that calls localhost.
6. Deploy. `frontend/vercel.json` rewrites SPA routes such as `/orders/12`
   and `/admin/orders/3` to `index.html`, and adds security/cache headers.
7. Add the exact Vercel origin to the backend `FRONTEND_ORIGINS`. Preview
   deployments use different domains; add each preview origin you need or
   test against the production domain.

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
  API and Vite, runs the API smoke checks, installs Chromium, and runs the
  Playwright purchase journey plus the admin-page smoke test.

No production secrets are needed in CI; the workflow uses disposable test
values.

## 5. Running the E2E suite locally

Use a disposable database so the test's order/customer records do not touch
your development data:

```bash
cd backend
# Set DATABASE_URL to a throwaway SQLite file, ADMIN_* to test values,
# APP_ENV=test, PAYMENT_PROVIDER=mock, PAYMENT_MOCK_ENABLED=true, and
# STOCK_RESERVATION_SWEEP_ENABLED=false, then:
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

The tests skip themselves unless `E2E_DISPOSABLE_DB=1` or `CI=true` is set,
because they create records. The purchase journey deletes the product and
coupon it creates; reviews and wishlist entries are removed with the product.
The online-payment step requires `PAYMENT_PROVIDER=mock` and
`PAYMENT_MOCK_ENABLED=true` on the disposable backend. The admin smoke test
checks `/health/ready` and loads the dashboard, orders, customers,
notifications, returns, refunds, reports, product-performance, inventory, and
catalog-import and shipping-method pages.

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

## 6. PayHere online payments

The application supports Cash on Delivery and an optional PayHere hosted
checkout. Card details are entered only on PayHere's hosted page; this
application stores provider references and payment status, never card data.

### Configuration

1. Create a PayHere merchant account and obtain sandbox credentials first.
2. Set these values through the host's secret manager:

```text
PAYMENT_PROVIDER=payhere
PAYMENT_CURRENCY=LKR
PAYHERE_MERCHANT_ID=...
PAYHERE_MERCHANT_SECRET=...
PAYHERE_API_APP_ID=...
PAYHERE_API_APP_SECRET=...
PAYHERE_SANDBOX=true
FRONTEND_BASE_URL=https://your-frontend-host
BACKEND_PUBLIC_URL=https://your-api-host
PAYMENT_MOCK_ENABLED=false
APP_ENV=production
```

`APP_ENV=production` is a hard guard: startup fails if mock payment mode is
enabled or `PAYMENT_PROVIDER=mock`. Keep `PAYMENT_MOCK_ENABLED=false`.

Validate the configuration and Merchant API key without exposing secrets:

```bash
cd backend
python -m app.payhere_check --check-api
```

After a sandbox checkout has produced a payment reference, retrieve it too:

```bash
python -m app.payhere_check --check-api \
  --reference "YOUR-ORDER-REFERENCE" --amount 2450
```

The command checks the provider selection, checkout credentials, mock guard,
Merchant API key, and notify URL, then reports the provider status/amount/
currency for the reference. It does not replace the browser-level sandbox
checkout and signed-notification test below.

3. The backend builds the `notify_url` as
   `BACKEND_PUBLIC_URL/payments/payhere/notify`. It must be publicly reachable
   over HTTPS for PayHere to deliver signed notifications. For local sandbox
   testing, expose the backend with a tunnel such as ngrok.
4. Checkout redirects to PayHere. The return/cancel URLs point back to
   `FRONTEND_BASE_URL/orders/{id}`.
5. Verify a sandbox payment end to end: order is created as `payment_status =
   pending`, PayHere notification is verified, order/payment become `paid`,
   and the customer/admin see the updated status.
6. Only after sandbox verification, switch `PAYHERE_SANDBOX=false` and use live
   credentials.

The webhook verifies the PayHere `md5sig`, merchant ID, amount, and currency
before changing any payment. Success, failure, cancellation, and chargeback
notifications are idempotent; duplicate notifications do not duplicate state
or events. A paid payment can transition to `chargedback`; other later failure
notifications do not downgrade it. Payment attempts and audit events are kept
for admin history.

Failed online payments can be retried from the order detail page until the
reservation expires. Online orders cannot be marked delivered until their
payment status is `paid`.

### Merchant API reconciliation and refunds

For automatic verification and refunds, create a PayHere API key under
Settings → API Keys with the required Automated Charging/Refund permissions.
Whitelist the backend domain and, for live calls, ask PayHere support to
allowlist the server IP. Set `PAYHERE_API_APP_ID` and
`PAYHERE_API_APP_SECRET`; the checkout merchant ID/secret alone are not enough.

- Admin “Verify with PayHere” uses the Retrieval API by payment reference and
  validates provider amount/currency before applying a status.
- Admin refunds can be processed through the Refund API; full/partial amounts
  are validated against the payment's remaining refundable balance.
- If API credentials or provider access are unavailable, use the manual
  reconciliation/refund records. The UI states when provider processing is
  unavailable.
- Refund and return records retain the admin, amount, reason, status, provider
  reference, and timestamps.

Full refunds set the payment/order payment status to `refunded`; partial
refunds remain recorded against a paid payment. Dashboard revenue is net of
completed refunds: gross revenue includes delivered orders that are paid or
fully refunded, completed refunds are subtracted, pending/processing refunds
are reported separately, and chargedback orders are excluded. The admin
Reports page provides the same figures with date filters and daily/monthly
grouping. The product-performance report uses delivered paid/refunded order
line items, completed returns for return rates, and current active stock for
stock value. Customer self-service returns are
item-level: customers choose a structured reason and item quantities on a
delivered order and can cancel a pending request. Return requests are rejected
after `RETURN_WINDOW_DAYS` from the recorded delivery timestamp; set `0` to
disable the deadline. The policy text and reason list are served at
`/returns/policy`. Admins approve or reject requests; marking an approved
return completed restocks the returned variant quantities exactly once. Admins
can link an existing refund record to an approved or completed return. Status
emails are sent for requested, approved, rejected, completed, and cancelled
returns when SMTP is configured.

PayHere may require outbound IP allowlisting for live Merchant API calls.
Render services share regional outbound ranges by default; dedicated
outbound IPs are a workspace feature. If PayHere cannot allowlist the shared
ranges, use the manual reconciliation/refund workflow or an external
static-IP proxy. Checkout notifications are inbound HTTPS and do not depend
on the outbound IP.

### Stock reservation expiry

Unpaid online orders reserve stock. `ONLINE_PAYMENT_RESERVATION_MINUTES`
controls the window (default 30; `0` disables expiry). The in-process sweeper
runs every `STOCK_RESERVATION_SWEEP_SECONDS` while the API is running. If your
host runs many workers or you prefer an external scheduler, disable the
in-process sweeper and run this command periodically:

```bash
cd backend
python -m app.expire_reservations
```

Expiry cancels the order, releases reserved stock and coupon usage exactly
once, and marks pending/failed payment attempts cancelled with an audit event.
Order/payment row locking prevents duplicate releases and limits overselling
on PostgreSQL.

### Inventory audit and low-stock alerts

Every variant has a `low_stock_threshold` (default `5`) that can be edited in
the admin product editor. The admin Inventory page lists active variants at or
below their threshold and supports manual stock adjustments with a required
reason. Stock movements are recorded for initial stock, order placement, order
cancellation, reservation expiry, return restocking, variant removal, product
deletion, and manual adjustments. Each movement snapshots the product name,
size, color, and SKU, so the history remains readable after a product or
variant is deleted. Movement history is available at:
`GET /admin/inventory/movements`.

The rollout migration records each existing variant's current stock as an
opening `initial_stock` balance. Order, cancellation, and return paths lock
variant rows before changing stock, so movement before/after values remain
consistent. Manual adjustments reject changes that would make stock negative.

### Manual payment reconciliation

Automatic PayHere lookup requires the Merchant API credentials described
above. If they are not configured or a notification is missed, verify the
transaction in the PayHere dashboard and use the admin Order detail →
Payment history form, or:

```text
POST /admin/orders/{order_id}/payments/{payment_id}/reconcile
```

The admin endpoint requires a note and a PayHere transaction ID for a paid or
chargedback result. It records the admin and note in the payment event history.
Refreshing a customer order only reloads local state; it does not query
PayHere.

### Refunds and cancellation

Refunds can be recorded manually or processed through the PayHere Refund API
when `PAYHERE_API_APP_ID`/`PAYHERE_API_APP_SECRET` are configured and the API
key has the required permissions. Full and partial refunds are validated
against the payment's remaining refundable balance; full refunds set the
payment and order to `refunded`.

If an order paid online is cancelled, the order is cancelled and stock/coupon
usage is restored, but the payment remains `paid`; process the refund through
the admin refund workflow or the PayHere dashboard. Never enable
`PAYMENT_PROVIDER=mock` in production: it allows test-only completion of online
orders.

### Mock mode

`PAYMENT_PROVIDER=mock` with `PAYMENT_MOCK_ENABLED=true` is for local
development and CI only. It exercises the same order/payment state transitions
without money or provider credentials, and the frontend labels it as test
online payment.

## 7. Production security checklist

- [ ] Strong `JWT_SECRET` and a new admin password; no `.env` in Git.
- [ ] Vercel Hobby is used for a non-commercial personal/university demo.
- [ ] `FRONTEND_ORIGINS` limited to the real frontend origin(s).
- [ ] `FRONTEND_BASE_URL` and `BACKEND_PUBLIC_URL` are the public HTTPS URLs.
- [ ] HTTPS enforced by the host; HSTS is sent for HTTPS requests.
- [ ] Database backups and SSL enabled.
- [ ] `DATABASE_URL` uses Neon’s pooled URL (if used) with `sslmode=require`.
- [ ] `MIGRATION_DATABASE_URL` uses Neon’s direct URL for Alembic.
- [ ] Render Blueprint uses the **free** plan, has no disk, and sets `UPLOADS_DIR=/tmp/furzy-uploads`.
- [ ] Render health check is `/health/ready`; migrations were run locally because pre-deploy is unavailable on Free.
- [ ] Render `autoDeployTrigger` is intentional (`off` in the committed Blueprint); enable deployment when ready.
- [ ] Vercel `VITE_API_URL` points at the Render URL and the frontend has been redeployed after the value was set.
- [ ] Uploaded product images are stored in PostgreSQL and survive a Render sleep/redeploy.
- [ ] `UPLOADS_DIR` is understood to be a temporary local fallback, not durable storage.
- [ ] Email is intentionally disabled for the free demo (no SMTP; `EMAIL_VERIFICATION_REQUIRED=false`).
- [ ] `EMAIL_VERIFICATION_REQUIRED`, `REVIEW_MODERATION_ENABLED`, and `ADMIN_EMAIL_ALERTS_ENABLED` are set intentionally for the demo.
- [ ] `PAYHERE_SANDBOX=true`, `PAYMENT_PROVIDER=payhere`, and `PAYMENT_MOCK_ENABLED=false`; live mode was never enabled.
- [ ] PayHere sandbox credentials (if supplied) are stored in Render's environment and never committed.
- [ ] Return workflow reviewed: item-level requests and admin completion before restocking.
- [ ] Review moderation policy reviewed (enable the queue, or confirm immediate publishing), and the admin Reviews page loads.
- [ ] Order activity timeline checked on a test order after status changes, a detail edit, and a return.
- [ ] Inventory low-stock thresholds reviewed per variant and the stock-movement audit history checked after a test order, cancellation, and return.
- [ ] `APP_ENV=production`.
- [ ] `BACKEND_PUBLIC_URL/payments/payhere/notify` reachable over HTTPS when PayHere sandbox is enabled.
- [ ] Render sleep (15 minutes) and Neon autosuspend (5 minutes) are understood; cold starts are accepted for the demo.
- [ ] Stock reservation expiry is understood to run only while the free service is awake.
- [ ] Admin account was seeded locally; `ADMIN_PASSWORD` is not stored in Render.
- [ ] Demo catalog seed (`python -m app.seed`) was never run.
- [ ] Host health check points to `/health/ready`; the included Docker health check is active if using the image.
- [ ] PostgreSQL migrations were applied to a fresh Neon database with `alembic upgrade head` and completed without SQLite-specific errors.
- [ ] `python -m app.smoke_test --base-url https://api.example.com` passes after deployment.
- [ ] `APP_ENV=production` starts successfully with the final JWT secret and CORS origins.
- [ ] `APP_ENV=production python -m app.check_production --free-demo` passes with only expected warnings.
- [ ] Dependencies updated and `npm audit` / `pip-audit` reviewed.
- [ ] `python -m pytest` and `npm test` green before deployment.
- [ ] `npm run build` succeeds with the production `VITE_API_URL`.
- [ ] A Render restart/sleep keeps uploaded images (database storage verified).
- [ ] Neon's 1 GB storage / 100 CU-hours and 6-hour restore window are understood; a rollback plan exists.

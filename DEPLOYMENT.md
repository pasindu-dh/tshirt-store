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

## Render + Vercel + Neon blueprint

The repository includes a `render.yaml` Blueprint and an updated
`frontend/vercel.json` for this stack.

### What the Blueprint creates

- A Python web service named `furzy-api`, root directory `backend`
- Python `3.13.16`
- Build: `pip install -r requirements.txt`
- Pre-deploy: `python -m alembic upgrade head`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*`
- Health check: `/health/ready`
- Persistent disk: `furzy-uploads`, mounted at `/var/data/uploads`
- `UPLOADS_DIR=/var/data/uploads`

The service uses the paid `0.5c-512mb` plan on purpose. Render free web
services cannot attach a persistent disk, and since September 2025 free web
services also block outbound SMTP ports 465 and 587. Port 25 is blocked on
all plans. Use a paid instance for both uploads and email.

### Required accounts and values

1. A Neon project with a database and two connection strings:
   - **Pooled** URL for `DATABASE_URL` (application runtime)
   - **Direct** URL for `MIGRATION_DATABASE_URL` (Alembic)
2. A Render Blueprint created from this repository.
3. A Vercel project with root directory `frontend`.
4. SMTP credentials for a provider that supports port 587 or 465.
5. PayHere sandbox credentials for initial online-payment verification.

Use the SQLAlchemy URL prefix `postgresql+psycopg://` for both Neon URLs.
Keep `sslmode=require` in both. Add the Neon database, user, and password
placeholders exactly as Neon provides them; never commit the URLs.

### Deployment order

1. Create the Neon database. Copy both the pooled and direct URLs.
2. Create the Render Blueprint. Creating a Blueprint triggers its first
   deploy, so do this only when you are ready; `autoDeployTrigger: "off"` in
   the Blueprint only disables later automatic deploys. Render reads
   `render.yaml` and prompts for every `sync: false` variable:
   - `DATABASE_URL` — Neon pooled URL
   - `MIGRATION_DATABASE_URL` — Neon direct URL
   - `FRONTEND_ORIGINS` — set to the final Vercel origin, for example
     `https://furzy.vercel.app` (no trailing slash). You can set this after
     the first frontend deploy and redeploy the API.
   - `FRONTEND_BASE_URL` — same Vercel origin
   - `BACKEND_PUBLIC_URL` — the Render service URL, for example
     `https://furzy-api.onrender.com`
   - SMTP host, port, username, password, and from address
   - PayHere merchant and Merchant API credentials
   - Optional `ADMIN_ALERT_EMAILS`
3. Let Render run the build and pre-deploy migration. The first deploy can
   start even if PayHere credentials are not filled in yet, but online
   payments stay disabled until they are.
4. Add `ADMIN_EMAIL` (non-secret) and `ADMIN_PASSWORD` (secret) as temporary
   Render environment variables, open the Render Shell, and seed the admin
   once:
   ```bash
   python -m app.seed_admin
   ```
   Then remove `ADMIN_PASSWORD` from the Render environment. Keep
   `ADMIN_EMAIL` because `check_production` uses it as a launch check. Do
   **not** run `python -m app.seed`; that is demo catalog data.
5. In Vercel, import the repository, set the root directory to `frontend`,
   and add `VITE_API_URL=https://furzy-api.onrender.com` to Production (and
   Preview if needed). Redeploy after changing it because Vite embeds the
   value at build time.
6. After the Vercel domain is known, set `FRONTEND_ORIGINS` and
   `FRONTEND_BASE_URL` on Render to the exact Vercel origin(s), then redeploy
   the API.
7. Set `BACKEND_PUBLIC_URL` to the Render URL. PayHere notifications will be
   sent to:
   `https://furzy-api.onrender.com/payments/payhere/notify`.
8. Run the production checks from the Render Shell:
   ```bash
   APP_ENV=production python -m app.check_production
   python -m app.smoke_test --base-url https://furzy-api.onrender.com
   ```

### Neon and migrations

Neon’s pooled endpoint runs PgBouncer in transaction mode. Schema migrations
should use the direct endpoint, so keep the direct URL in
`MIGRATION_DATABASE_URL`. `alembic/env.py` uses that URL when present and
falls back to `DATABASE_URL` otherwise. The application keeps using the
pooled URL in `DATABASE_URL`.

The application engine uses `pool_pre_ping` and a five-minute connection
recycle to survive Neon idle disconnects. A single API instance uses a small
pool; tune `pool_size`/`max_overflow` in `app/database.py` if you add
concurrency.

If Neon is suspended, its first connection can take several seconds. Render’s
health check times out after five seconds, so a cold database can make
`/health/ready` fail. Keep the database active, or use a Neon compute setting
that does not suspend, if you see readiness restarts.

### Render disks and uploads

Only files written under `/var/data/uploads` survive deploys and restarts.
The health check verifies that directory is writable, and uploads are served
from `/uploads`. Render snapshots disks daily and retains seven days of
snapshots, but a disk-backed service cannot scale to multiple instances and
deploys stop the old instance before starting the new one. For long-term
durability or multiple instances, copy uploads to S3/Cloudinary and add an
object-storage adapter.

### PostgreSQL compatibility notes

- Use the `postgresql+psycopg://` SQLAlchemy prefix; `postgres://` is not
  accepted by SQLAlchemy 2.
- Neon requires TLS; keep `sslmode=require`.
- The admin-notification boolean default was corrected to a SQL boolean
  default (`false`) so fresh PostgreSQL migrations accept it. SQLite accepts
  the same expression.
- Existing SQLite databases are unaffected; this project does not migrate
  SQLite data into Neon. Start production from an empty Neon database and
  run `alembic upgrade head`.

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
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*`
- Release command: `python -m alembic upgrade head`
- Health check path: `/health/ready`

The proxy flags let Uvicorn read Render’s `X-Forwarded-Proto` header so
HTTPS detection and HSTS work correctly behind the platform proxy.

### Docker

A `backend/Dockerfile` is included:

```bash
docker build -t furzy-api ./backend
docker run --env-file backend/.env -p 8000:8000 \
  -v furzy-uploads:/app/uploads furzy-api
```

Run `python -m alembic upgrade head` before starting a new release/container.
The image includes a `HEALTHCHECK` against `/health/ready`.

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

### Required environment variables

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | PostgreSQL URL with `postgresql+psycopg://`; use the Neon pooled URL when available |
| `MIGRATION_DATABASE_URL` | Optional direct/non-pooled PostgreSQL URL used only by Alembic; recommended with Neon |
| `APP_ENV` | Set to `production` in production; mock payments, weak/default JWT secrets, and wildcard CORS origins are rejected at startup there |
| `JWT_SECRET` | Long random value, for example `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `FRONTEND_ORIGINS` | Comma-separated production frontend origins, no trailing slash |
| `UPLOADS_DIR` | Directory on a persistent disk, for example `/var/data/uploads` |
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
It never recreates the old development admin account. Remove the admin
password from the runtime environment after seeding if your host supports
separate release/run environments.

Do not commit `backend/.env`. It is ignored by Git and must be supplied through
the host's secret manager.

Order confirmation and status emails are sent in the background after the
database transaction succeeds. If SMTP is not configured, sending is skipped
and logged; email failures never fail the order itself. Use an app-specific
SMTP password rather than a mailbox password where the provider supports it.

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

`UPLOADS_DIR` must be writable and persistent. On platforms with an ephemeral
filesystem (for example, many serverless deployments), mount a persistent disk
or add an object-storage adapter. If you run more than one API instance, local
disk uploads are not shared; use Cloudinary, S3, or another shared store.

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
- [ ] `FRONTEND_ORIGINS` limited to the real frontend origin(s).
- [ ] `FRONTEND_BASE_URL` and `BACKEND_PUBLIC_URL` are the public HTTPS URLs.
- [ ] HTTPS enforced by the host; HSTS is sent for HTTPS requests.
- [ ] Database backups and SSL enabled.
- [ ] `DATABASE_URL` uses Neon’s pooled URL (if used) with `sslmode=require`.
- [ ] `MIGRATION_DATABASE_URL` uses Neon’s direct URL for Alembic.
- [ ] Render Blueprint uses a paid plan with the uploads disk mounted at `/var/data/uploads` and `UPLOADS_DIR` matching.
- [ ] Render health check is `/health/ready`; pre-deploy runs `python -m alembic upgrade head`.
- [ ] Render `autoDeployTrigger` is intentional (`off` in the committed Blueprint); enable deployment when launch is approved.
- [ ] Vercel `VITE_API_URL` points at the Render URL and the frontend has been redeployed after the value was set.
- [ ] Uploads directory private to the app and backed up.
- [ ] SMTP password stored as a secret; sender domain configured and tested for order, verification, reset, and admin alert email.
- [ ] `EMAIL_VERIFICATION_REQUIRED`, `REVIEW_MODERATION_ENABLED`, and `ADMIN_EMAIL_ALERTS_ENABLED` set intentionally for launch.
- [ ] Password reset, email verification, and admin alert emails tested end to end with a real mailbox.
- [ ] PayHere merchant secret stored as a secret; sandbox disabled for live.
- [ ] PayHere Merchant API key restricted to the required permissions/domain/IP.
- [ ] Return workflow reviewed: item-level requests, admin completion before restocking, and return status emails.
- [ ] Review moderation policy reviewed (enable the queue, or confirm immediate publishing), and the admin Reviews page loads.
- [ ] Order activity timeline checked on a test order after status changes, a detail edit, and a return.
- [ ] Inventory low-stock thresholds reviewed per variant and the stock-movement audit history checked after a test order, cancellation, and return.
- [ ] `APP_ENV=production`, `PAYMENT_PROVIDER=payhere`, and `PAYMENT_MOCK_ENABLED=false`.
- [ ] `BACKEND_PUBLIC_URL/payments/payhere/notify` reachable over HTTPS.
- [ ] Stock reservation expiry configured and, if the in-process sweeper is disabled, a cron job runs `python -m app.expire_reservations`.
- [ ] Login rate limiting sized for your traffic or moved to Redis.
- [ ] Admin account verified with `python -m app.seed_admin` validation rules.
- [ ] `ADMIN_PASSWORD` removed from the runtime environment after the one-time admin seed.
- [ ] Demo catalog seed (`python -m app.seed`) was never run in production.
- [ ] Host health check points to `/health/ready`; the included Docker health check is active if using the image.
- [ ] PostgreSQL migrations were applied to a fresh Neon database with `alembic upgrade head` and completed without SQLite-specific errors.
- [ ] `python -m app.smoke_test --base-url https://api.example.com` passes after deployment.
- [ ] `APP_ENV=production` starts successfully with the final JWT secret and CORS origins, and fails with intentionally weak values.
- [ ] `APP_ENV=production python -m app.check_production` passes (warnings reviewed) before the release.
- [ ] Dependencies updated and `npm audit` / `pip-audit` reviewed.
- [ ] `python -m pytest` and `npm test` green before deployment.
- [ ] `npm run build` succeeds with the production `VITE_API_URL`.
- [ ] A Render deploy/restart keeps uploaded files (disk persistence verified).
- [ ] A rollback plan exists; migrations are backward-compatible and a Neon backup/snapshot is available.

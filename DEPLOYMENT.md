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
| `APP_ENV` | Set to `production` in production; `mock` payment mode is rejected at startup there |
| `JWT_SECRET` | Long random value, for example `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `FRONTEND_ORIGINS` | Comma-separated production frontend origins, no trailing slash |
| `UPLOADS_DIR` | Directory on a persistent disk, for example `/var/data/uploads` |
| `SHIPPING_FEE_LKR` | Optional checkout shipping fee |
| `ONLINE_PAYMENT_RESERVATION_MINUTES` | Unpaid online order stock reservation window; `0` disables expiry |
| `STOCK_RESERVATION_SWEEP_ENABLED` | In-process reservation sweeper; set `false` if using the cron command |
| `STOCK_RESERVATION_SWEEP_SECONDS` | Sweeper interval, minimum 10 seconds |
| `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Only needed for the one-time admin seed command |
| `SMTP_HOST` | Optional SMTP server for order emails; leave blank to disable |
| `SMTP_PORT` | SMTP port, commonly `587` |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | SMTP credentials, supplied through the host's secret manager |
| `SMTP_FROM_EMAIL` | From address used for order notifications |
| `SMTP_USE_TLS` | `true` for STARTTLS on port 587 |
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

The test skips itself unless `E2E_DISPOSABLE_DB=1` or `CI=true` is set,
because it leaves an order and customer account behind. It deletes the product
and coupon it creates; reviews and wishlist entries are removed with the
product. The online-payment step requires `PAYMENT_PROVIDER=mock` and
`PAYMENT_MOCK_ENABLED=true` on the disposable backend.

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
refunds remain recorded against a paid payment. Dashboard revenue excludes
fully refunded and chargedback delivered orders, but does not currently
subtract partial refunds from gross revenue. Customer self-service return
requests are not included; refunds/returns are recorded by admins.

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

### Manual payment reconciliation

Automatic PayHere lookup is not configured. If a notification is missed,
verify the transaction in the PayHere dashboard and use the admin Order detail
→ Payment history form, or:

```text
POST /admin/orders/{order_id}/payments/{payment_id}/reconcile
```

The admin endpoint requires a note and a PayHere transaction ID for a paid or
chargedback result. It records the admin and note in the payment event history.
Refreshing a customer order only reloads local state; it does not query
PayHere.

### Refunds and cancellation

There is no automated refund API integration. If an order paid online is
cancelled, the order is cancelled and stock/coupon usage is restored, but the
payment remains `paid`; process the refund in the PayHere dashboard or add a
provider refund workflow later. Never enable `PAYMENT_PROVIDER=mock` in
production: it allows test-only completion of online orders.

### Mock mode

`PAYMENT_PROVIDER=mock` with `PAYMENT_MOCK_ENABLED=true` is for local
development and CI only. It exercises the same order/payment state transitions
without money or provider credentials, and the frontend labels it as test
online payment.

## 7. Production security checklist

- [ ] Strong `JWT_SECRET` and a new admin password; no `.env` in Git.
- [ ] `FRONTEND_ORIGINS` limited to the real frontend origin(s).
- [ ] HTTPS enforced by the host; HSTS is sent for HTTPS requests.
- [ ] Database backups and SSL enabled.
- [ ] Uploads directory private to the app and backed up.
- [ ] SMTP password stored as a secret; sender domain configured and tested.
- [ ] PayHere merchant secret stored as a secret; sandbox disabled for live.
- [ ] PayHere Merchant API key restricted to the required permissions/domain/IP.
- [ ] `APP_ENV=production`, `PAYMENT_PROVIDER=payhere`, and `PAYMENT_MOCK_ENABLED=false`.
- [ ] `BACKEND_PUBLIC_URL/payments/payhere/notify` reachable over HTTPS.
- [ ] Stock reservation expiry configured and, if the in-process sweeper is disabled, a cron job runs `python -m app.expire_reservations`.
- [ ] Login rate limiting sized for your traffic or moved to Redis.
- [ ] Admin account verified with `python -m app.seed_admin` validation rules.
- [ ] Dependencies updated and `npm audit` / `pip-audit` reviewed.
- [ ] `python -m pytest` and `npm test` green before deployment.

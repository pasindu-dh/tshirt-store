# T-Shirt Store

A full-stack web application featuring an interactive React frontend and a robust Python FastAPI backend, designed to showcase an infinite scrolling gallery of T-shirts.

## 🚀 Tech Stack

### Frontend
- **React 19**
- **Vite** (for fast development and building)
- **Tailwind CSS v4** (for styling)
- **React Router DOM** (for routing)
- **React Infinite Scroll Component** (for seamless pagination)
- **TSParticles** (for dynamic and interactive background UI effects)
- **Axios** (for API requests)

### Backend
- **FastAPI** (High-performance Python web framework)
- **SQLAlchemy 2.0** + **Alembic** (ORM and database migrations)
- **SQLite** for local development (PostgreSQL-ready via `DATABASE_URL`)
- **PyJWT** + **pwdlib (Argon2)** (JWT authentication and password hashing)
- **Pydantic Settings** (Environment configuration)
- **Pillow** (Server-side image verification for admin uploads)
- **psycopg 3** (PostgreSQL driver for production)
- **Uvicorn** (ASGI server)
- **StaticFiles** (Local image serving)
- **SMTP** (Optional order confirmation/status emails via the standard library)
- **PayHere** (Optional hosted online checkout with signed notifications)
- **CORS Middleware** (Configured to allow frontend connections)
- **pytest + FastAPI TestClient** (Backend test suite)

## 📁 Project Structure

```
tshirt-store/
│
├── backend/              # FastAPI Python server
│   ├── app/
│   │   ├── main.py       # FastAPI application
│   │   ├── config.py     # Settings loaded from environment
│   │   ├── database.py   # Engine, session, and declarative Base
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── routers/      # Public and admin API routes
│   │   ├── services/     # Catalog, cart, order, coupon, review, and email logic
│   │   ├── utils/        # Slug helpers
│   │   ├── security.py   # Password hashing and JWT helpers
│   │   ├── rate_limit.py # Failed-login rate limiter
│   │   ├── dependencies.py # Current-user and admin-guard dependencies
│   │   ├── seed.py       # Sample catalog seed script
│   │   └── seed_admin.py # Admin account seed script
│   ├── alembic/          # Database migrations
│   ├── images/           # Static product images served by the backend
│   ├── uploads/          # Uploaded product images (runtime, git-ignored)
│   ├── tests/            # pytest suite (isolated temporary database)
│   ├── main.py           # Entry point for `uvicorn main:app`
│   ├── Dockerfile        # Production API image
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── frontend/             # React/Vite frontend application
│   ├── public/
│   ├── e2e/              # Playwright purchase-journey test
│   ├── src/              # React components, pages, API client, context
│   │   ├── test/         # Vitest setup
│   │   ├── utils/        # Cart and error helpers
│   │   └── pages/admin/  # Dashboard, orders, products, categories, and coupons
│   ├── package.json
│   ├── playwright.config.js
│   └── vite.config.js
│
├── .github/workflows/ci.yml
└── DEPLOYMENT.md
```

## 🛠️ Getting Started

### 1. Backend Setup

The backend serves the API and static images for the products.

1. Open a terminal and navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install the required Python packages (it is recommended to use a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```
3. Apply the database migrations:
   ```bash
   alembic upgrade head
   ```
4. Seed the catalog with sample categories and products:
   ```bash
   python -m app.seed
   ```
   Use `python -m app.seed --reset` to wipe the catalog and seed it again.
5. Create or update the admin account:
   ```bash
   python -m app.seed_admin
   ```
   The script reads `ADMIN_NAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` from `backend/.env`. Set these values before running it — the committed `.env.example` contains placeholders only. `ADMIN_PASSWORD` must be at least 8 characters. The script refuses to run when the email or password is missing, invalid, or set to a known default or placeholder value, and it will not create a default development admin automatically. Never commit `backend/.env` or real credentials.
6. Run the backend server:
   ```bash
   uvicorn main:app --reload --port 8005
   ```
   *The backend will be available at `http://127.0.0.1:8005`. You can view the interactive API documentation at `http://127.0.0.1:8005/docs`.*

   Allowed frontend origins default to `http://localhost:5173` and `http://127.0.0.1:5173`. Override them with the `FRONTEND_ORIGINS` environment variable (comma-separated). See `backend/.env.example` for all options. The SQLite database lives at `backend/store.db` and is git-ignored.

   Product images uploaded through the admin panel are stored in `backend/uploads/` (created automatically and git-ignored) and served from `/uploads`. Uploads are verified by Pillow: the file must actually contain a JPEG, PNG, or WebP image, not just claim that content type. Files are limited to 5 MB and 40 megapixels.

   Login attempts are rate-limited in memory (5 failed attempts per account and 20 per IP in a 15-minute window). Successful logins reset the account/IP counters. Multi-worker deployments should move this to Redis.

### 2. Frontend Setup

The frontend runs on Vite and communicates with the FastAPI backend.

1. Open a new terminal and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install the Node dependencies:
   ```bash
   npm install
   ```
3. (Optional) Copy `.env.example` to `.env` if your backend does not run on the default URL `http://127.0.0.1:8005`.
4. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The terminal will output the local URL (usually `http://localhost:5173`) where you can view the application.*

   Frontend routes: `/` (home), `/shop`, `/product/:slug`, `/about`, `/contact`, `/login`, `/register`, `/forbidden`, `/checkout` (signed-in), `/orders` and `/orders/:orderId` (signed-in), `/wishlist` (signed-in), and the admin area (`/admin`, `/admin/orders`, `/admin/orders/:orderId`, `/admin/products`, `/admin/products/new`, `/admin/products/:id/edit`, `/admin/categories`, `/admin/coupons`). The admin area requires the `admin` role.

## 🔗 API Endpoints

### Catalog (public)
- `GET /products`: Paginated product list.
  - Query parameters: `page`, `limit` (max 100), `search`, `category` (slug), `sort` (`newest`, `price_asc`, `price_desc`, `name`).
  - Returns the `X-Total-Count` header with the total number of matching products.
- `GET /products/{id}`: Product detail (active products only).
- `GET /products/slug/{slug}`: Product detail by slug (active products only), used by the storefront product page.
- `GET /categories`: List product categories.
- `GET /images/{filename}`: Serves static images for the T-shirts.
- `GET /`: Health check endpoint.

### Authentication
- `POST /auth/register`: Create a customer account and return access + refresh tokens.
- `POST /auth/login`: OAuth2 password-form login (`username` is the email). Also enables the **Authorize** button in `/docs`. Repeated failed attempts return `429` with `Retry-After`.
- `POST /auth/refresh`: Exchange a refresh token for a new token pair.
- `GET /auth/me`: Return the current authenticated user.

> The frontend silently refreshes an expired access token on a `401` and retries the request. If the refresh token is also invalid, the session is cleared and the user is signed out.

### Cart (authenticated)
> All cart endpoints require a bearer token. Guests keep their cart in localStorage and merge it after signing in.

- `GET /cart`: Current cart with line items, item count, subtotal, shipping fee, and total.
- `POST /cart/items`: Add a variant (`variant_id`, `quantity`); stock is enforced.
- `PUT /cart/items/{id}`: Set a line quantity.
- `DELETE /cart/items/{id}`: Remove a line.
- `DELETE /cart`: Empty the cart.
- `POST /cart/merge`: Merge guest cart items into the authenticated cart, capping quantities at available stock.

### Orders (authenticated)
> Requires a bearer token. Prices, shipping, and totals are computed server-side from the database, and stock is revalidated at checkout.

- `POST /orders`: Place an order from the server cart using the supplied contact/shipping details and `payment_method` (`cod` or `online`). An optional `coupon_code` applies a server-validated discount. Stock is decremented, line items are snapshotted, and the cart is cleared in one transaction. Online orders require a configured payment provider and receive a configurable reservation expiry.
- `GET /orders`: The signed-in customer's orders, newest first.
- `GET /orders/{id}`: One of the signed-in customer's orders, including reservation and stock-release state.

### Payments
- `GET /payments/config`: Public payment capability flags (`disabled`, `payhere`, or `mock`) without exposing secrets.
- `POST /payments/orders/{id}/session`: Authenticated owner creates a hosted-checkout session for an online order. PayHere returns the action URL and signed form fields; mock mode returns a local test session. Chargedback orders cannot be paid again.
- `POST /payments/orders/{id}/mock-complete`: Development/test-only completion endpoint; unavailable in production or under the PayHere provider.
- `POST /payments/payhere/notify`: PayHere server notification endpoint. Verifies the merchant signature, amount, and currency, then updates the payment/order idempotently. It records payment events and supports paid → chargedback transitions.
- `GET /admin/orders/{id}/payments`: Admin-only payment attempt history with references, transaction IDs, statuses, refunds, and audit events.
- `POST /admin/orders/{id}/payments/{payment_id}/reconcile`: Admin-only manual reconciliation for cases where automatic provider lookup is unavailable. Requires a verification note and a transaction ID for paid/chargedback results.
- `POST /admin/orders/{id}/payments/{payment_id}/reconcile-provider`: Admin-only PayHere Retrieval API verification. Requires PayHere Merchant API credentials; it validates provider amount/currency and records paid/chargedback/refunded outcomes.
- `GET /admin/orders/{id}/refunds`: Admin-only refund and return records.
- `POST /admin/orders/{id}/payments/{payment_id}/refunds`: Record a refund or return. Supports manual records or provider processing when the PayHere Refund API is configured.
- `PATCH /admin/orders/{id}/refunds/{refund_id}`: Update a pending/processing/failed refund, including marking it completed after manual processing.

### Reviews
- `GET /reviews/product/{id}`: Public review list with count and average rating for an active product.
- `POST /reviews/product/{id}`: Create the signed-in customer's review (`rating` 1–5, optional `title`/`comment`); one review per customer per product.
- `PUT /reviews/{id}`: Edit your own review.
- `DELETE /reviews/{id}`: Delete your own review; admins can delete any review for moderation.

### Wishlist (authenticated)
- `GET /wishlist`: The signed-in customer's saved products.
- `PUT /wishlist/items/{product_id}`: Save an active product (idempotent).
- `DELETE /wishlist/items/{product_id}`: Remove a saved product.

### Coupons
- `POST /coupons/preview`: Authenticated preview of a coupon against the server cart. Returns the discount and recalculated totals without consuming usage.
- Admin coupon CRUD is under `/admin/coupons`; see the Admin section.

### Admin
> All admin endpoints require `Authorization: Bearer <access_token>` for a user with the `admin` role. Requests without a token return `401`; customer tokens return `403`.

- `GET /admin/products`: Product list including inactive products.
- `GET /admin/products/{id}`: Full product detail, including inactive products.
- `POST /admin/products`: Create a product with images and size variants.
- `PUT /admin/products/{id}`: Update a product, its images, or its variants.
- `DELETE /admin/products/{id}`: Delete a product.
- `POST /admin/uploads`: Upload a product image using multipart form data (`file` field). Accepts JPEG, PNG, and WebP up to 5 MB; the actual image format is verified with Pillow. Returns `{ "url": "/uploads/<filename>" }`.
- `POST /admin/categories`: Create a category.
- `PUT /admin/categories/{id}`: Rename a category.
- `DELETE /admin/categories/{id}`: Delete an empty category.
- `GET /admin/orders`: Paginated order list with optional `status`, `search`, `date_from`, and `date_to` filters; returns `X-Total-Count`.
- `GET /admin/orders/{id}`: Full order detail for any customer order.
- `PATCH /admin/orders/{id}/status`: Advance an order through `pending → confirmed → shipped → delivered`, or cancel from `pending`/`confirmed`. Online orders must be paid before they can be delivered. Cancelling restores reserved stock/coupon usage once; delivering marks COD payment as paid. Status changes send an email when SMTP is configured.
- `GET /admin/orders/{id}/payments`: Payment attempts, references, provider transaction IDs, statuses, refund/return records, and event history.
- `POST /admin/orders/{id}/payments/{payment_id}/reconcile`: Record a manually verified paid/failed/cancelled/chargedback result. The admin and note are preserved in the payment event history.
- `POST /admin/orders/{id}/payments/{payment_id}/reconcile-provider`: Verify the payment against the PayHere Retrieval API and apply the provider-confirmed status.
- `POST /admin/orders/{id}/payments/{payment_id}/refunds` and `PATCH /admin/orders/{id}/refunds/{refund_id}`: Record refunds/returns, optionally process via the PayHere Refund API, and complete or fail them with an audit trail.
- `GET /admin/stats`: Dashboard aggregates — revenue from delivered orders, open/pending/delivered/cancelled counts, low-stock variants, and product/category totals.
- `GET/POST /admin/coupons` and `PUT/DELETE /admin/coupons/{id}`: Manage percentage or fixed-amount coupons with minimum subtotals, usage limits, active windows, and active/inactive state.

## 🛍️ Admin Panel

Sign in at `/login` with an admin account to manage the store:

- **Dashboard**: delivered revenue, open/pending orders, low-stock variants, order/product/category counts, and quick actions.
- **Orders**: search by order number/customer, filter by status and date range, paginate, and open order details.
- **Order detail**: review customer/shipping/payment details, items, totals, discounts, notes, payment attempts, PayHere references, transaction IDs, refunds/returns, and event history; confirm, ship, deliver, or cancel orders. Online orders cannot be delivered until payment is paid. Admins can verify payments through PayHere, record manual reconciliation, and record manual or provider-processed refunds/returns.
- **Cancellation and chargebacks**: cancellation restores stock and coupon usage once; paid cancellations keep the payment as paid for manual refund handling. Chargedback payments are shown as a distinct state.
- **Products**: search/filter/paginate, activate or deactivate, delete, and edit.
- **Product editor**: upload images (choose a primary image), set price, category and visibility, and manage size/color/SKU/stock variants.
- **Categories**: create, rename, and delete categories (a category with products cannot be deleted).
- **Coupons**: create percentage or fixed-amount coupons with minimum subtotals, usage limits, start/expiry windows, and active state; edit or delete them.
- Active products created in the admin panel appear on the storefront immediately.

## 🛒 Storefront

- **Shop** uses server-side search, category filtering, price/name sorting, and paginated infinite scrolling.
- Product cards open a product detail page at `/product/:slug` and include a wishlist heart.
- The detail page includes an image gallery, color and size selection, live stock status, a stock-aware add-to-cart button, a wishlist toggle, and customer reviews with average ratings and one-review-per-customer editing.
- Guests keep their cart in localStorage; after login or registration it is merged into the server-side cart. Signed-in customers keep their cart across sessions and devices. Expired access tokens are refreshed automatically.
- Checkout requires an account, validates prices and stock server-side, supports **Cash on Delivery** and optional **PayHere hosted online payment**, and accepts server-validated coupons. Online orders redirect to PayHere's secure checkout; the signed PayHere notification updates payment status. A flat shipping fee of LKR 350 is applied by default (configurable with `SHIPPING_FEE_LKR`).
- Unpaid online orders have a configurable reservation window (`ONLINE_PAYMENT_RESERVATION_MINUTES`). Expired orders are cancelled, their reserved stock is released exactly once, and pending payment attempts are closed.
- After ordering, customers see a confirmation and can review their orders at `/orders`. Order emails distinguish pending online payment from confirmed payment; a separate payment confirmation is sent only after server-side payment verification. Refund/return records are currently admin-managed; customer self-service return requests are not included. When SMTP is configured, status-update emails are also sent.

## 🧪 Testing

### Backend

The pytest suite uses an isolated temporary SQLite database and upload folder, so it never touches `backend/store.db`.

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

Coverage includes authentication and role guards, login rate limiting, catalog filters and slug lookup, cart stock caps and guest-cart merging, transactional order creation and stock decrement, coupon previews/discounts/usage rules, admin status transitions and cancellation restock, dashboard stats, reviews, wishlist privacy, upload validation, security headers, CORS, order date filters, mock online payments, PayHere signature/amount verification, chargebacks, duplicate/delayed notifications, stock reservation expiry, fulfillment guards, manual reconciliation, refund/return records, provider reconciliation/refund adapters, and payment email timing.

### Frontend

```bash
cd frontend
npm test          # Vitest + React Testing Library
npm run lint
npm run build
```

### End-to-end

The Playwright test drives a full guest-cart → login → checkout → coupon → online payment → order → review → wishlist → history journey and verifies that the access-token refresh interceptor recovers from an expired token. It needs a running backend with an admin account and the mock payment provider enabled.

```bash
cd frontend
npx playwright install chromium   # once
E2E_DISPOSABLE_DB=1 E2E_ADMIN_EMAIL=... E2E_ADMIN_PASSWORD=... npm run test:e2e
```

The disposable backend must be started with `PAYMENT_PROVIDER=mock` and `PAYMENT_MOCK_ENABLED=true` so the journey can exercise the online-payment UI. The test refuses to run unless `E2E_DISPOSABLE_DB=1` (or `CI=true`) is set, because it creates an order and a customer account. It deletes the product and coupon it creates. `E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD` override the admin credentials read from `backend/.env`. See [`DEPLOYMENT.md`](DEPLOYMENT.md) for running the suite against a disposable database.

## 🚢 Deployment

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the production checklist and step-by-step instructions for Render/Railway, PostgreSQL, Vercel/Netlify, Docker, CI, and uploads. GitHub Actions runs backend tests, frontend lint/unit/build, and the Playwright journey on every push and pull request.

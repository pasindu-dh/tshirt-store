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
- **Pydantic Settings** (Environment configuration)
- **Uvicorn** (ASGI server)
- **StaticFiles** (Local image serving)
- **CORS Middleware** (Configured to allow frontend connections)

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
│   │   ├── services/     # Catalog business logic
│   │   ├── utils/        # Slug helpers
│   │   └── seed.py       # Sample data seed script
│   ├── alembic/          # Database migrations
│   ├── images/           # Static product images served by the backend
│   ├── main.py           # Entry point for `uvicorn main:app`
│   └── requirements.txt
│
└── frontend/             # React/Vite frontend application
    ├── public/
    ├── src/              # React components, pages, API client, context
    ├── package.json
    └── vite.config.js
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
5. Run the backend server:
   ```bash
   uvicorn main:app --reload --port 8005
   ```
   *The backend will be available at `http://127.0.0.1:8005`. You can view the interactive API documentation at `http://127.0.0.1:8005/docs`.*

   Allowed frontend origins default to `http://localhost:5173` and `http://127.0.0.1:5173`. Override them with the `FRONTEND_ORIGINS` environment variable (comma-separated). See `backend/.env.example` for all options. The SQLite database lives at `backend/store.db` and is git-ignored.

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

## 🔗 API Endpoints

### Public
- `GET /products`: Paginated product list.
  - Query parameters: `page`, `limit` (max 100), `search`, `category` (slug), `sort` (`newest`, `price_asc`, `price_desc`, `name`).
  - Returns the `X-Total-Count` header with the total number of matching products.
- `GET /products/{id}`: Product detail (active products only).
- `GET /categories`: List product categories.
- `GET /images/{filename}`: Serves static images for the T-shirts.
- `GET /`: Health check endpoint.

### Admin
> These endpoints are **not authenticated yet**. Admin authentication is added in Phase 2, before deployment.

- `GET /admin/products`: Product list including inactive products.
- `POST /admin/products`: Create a product with images and size variants.
- `PUT /admin/products/{id}`: Update a product, its images, or its variants.
- `DELETE /admin/products/{id}`: Delete a product.
- `POST /admin/categories`: Create a category.
- `PUT /admin/categories/{id}`: Rename a category.
- `DELETE /admin/categories/{id}`: Delete an empty category.

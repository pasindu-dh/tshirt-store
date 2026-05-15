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
- **Uvicorn** (ASGI server)
- **StaticFiles** (Local image serving)
- **CORS Middleware** (Configured to allow frontend connections)

## 📁 Project Structure

```
tshirt-store/
│
├── backend/          # FastAPI Python server and static images
│   ├── images/       # Static product images served by the backend
│   └── main.py       # Main FastAPI application entry point
│
└── frontend/         # React/Vite frontend application
    ├── public/
    ├── src/          # React components and pages
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
   pip install fastapi uvicorn
   ```
3. Run the backend server:
   ```bash
   uvicorn main:app --reload --port 8005
   ```
   *The backend will be available at `http://127.0.0.1:8005`. You can view the interactive API documentation at `http://127.0.0.1:8005/docs`.*

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
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The terminal will output the local URL (usually `http://localhost:5173`) where you can view the application.*

## 🔗 API Endpoints

- `GET /products`: Fetches a paginated list of products. (Query parameters: `page` and `limit`)
- `GET /images/{filename}`: Serves static images for the T-shirts.
- `GET /`: Health check endpoint.

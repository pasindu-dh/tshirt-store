from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ THIS IS THE FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Backend working"}

@app.get("/products")
def get_products():
    return [
        {"id": 1, "name": "Black T-Shirt", "price": 2500},
        {"id": 2, "name": "White T-Shirt", "price": 2000},
        {"id": 3, "name": "Oversized Tee", "price": 3000},
    ]
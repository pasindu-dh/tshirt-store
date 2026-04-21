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
        {
            "id": 1,
            "name": "Black T-Shirt",
            "price": 2500,
            "image": "http://localhost:5173/images/t_shirt_01.jpg"
        },
        {
            "id": 2,
            "name": "White T-Shirt",
            "price": 2000,
            "image": "http://localhost:5173/images/t_shirt_02.jpg"
        },
        {
            "id": 3,
            "name": "Oversized Tee",
            "price": 3000,
            "image": "http://localhost:5173/images/t_shirt_03.jpg"
        },
        {
            "id": 4,
            "name": "Red Hoodie",
            "price": 3500,
            "image": "http://localhost:5173/images/t_shirt_04.jpg"
        }
    ]
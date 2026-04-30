from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# ✅ Allow frontend (React) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Serve images from local folder
app.mount("/images", StaticFiles(directory="images"), name="images")

# ✅ Fake database (30 products for testing)
all_products = [
    {
        "id": i,
        "name": f"Product {i}",
        "price": 1000 + i * 500,  # Just a sample price
        "image": f"http://127.0.0.1:8005/images/t_shirt_0{i}.jpg"
    }
    for i in range(1, 31)
]

# ✅ Pagination API (IMPORTANT)
@app.get("/products")
def get_products(page: int = Query(1, ge=1), limit: int = 6):
    start = (page - 1) * limit
    end = start + limit

    paginated_products = all_products[start:end]

    return paginated_products

# ✅ Test route
@app.get("/")
def home():
    return {"message": "Backend working"}
from app.database import SessionLocal
from app.services.stock import expire_unpaid_online_orders


def main() -> None:
    with SessionLocal() as db:
        released = expire_unpaid_online_orders(db)

    print(f"Expired {released} unpaid online order(s).")


if __name__ == "__main__":
    main()

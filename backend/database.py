import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "ecommerce.db"
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DEFAULT_DB_PATH.as_posix()}",
)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql+psycopg2://", 1
    )
elif SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )

connect_args = (
    {"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    else {}
)
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_product_seller_id_column():
    inspector = inspect(engine)
    if not inspector.has_table("products"):
        return

    columns = {column["name"] for column in inspector.get_columns("products")}
    if "seller_id" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE products ADD COLUMN "
                    "seller_id VARCHAR REFERENCES users(uid)"
                )
            )
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_products_seller_id "
                "ON products (seller_id)"
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
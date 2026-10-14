import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

def get_engine():
    connection_url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )

    return create_engine(connection_url)


def test_connection():
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT PostGIS_Version();"))
        version = result.fetchone()[0]

    print("Connected! PostGIS version:", version)


if __name__ == "__main__":
    test_connection()
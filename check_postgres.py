"""Check the local PostgreSQL connection used in notebook Cell 20."""

import os

import psycopg2
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    required = ["POSTGRES_USER", "POSTGRES_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing .env setting(s): {', '.join(missing)}")

    connection = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "postgres"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            print("Connected successfully!")
            print(cursor.fetchone()[0])
    finally:
        connection.close()


if __name__ == "__main__":
    main()

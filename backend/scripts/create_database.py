"""Create the PostgreSQL database from DATABASE_URL if it does not exist."""

from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import os


def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set in .env")

    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/")
    if not db_name:
        raise SystemExit("DATABASE_URL must include a database name")

    admin_url = parsed._replace(path="/postgres").geturl()
    conn = psycopg2.connect(admin_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if cur.fetchone():
        print(f"Database '{db_name}' already exists")
    else:
        cur.execute(f'CREATE DATABASE "{db_name}"')
        print(f"Created database '{db_name}'")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

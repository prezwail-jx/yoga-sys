import os
import subprocess
from testcontainers.postgres import PostgresContainer

with PostgresContainer("postgres:16") as postgres:
    url = postgres.get_connection_url().replace("psycopg2", "psycopg")
    print("DB URL:", url)
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    
    # Run with debug
    subprocess.run(["uv", "run", "alembic", "upgrade", "head", "--sql"], env=env, check=True)

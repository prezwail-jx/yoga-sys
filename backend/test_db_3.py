from sqlalchemy import text, create_engine
from testcontainers.postgres import PostgresContainer

with PostgresContainer("postgres:16") as postgres:
    url = postgres.get_connection_url() # default is psycopg2
    print("DB URL:", url)
    engine = create_engine(url)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1"))
        print(res.scalar())

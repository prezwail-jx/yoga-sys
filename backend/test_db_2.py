from testcontainers.postgres import PostgresContainer

try:
    with PostgresContainer("postgres:16") as postgres:
        print("SUCCESS:", postgres.get_connection_url())
except Exception as e:
    print("ERROR:", e)
